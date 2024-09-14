from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from pydantic import SecretStr

from features.prompting import prompt_library
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

# Based on popularity and support in model embeddings
KNOWN_DOCS_FORMATS = {
    "pdf": "application/pdf",
}

COPYWRITER_OPEN_AI_MODEL = "gpt-4o-mini"
COPYWRITER_OPEN_AI_TEMPERATURE = 0.3
COPYWRITER_OPEN_AI_MAX_TOKENS = 4096
SEARCH_RESULT_PAGES = 2
DEFAULT_QUESTION = "What is this document about?"


# Not tested as it's just a proxy
class DocumentSearch(SafePrinterMixin):
    __job_id: str
    __embeddings: Embeddings
    __loaded_pages: list[Document]
    __additional_context: str
    __copywriter_messages: list[BaseMessage]
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
        self.__loaded_pages = PyPDFLoader(document_url, extract_images = True).load_and_split()
        self.__embeddings = OpenAIEmbeddings(openai_api_key = SecretStr(open_ai_api_key))
        self.__additional_context = additional_context or DEFAULT_QUESTION
        self.__copywriter_messages = []
        self.__copywriter_messages.append(SystemMessage(prompt_library.document_search_copywriter))
        # noinspection PyArgumentList
        self.__copywriter = ChatOpenAI(
            model = COPYWRITER_OPEN_AI_MODEL,
            temperature = COPYWRITER_OPEN_AI_TEMPERATURE,
            max_tokens = COPYWRITER_OPEN_AI_MAX_TOKENS,
            timeout = float(config.web_timeout_s),
            max_retries = config.web_retries,
            api_key = str(open_ai_api_key),
        )

    def execute(self) -> str | None:
        self.sprint(f"Starting document search for job '{self.__job_id}'")
        try:
            # run the raw search first
            document_index = FAISS.from_documents(documents = self.__loaded_pages, embedding = self.__embeddings)
            results = document_index.similarity_search(query = self.__additional_context, k = SEARCH_RESULT_PAGES)
            self.sprint(f"Document search returned {len(results)} similarity search results")
            search_results: str = ""
            if results:
                for result in results:
                    page_number = result.metadata.get("page") or "Unknown"
                    content = result.page_content or "<No result>"
                    search_results += f"[Page {page_number}]\n{content}\n\n---\n\n"
                search_results = search_results.strip()
            if not search_results:
                search_results = "<No results>"

            # then run the copywriter on the search results
            self.sprint("Invoking copywriter on search results")
            self.__copywriter_messages.append(HumanMessage(content = search_results))
            answer = self.__copywriter.invoke(self.__copywriter_messages)
            if not isinstance(answer, AIMessage):
                raise AssertionError(f"Received a non-AI message from the model: {answer}")
            if not answer.content or not isinstance(answer.content, str):
                raise AssertionError(f"Received an unexpected content from the model: {answer}")
            return f"Document Search Results:\n\n```\n{str(answer.content)}\n```"
        except Exception as e:
            self.sprint("Document search failed", e)
            return None
