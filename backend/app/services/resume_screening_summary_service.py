import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


class ResumeScreeningSummaryService:

    @staticmethod
    def generate_summary(
        candidate_name: str,
        job_title: str,
        fit_score: float,
        required_skill_score: float,
        preferred_skill_score: float,
        experience_score: float,
        matched_required_skills: list[str],
        missing_required_skills: list[str],
        matched_preferred_skills: list[str],
        missing_preferred_skills: list[str],
        recommendation: str,
    ) -> str:

        groq_api_key = os.getenv("GROQ_API_KEY")

        # Deterministic fallback in case Groq is unavailable
        # or returns an empty response.
        fallback_summary = (
            f"{candidate_name} has an overall fit score of "
            f"{fit_score:.0f}% for the {job_title} role. "
            f"Required skills match: {required_skill_score:.0f}%. "
            f"Preferred skills match: {preferred_skill_score:.0f}%. "
            f"Experience score: {experience_score:.0f}%. "
            f"Matched required skills: "
            f"{', '.join(matched_required_skills) or 'None'}. "
            f"Missing required skills: "
            f"{', '.join(missing_required_skills) or 'None'}. "
            f"Matched preferred skills: "
            f"{', '.join(matched_preferred_skills) or 'None'}. "
            f"Missing preferred skills: "
            f"{', '.join(missing_preferred_skills) or 'None'}. "
            f"Recommendation: {recommendation}. "
            "Human review is required before making a hiring decision."
        )

        # If no Groq API key is configured, use fallback.
        if not groq_api_key:
            return fallback_summary

        client = Groq(api_key=groq_api_key)

        prompt = f"""
You are an HR recruitment assistant.

Generate a concise, factual screening summary for a recruiter.

IMPORTANT:
- Use ONLY the information provided below.
- Do not invent qualifications, experience, education, or achievements.
- Do not make the hiring decision.
- Do not infer protected or sensitive characteristics.
- Clearly mention important matched and missing skills.
- State that human review is required.
- Keep the response between 80 and 120 words.
- Do not use the fit score as the sole basis for a hiring decision.
- Write only the recruiter-facing summary.

Candidate: {candidate_name}
Role: {job_title}

Overall fit score: {fit_score:.2f}%
Required skill score: {required_skill_score:.2f}%
Preferred skill score: {preferred_skill_score:.2f}%
Experience score: {experience_score:.2f}%

Matched required skills:
{", ".join(matched_required_skills) or "None"}

Missing required skills:
{", ".join(missing_required_skills) or "None"}

Matched preferred skills:
{", ".join(matched_preferred_skills) or "None"}

Missing preferred skills:
{", ".join(missing_preferred_skills) or "None"}

Current screening recommendation:
{recommendation}
"""

        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You generate factual recruitment "
                            "screening summaries."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.2,
                max_completion_tokens=512,
                reasoning_effort="low",
                include_reasoning=False,
            )

            content = response.choices[0].message.content

            # Prevent blank AI summaries from being stored.
            if content and content.strip():
                return content.strip()

        except Exception:
            # Fall back to a deterministic summary if the
            # Groq request fails for any reason.
            pass

        return fallback_summary