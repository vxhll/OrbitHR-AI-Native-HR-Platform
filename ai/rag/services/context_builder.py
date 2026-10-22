from .retrieval import PolicyRetriever


class RAGContextBuilder:
    def __init__(self):
        self.retriever = PolicyRetriever()

    def build_context(self, query: str, top_k: int = 3) -> str:
        results = self.retriever.search(
            query=query,
            top_k=top_k,
        )

        if not results:
            return "No relevant HR policy information was found."

        context_parts = []

        for index, result in enumerate(results, start=1):
            context_parts.append(
                f"""SOURCE {index}: {result['source']}
CONTENT:
{result['text']}
"""
            )

        return "\n".join(context_parts)


if __name__ == "__main__":
    builder = RAGContextBuilder()

    query = input("\nEnter HR policy question: ").strip()

    context = builder.build_context(query)

    print("\nOrbitHR RAG Context")
    print("-------------------")
    print(context)