import re


class SkillNormalizationService:

    # Canonical skill -> supported aliases
    SKILL_ALIASES = {
        "python": [
            "python",
            "python3",
        ],
        "machine learning": [
            "machine learning",
            "ml",
        ],
        "deep learning": [
            "deep learning",
            "dl",
        ],
        "artificial intelligence": [
            "artificial intelligence",
            "ai",
        ],
        "fastapi": [
            "fastapi",
            "fast api",
        ],
        "sql": [
            "sql",
            "structured query language",
        ],
        "git": [
            "git",
            "github",
            "gitlab",
            "version control",
        ],
        "pytorch": [
            "pytorch",
            "torch",
        ],
        "tensorflow": [
            "tensorflow",
            "tf",
        ],
        "rag": [
            "rag",
            "retrieval augmented generation",
            "retrieval-augmented generation",
        ],
        "docker": [
            "docker",
            "containerization",
            "containerisation",
        ],
        "langchain": [
            "langchain",
        ],
        "aws": [
            "aws",
            "amazon web services",
        ],
        "azure": [
            "azure",
            "microsoft azure",
        ],
        "gcp": [
            "gcp",
            "google cloud",
            "google cloud platform",
        ],
        "postgresql": [
            "postgresql",
            "postgres",
        ],
        "rest api": [
            "rest api",
            "restful api",
            "restful",
        ],
        "scikit-learn": [
            "scikit-learn",
            "sklearn",
        ],
        "pandas": [
            "pandas",
        ],
        "numpy": [
            "numpy",
        ],
        "react": [
            "react",
            "reactjs",
            "react.js",
        ],
        "javascript": [
            "javascript",
            "js",
        ],
        "typescript": [
            "typescript",
            "ts",
        ],
    }

    @classmethod
    def normalize_text(cls, text: str) -> str:
        text = text.lower()

        text = text.replace("-", " ")
        text = text.replace("/", " ")

        text = re.sub(r"[^a-z0-9+#. ]", " ", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @classmethod
    def canonicalize_skill(cls, skill: str) -> str:
        normalized_skill = cls.normalize_text(skill)

        for canonical_skill, aliases in cls.SKILL_ALIASES.items():
            for alias in aliases:
                if normalized_skill == cls.normalize_text(alias):
                    return canonical_skill

        return normalized_skill

    @classmethod
    def parse_skills(cls, skills_text: str | None) -> list[str]:
        if not skills_text:
            return []

        skills = []

        for skill in skills_text.split(","):
            skill = skill.strip()

            if not skill:
                continue

            canonical_skill = cls.canonicalize_skill(skill)

            if canonical_skill not in skills:
                skills.append(canonical_skill)

        return skills

    @classmethod
    def skill_present(
        cls,
        resume_text: str,
        canonical_skill: str,
    ) -> bool:

        normalized_resume = cls.normalize_text(resume_text)

        aliases = cls.SKILL_ALIASES.get(
            canonical_skill,
            [canonical_skill],
        )

        for alias in aliases:
            normalized_alias = cls.normalize_text(alias)

            pattern = (
                r"(?<![a-z0-9+#])"
                + re.escape(normalized_alias)
                + r"(?![a-z0-9+#])"
            )

            if re.search(pattern, normalized_resume):
                return True

        return False

    @classmethod
    def match_skills(
        cls,
        resume_text: str,
        skills: list[str],
    ) -> tuple[list[str], list[str]]:

        matched = []
        missing = []

        for skill in skills:

            canonical_skill = cls.canonicalize_skill(skill)

            if cls.skill_present(
                resume_text,
                canonical_skill,
            ):
                matched.append(canonical_skill)
            else:
                missing.append(canonical_skill)

        return matched, missing