import re

from app.services.skill_normalization_service import (
    SkillNormalizationService,
)


class ResumeScreeningService:

    @staticmethod
    def _calculate_skill_score(
        matched_count: int,
        total_count: int,
    ) -> float:

        if total_count == 0:
            return 0.0

        return (matched_count / total_count) * 100

    @staticmethod
    def _calculate_experience_score(
        resume_text: str,
        minimum_experience_years: int,
    ) -> float:

        if minimum_experience_years <= 0:
            return 100.0

        normalized_resume = (
            SkillNormalizationService.normalize_text(
                resume_text
            )
        )

        patterns = [
            r"(\d+)\+?\s+years?",
            r"(\d+)\+?\s+yrs?",
        ]

        detected_years = []

        for pattern in patterns:
            matches = re.findall(
                pattern,
                normalized_resume,
            )

            for match in matches:
                detected_years.append(int(match))

        if not detected_years:
            return 0.0

        maximum_detected_experience = max(
            detected_years
        )

        if (
            maximum_detected_experience
            >= minimum_experience_years
        ):
            return 100.0

        return (
            maximum_detected_experience
            / minimum_experience_years
        ) * 100

    @staticmethod
    def screen_candidate(
        resume_text: str,
        required_skills: str,
        preferred_skills: str | None,
        minimum_experience_years: int,
    ) -> dict:

        # ---------------------------------------------------------
        # STEP 1: Canonicalize job skills
        # ---------------------------------------------------------

        required_skill_list = (
            SkillNormalizationService.parse_skills(
                required_skills
            )
        )

        preferred_skill_list = (
            SkillNormalizationService.parse_skills(
                preferred_skills
            )
        )

        # ---------------------------------------------------------
        # STEP 2: Alias-aware resume matching
        # ---------------------------------------------------------

        required_matched, required_missing = (
            SkillNormalizationService.match_skills(
                resume_text,
                required_skill_list,
            )
        )

        preferred_matched, preferred_missing = (
            SkillNormalizationService.match_skills(
                resume_text,
                preferred_skill_list,
            )
        )

        # ---------------------------------------------------------
        # STEP 3: Calculate component scores
        # ---------------------------------------------------------

        required_score = (
            ResumeScreeningService._calculate_skill_score(
                len(required_matched),
                len(required_skill_list),
            )
        )

        preferred_score = (
            ResumeScreeningService._calculate_skill_score(
                len(preferred_matched),
                len(preferred_skill_list),
            )
        )

        experience_score = (
            ResumeScreeningService._calculate_experience_score(
                resume_text,
                minimum_experience_years,
            )
        )

        # ---------------------------------------------------------
        # STEP 4: Calculate overall fit
        # ---------------------------------------------------------


        if preferred_skill_list:
            overall_score = (
                (required_score * 0.60)
                + (preferred_score * 0.20)
                + (experience_score * 0.20)
            )
        else:
            overall_score = (
                (required_score * 0.75)
                + (experience_score * 0.25)
            )

        # ---------------------------------------------------------
        # STEP 5: Generate deterministic recommendation
        # ---------------------------------------------------------

        if overall_score >= 80:
            recommendation = "Strong Match"

        elif overall_score >= 60:
            recommendation = "Potential Match"

        else:
            recommendation = "Needs Review"

        return {
            "fit_score": overall_score,

            "required_skill_score": round(
                required_score,
                2,
            ),

            "preferred_skill_score": round(
                preferred_score,
                2,
            ),

            "experience_score": round(
                experience_score,
                2,
            ),

            "matched_required_skills": required_matched,

            "missing_required_skills": required_missing,

            "matched_preferred_skills": preferred_matched,

            "missing_preferred_skills": preferred_missing,

            "recommendation": recommendation,
        }