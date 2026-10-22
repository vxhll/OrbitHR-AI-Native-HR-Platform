from app.services.rag.chunker import PolicyChunker
from app.services.rag.document_loader import PolicyDocumentLoader
from app.services.rag.vector_store import PolicyVectorStore


class PolicyIngestionService:
    def __init__(self, policy_directory: str):
        self.loader = PolicyDocumentLoader(policy_directory)
        self.chunker = PolicyChunker()
        self.vector_store = PolicyVectorStore()

    def ingest(self) -> dict:
        documents = self.loader.load_documents()

        chunks = self.chunker.chunk_documents(documents)

        stored_chunks = self.vector_store.add_chunks(chunks)

        return {
            "documents_loaded": len(documents),
            "chunks_created": len(chunks),
            "chunks_stored": stored_chunks,
            "vector_store_count": self.vector_store.count(),
        }