from time import time

from langchain_core.embeddings import Embeddings
from openai import OpenAI

from di.di import DI
from features.accounting.usage_tracking_service import UsageTrackingService
from features.external_tools.tool_choice_resolver import ConfiguredTool


class UsageTrackingEmbeddings(Embeddings):
    """Uses OpenAI client directly to track real token usage."""

    def __init__(
        self,
        embedding_tool: ConfiguredTool,
        di: DI,
    ):
        embedding_model, embedding_token, _ = embedding_tool
        self.__client = OpenAI(api_key = embedding_token.get_secret_value())
        self.__model_id = embedding_model.id
        self.__embedding_tool = embedding_model
        self.__di = di

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed search docs and track usage."""
        start_time = time()
        response = self.__client.embeddings.create(
            model = self.__model_id,
            input = texts,
        )
        runtime_seconds = int(time() - start_time)

        tracking_service = UsageTrackingService(self.__di)
        tracking_service.track_llm(
            tool = self.__embedding_tool,
            runtime_seconds = runtime_seconds,
            input_tokens = response.usage.prompt_tokens,
            total_tokens = response.usage.total_tokens,
        )

        return [embedding.embedding for embedding in response.data]

    def embed_query(self, text: str) -> list[float]:
        """Embed query and track usage."""
        start_time = time()
        response = self.__client.embeddings.create(
            model = self.__model_id,
            input = text,
        )
        runtime_seconds = int(time() - start_time)

        tracking_service = UsageTrackingService(self.__di)
        tracking_service.track_llm(
            tool = self.__embedding_tool,
            runtime_seconds = runtime_seconds,
            input_tokens = response.usage.prompt_tokens,
            total_tokens = response.usage.total_tokens,
        )

        return response.data[0].embedding
