from app.services.rag.answer_service import HRPolicyAnswerService


class LeaveAgent:
    """
    Specialized agent for employee leave-related questions.

    The current version is policy-focused and uses the
    existing HR Policy RAG knowledge base.
    """

    def __init__(self):
        self.policy_service = HRPolicyAnswerService()

    def answer(self, question: str) -> dict:
        result = self.policy_service.answer_question(
            question=question,
            top_k=5,
        )

        return {
            "answer": result["answer"],
            "sources": result["sources"],
            "requires_human": False,
        }