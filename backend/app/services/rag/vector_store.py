from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction


class PolicyVectorStore:
    COLLECTION_NAME = "hr_policies"

    def __init__(
        self,
        persist_directory: str = "storage/rag/chroma",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=persist_directory
        )

        self.embedding_function = SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )

        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=self.embedding_function,
        )

    def add_chunks(self, chunks: list[dict]) -> int:
        if not chunks:
            return 0

        self.collection.upsert(
            ids=[chunk["id"] for chunk in chunks],
            documents=[chunk["text"] for chunk in chunks],
            metadatas=[chunk["metadata"] for chunk in chunks],
        )

        return len(chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> dict:
        return self.collection.query(
            query_texts=[query],
            n_results=top_k,
        )

    def count(self) -> int:
        return self.collection.count()