from langchain_anthropic import ChatAnthropic
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from features.ai_tools.external_ai_tool_library import TEXT_EMBEDDING_3_SMALL, CLAUDE_3_7_SONNET
from features.prompting import prompt_library
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

DEFAULT_QUESTION = "What is this document about?"
SEARCH_RESULT_PAGES = 2


# Not tested as it's just a proxy
class DocumentSearch(SafePrinterMixin):
    __job_id: str
    __embeddings: Embeddings
    __loaded_pages: list[Document]
    __additional_context: str
    __copywriter: BaseChatModel

    def __init__(
        self,
        job_id: str,
        document_url: str,
        open_ai_api_key: str,
        additional_context: str | None = None,
    ):
        super().__init__(config.verbose)
        self.__job_id = job_id
        self.__loaded_pages = PyMuPDFLoader(document_url).load()
        self.sprint(f"Loaded document pages: {len(self.__loaded_pages)}")
        # noinspection PyArgumentList
        self.__embeddings = OpenAIEmbeddings(
            model = TEXT_EMBEDDING_3_SMALL.id,
            openai_api_key = SecretStr(open_ai_api_key),
        )
        self.__additional_context = additional_context or DEFAULT_QUESTION
        # noinspection PyArgumentList
        self.__copywriter = ChatAnthropic(
            model_name = CLAUDE_3_7_SONNET.id,
            temperature = 0.3,
            max_tokens = 4096,
            timeout = float(config.web_timeout_s),
            max_retries = config.web_retries,
            api_key = SecretStr(str(config.anthropic_token)),
        )

    def execute(self) -> str | None:
        self.sprint(f"Starting document search for job '{self.__job_id}'")
        try:
            # run the raw search first
            document_index = InMemoryVectorStore(self.__embeddings)
            document_index.add_documents(self.__loaded_pages)
            results = document_index.similarity_search(query = self.__additional_context, k = SEARCH_RESULT_PAGES)
            self.sprint(f"Document search returned {len(results)} similarity search results")
            search_results: str = ""
            if results:
                for result in results:
                    page_number = result.metadata.get("page") or "Unknown"
                    content = result.page_content or "<No result>"
                    search_results += f"[Chunk {page_number}]\n{content}\n\n---\n\n"
                search_results = search_results.strip()
            if not search_results:
                search_results = "<No results>"

            # then run the copywriter on the search results
            self.sprint("Invoking copywriter on search results")
            copywriter_prompt = prompt_library.document_search_copywriter(self.__additional_context)
            copywriter_messages = [SystemMessage(copywriter_prompt), HumanMessage(search_results)]
            answer = self.__copywriter.invoke(copywriter_messages)
            if not isinstance(answer, AIMessage):
                raise AssertionError(f"Received a non-AI message from the model: {answer}")
            if not answer.content or not isinstance(answer.content, str):
                raise AssertionError(f"Received an unexpected content from the model: {answer}")
            return f"Document Search Results:\n\n```\n{str(answer.content)}\n```"
        except Exception as e:
            self.sprint("Document search failed", e)
            return None
