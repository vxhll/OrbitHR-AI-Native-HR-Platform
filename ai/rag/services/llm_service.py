import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


# ---------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------

ENV_PATH = (
    Path(__file__).resolve().parents[3]
    / "backend"
    / ".env"
)

load_dotenv(dotenv_path=ENV_PATH)


# ---------------------------------------------------------
# LLM Service
# ---------------------------------------------------------

class LLMService:

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not configured"
            )

        self.client = Groq(
            api_key=api_key
        )

        # Current Groq model
        self.model = "openai/gpt-oss-120b"

    # -----------------------------------------------------
    # Generate grounded HR answer
    # -----------------------------------------------------

    def generate_answer(
        self,
        question: str,
        context: str,
    ) -> str:

        system_prompt = """
You are the OrbitHR HR Policy Assistant.

Your job is to answer employee HR policy questions
using only the policy context provided by the system.

Rules:

1. Use only information contained in the provided context.
2. Do not invent policies, rules, benefits, or numbers.
3. If the context does not contain enough information,
   clearly state that the available HR policy documents
   do not provide enough information.
4. Give concise and professional answers.
5. Mention the relevant policy source when appropriate.
6. Do not make employment decisions.
7. Do not provide legal advice.
8. Do not assume information that is not present in the
   provided policy context.
"""

        user_prompt = f"""
HR POLICY CONTEXT:

{context}

EMPLOYEE QUESTION:

{question}

Answer the employee's question using only the
HR policy context provided above.
"""

        response = self.client.chat.completions.create(
            model=self.model,
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
            temperature=0.1,
        )

        return response.choices[0].message.content.strip()


# ---------------------------------------------------------
# Direct test
# ---------------------------------------------------------

if __name__ == "__main__":

    print("OrbitHR LLM Service")
    print("-------------------")

    service = LLMService()

    answer = service.generate_answer(
        question="How many casual leave days can an employee take?",

        context="""
ORBIT HR - LEAVE POLICY

Employees are eligible for 12 days of casual leave
per calendar year.

Casual leave may be used for personal work,
short-term requirements, or unforeseen situations.
""",
    )

    print("\nAnswer:")
    print(answer)