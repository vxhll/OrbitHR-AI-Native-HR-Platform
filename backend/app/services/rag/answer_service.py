import os

from dotenv import load_dotenv
from groq import Groq

from app.services.rag.vector_store import PolicyVectorStore


load_dotenv()


class HRPolicyAnswerService:
    def __init__(self):
        self.vector_store = PolicyVectorStore()

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not configured."
            )

        self.client = Groq(api_key=api_key)

    def answer_question(
        self,
        question: str,
        top_k: int = 5,
    ) -> dict:
        results = self.vector_store.search(
            query=question,
            top_k=top_k,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        if not documents:
            return {
                "question": question,
                "answer": (
                    "I could not find relevant information "
                    "in the HR policy knowledge base. "
                    "Please contact HR for clarification."
                ),
                "sources": [],
            }

        context_parts = []

        for index, document in enumerate(documents):
            metadata = metadatas[index]

            context_parts.append(
                (
                    f"Source: {metadata.get('source')}\n"
                    f"Policy ID: {metadata.get('policy_id')}\n"
                    f"Section: {metadata.get('section')}\n\n"
                    f"{document}"
                )
            )

        context = "\n\n---\n\n".join(context_parts)

        system_prompt = """
You are OrbitHR's HR Policy Assistant.

Your job is to answer employee questions using ONLY the
HR policy context provided by the system.

STRICT GROUNDING RULES:

1. Use only facts explicitly supported by the provided
   HR policy context.

2. Do not invent policy rules, benefits, leave balances,
   approval requirements, deadlines, eligibility rules,
   systems, websites, email addresses, help desks,
   workflows, or organizational channels.

3. Do not provide examples of internal systems or
   processes unless those examples appear explicitly
   in the policy context.

4. If the answer is explicitly available in the context,
   answer clearly and concisely.

5. If the context does not contain enough information,
   say:
   "The available HR policy information does not specify
   this. Please contact HR for clarification."

6. Preserve important conditions and exceptions from
   the policy.

7. Do not make employment decisions.

8. Do not provide legal advice.

9. Never claim that a request is approved merely because
   the policy describes an approval process.

10. When appropriate, mention the relevant policy ID
    and section.

11. Do not infer information from general knowledge.

12. Do not expand vague policy language into specific
    operational procedures.

Return only the employee-facing answer.
"""

        user_prompt = f"""
HR POLICY CONTEXT:

{context}

EMPLOYEE QUESTION:

{question}
"""

        response = self.client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            max_completion_tokens=512,
            reasoning_effort="low",
            include_reasoning=False,
        )

        answer = response.choices[0].message.content.strip()

        sources = []

        for metadata in metadatas:
            source = {
                "source": metadata.get("source"),
                "policy_id": metadata.get("policy_id"),
                "section": metadata.get("section"),
            }

            if source not in sources:
                sources.append(source)

        return {
            "question": question,
            "answer": answer,
            "sources": sources,
        }