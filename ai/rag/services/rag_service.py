from .context_builder import RAGContextBuilder
from .llm_service import LLMService


class RAGService:

    def __init__(self):
        self.context_builder = RAGContextBuilder()
        self.llm_service = LLMService()

    def ask(
        self,
        question: str,
        top_k: int = 3,
    ) -> dict:

        results = self.context_builder.retriever.search(
            query=question,
            top_k=top_k,
        )

        context = self.context_builder.build_context(
            query=question,
            top_k=top_k,
        )

        answer = self.llm_service.generate_answer(
            question=question,
            context=context,
        )

        sources = []

        for result in results:
            sources.append(
                {
                    "source": result["source"],
                    "distance": result["distance"],
                }
            )

        return {
            "question": question,
            "answer": answer,
            "sources": sources,
        }


if __name__ == "__main__":

    print("\nOrbitHR RAG Service")
    print("-------------------")

    rag = RAGService()

    question = input(
        "\nEnter HR policy question: "
    ).strip()

    result = rag.ask(question)

    print("\nAnswer:")
    print(result["answer"])

    print("\nSources:")
    for source in result["sources"]:
        print(
            f"- {source['source']} "
            f"(distance: {source['distance']})"
        )