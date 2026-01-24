from langchain_core.embeddings import Embeddings
from openai import OpenAI


class LangChainEmbeddingsAdapter(Embeddings):

    def __init__(
        self,
        client: OpenAI,
        model_id: str,
    ):
        self.__client = client
        self.__model_id = model_id

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # noinspection PyTypeChecker
        response = self.__client.embeddings.create(
            model = self.__model_id,
            input = texts,
        )
        return [embedding.embedding for embedding in response.data]

    def embed_query(self, text: str) -> list[float]:
        # noinspection PyTypeChecker
        response = self.__client.embeddings.create(
            model = self.__model_id,
            input = text,
        )
        return response.data[0].embedding
