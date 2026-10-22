import json
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()


class IntentClassifier:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        self.client = Groq(api_key=api_key)

    def classify(self, question: str) -> dict:
        system_prompt = """
You are OrbitHR's HR Intent Classifier.

Classify the employee question into exactly one of these intents:

LEAVE
HR_POLICY
ONBOARDING
PAYROLL
RETENTION
UNKNOWN
HUMAN_ESCALATION

Intent definitions:

LEAVE:
Questions specifically about taking leave or leave entitlements,
including leave balance, number of leave days, leave types,
casual leave, sick leave, earned leave, leave requests,
leave approval, or taking time off.

HR_POLICY:
General HR policy questions that are NOT specifically about
leave, onboarding, payroll, or another dedicated HR workflow.
Examples include attendance policy, work-from-home policy,
employee handbook rules, workplace benefits, and general HR rules.

ONBOARDING:
Questions about joining, onboarding tasks, onboarding documents,
new employee setup, joining formalities, or onboarding status.

PAYROLL:
Questions about salary, payroll, payslips, deductions,
salary discrepancies, payroll records, or payment issues.

RETENTION:
Questions about employee attrition risk, retention support,
workplace engagement, job satisfaction, retention strategies,
or supportive actions intended to help employees remain
with the organization.

Do not use RETENTION for termination decisions, disciplinary
actions, sensitive employment disputes, or requests to make
high-impact employment decisions. Use HUMAN_ESCALATION
for those matters.

HUMAN_ESCALATION:
Sensitive or high-impact employment matters that should be
handled by HR or a human reviewer, including disputes,
harassment, discrimination, termination concerns, legal threats,
serious complaints, or requests for employment decisions.

UNKNOWN:
Questions that do not clearly belong to the categories above.

Rules:

1. Return exactly one intent.
2. Do not answer the employee's question.
3. Use only the employee's actual question.
4. Do not invent facts.
5. If the question does not clearly belong to a dedicated
   workflow, classify it as HR_POLICY when it is clearly
   asking about an HR/company policy.

6. If the question is unrelated to HR or cannot be classified,
   use UNKNOWN.

7. If the question involves a sensitive employment issue,
   prefer HUMAN_ESCALATION.
Return JSON only:

{
  "intent": "LEAVE",
  "confidence": 0.95,
  "reason": "The question is about requesting leave."
}
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
                    "content": question,
                },
            ],
            max_completion_tokens=256,
            reasoning_effort="low",
            include_reasoning=False,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content.strip()

        result = json.loads(content)

        return {
            "question": question,
            "intent": result["intent"],
            "confidence": float(result["confidence"]),
            "reason": result["reason"],
        }