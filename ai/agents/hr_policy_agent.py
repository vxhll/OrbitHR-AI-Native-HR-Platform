import sys
from pathlib import Path
from typing import TypedDict


# =========================================================
# PROJECT PATH
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =========================================================
# ORBIT HR RAG SERVICE
# =========================================================

from ai.rag.services.rag_service import RAGService


# =========================================================
# HR POLICY AGENT STATE
# =========================================================

class HRPolicyAgentState(TypedDict):
    question: str
    answer: str
    sources: list[dict]


# =========================================================
# HR POLICY AGENT
# =========================================================

class HRPolicyAgent:

    def __init__(self):

        self.rag_service = RAGService()


    # =====================================================
    # ANSWER POLICY QUESTION
    # =====================================================

    def answer(
        self,
        question: str
    ) -> dict:

        question = question.strip()

        if not question:

            return {
                "question": question,
                "answer": (
                    "Please provide an HR policy question."
                ),
                "sources": [],
            }

        result = self.rag_service.ask(
            question=question,
            top_k=3,
        )

        return {
            "question": question,
            "answer": result["answer"],
            "sources": result["sources"],
        }


    # =====================================================
    # HANDLE AGENT STATE
    # =====================================================

    def handle(
        self,
        state: HRPolicyAgentState
    ) -> HRPolicyAgentState:

        result = self.answer(
            state["question"]
        )

        return {
            **state,
            "answer": result["answer"],
            "sources": result["sources"],
        }


# =========================================================
# CLI TEST
# =========================================================

if __name__ == "__main__":

    print()
    print("OrbitHR HR Policy Agent")
    print("-----------------------")

    question = input(
        "\nEnter HR policy question: "
    ).strip()

    agent = HRPolicyAgent()

    result = agent.handle(
        {
            "question": question,
            "answer": "",
            "sources": [],
        }
    )

    print()
    print("Answer:")
    print(result["answer"])

    if result["sources"]:

        print()
        print("Sources:")

        for source in result["sources"]:

            print(
                f"- {source['source']} "
                f"(distance: {source['distance']})"
            )