from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.vectorstores import InMemoryVectorStore

from di.di import DI
from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import CLAUDE_3_7_SONNET, TEXT_EMBEDDING_3_SMALL
from features.external_tools.configured_tool import ConfiguredTool
from features.integrations import prompt_resolvers
from util import log

DEFAULT_QUESTION = "What is this document about?"
SEARCH_RESULT_PAGES = 2


# Not tested as it's just a proxy
class DocumentSearch:

    DEFAULT_EMBEDDING_TOOL: ExternalTool = TEXT_EMBEDDING_3_SMALL
    EMBEDDING_TOOL_TYPE: ToolType = ToolType.embedding
    DEFAULT_COPYWRITER_TOOL: ExternalTool = CLAUDE_3_7_SONNET
    COPYWRITER_TOOL_TYPE: ToolType = ToolType.copywriting

    error: str | None
    __job_id: str
    __embeddings: Embeddings
    __loaded_pages: list[Document]
    __additional_context: str
    __copywriter: BaseChatModel
    __di: DI

    def __init__(
        self,
        job_id: str,
        document_url: str,
        embedding_tool: ConfiguredTool,
        copywriter_tool: ConfiguredTool,
        di: DI,
        additional_context: str | None = None,
    ):
        self.__job_id = job_id
        self.__loaded_pages = PyMuPDFLoader(document_url).load()
        log.t(f"Loaded document pages: {len(self.__loaded_pages)}")
        self.__additional_context = additional_context or DEFAULT_QUESTION
        self.__embeddings = di.openai_embeddings(embedding_tool)
        self.__copywriter = di.chat_langchain_model(copywriter_tool)
        self.__di = di

    def execute(self) -> str | None:
        log.d(f"Starting document search for job '{self.__job_id}'")
        self.error = None
        try:
            # run the raw search first
            document_index = InMemoryVectorStore(self.__embeddings)
            document_index.add_documents(self.__loaded_pages)
            results = document_index.similarity_search(query = self.__additional_context, k = SEARCH_RESULT_PAGES)
            log.t(f"Document search returned {len(results)} similarity search results")
            search_results: str = "[Raw Document Search Results]\n\n"
            found_content = False
            if results:
                for result in results:
                    page_number = result.metadata.get("page", "Unknown") or "Unknown"
                    content = result.page_content or "<No result>"
                    search_results += f"[Chunk {page_number}]\n{content}\n\n---\n\n"
                    found_content = True
                search_results = search_results.strip()
            if not found_content:
                search_results = "<No results>"

            # then run the copywriter on the search results
            log.t("Invoking copywriter on search results")
            system_prompt = prompt_resolvers.document_search_and_response(self.__additional_context, self.__di.invoker_chat)
            copywriter_messages = [SystemMessage(system_prompt), HumanMessage(search_results)]
            answer = self.__copywriter.invoke(copywriter_messages)
            if not isinstance(answer, AIMessage):
                raise AssertionError(f"Received a non-AI message from the model: {answer}")
            if not answer.content or not isinstance(answer.content, str):
                raise AssertionError(f"Received an unexpected content from the model: {answer}")
            return f"Document Search Results:\n\n```\n{str(answer.content)}\n```"
        except Exception as e:
            self.error = log.e("Document search failed", e)
            return None
