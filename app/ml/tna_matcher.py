"""
Boosts recommendation scores toward training programs that match real
institutional demand - either the official 2025 Training Needs Assessment
(tna_2025_demand table, seeded from docs/Summary of TNA 2025.pdf), or,
for a college that submitted nothing there, what that college's own
employees have already said they want through TrainWise's own assessment
form (assessments.desired_skills).

Per the subject specialist's explicit guidance (2026-08-26/27): this is
NOT a training signal for the model - it's too small/curated for that
(the official list) or too informal (the self-reported fallback). It's a
second, higher-trust reference used to boost recommendations toward
institutionally-validated need instead of only synthetic labels.

Only 4 of 13 colleges (CCJE, CFND, CTE, ADMIN) submitted anything to the
2025 list. Rather than leaving every other college with nothing to check
against, this falls back to a REAL, already-existing signal for them -
what their own people have actually typed into the system - never a
fabricated or borrowed list from a different college. The fallback is
always labeled differently and weighted lower than an official match
(see SELF_REPORTED_WEIGHT in recommender.py), since it hasn't been
reviewed/aggregated by college leadership the way an official TNA
submission has.

Colleges with neither an official list nor any self-reported assessment
data yet simply get a 0.0 boost on every program - this must never
become a hard filter or those colleges lose recommendations entirely.
"""
from __future__ import annotations

from sentence_transformers import util

from app.ml.text_similarity import get_model


class Tna2025Matcher:
    def __init__(self):
        self.model = get_model()
        self._boost_by_college: dict[str, dict[int, float]] = {}
        # "official" (2025 TNA list) or "self_reported" (own employees'
        # assessment answers) - per college, so the caller can pick the
        # right explanation wording and weight.
        self._source_by_college: dict[str, str] = {}

    def index(
        self,
        titles_by_college: dict[str, list[str]],
        self_reported_by_college: dict[str, list[str]],
        programs: list[dict],
    ) -> None:
        """
        titles_by_college: {college_code: [title, ...]} from
        tna_2025_demand - the official, higher-trust source.
        self_reported_by_college: {college_code: [desired_skills text, ...]}
        from assessments - used ONLY for a college with no rows in
        titles_by_college, since official data always takes priority.
        programs: [{"id": int, "description": str}, ...] - same shape as
        TextSimilarityMatcher.index_programs.

        For each (college, program) pair, the boost is the MAX cosine
        similarity between that program's description and ANY of that
        college's reference texts - not an average, so one strong match
        isn't diluted by many unrelated ones.
        """
        self._boost_by_college = {}
        self._source_by_college = {}
        if not programs:
            return

        program_ids = [p["id"] for p in programs]
        program_embeddings = self.model.encode(
            [p["description"] for p in programs], convert_to_tensor=True
        )

        def index_source(texts_by_college: dict[str, list[str]], source: str):
            for college_code, texts in texts_by_college.items():
                if not texts or college_code in self._boost_by_college:
                    continue  # official data (indexed first) always wins
                text_embeddings = self.model.encode(texts, convert_to_tensor=True)
                sim_matrix = util.cos_sim(text_embeddings, program_embeddings).cpu().numpy()
                max_per_program = sim_matrix.max(axis=0)
                self._boost_by_college[college_code] = {
                    pid: float(score) for pid, score in zip(program_ids, max_per_program)
                }
                self._source_by_college[college_code] = source

        index_source(titles_by_college, "official")
        index_source(self_reported_by_college, "self_reported")

    def get_boost(self, college_code: str | None, program_id: int) -> float:
        if not college_code:
            return 0.0
        return self._boost_by_college.get(college_code, {}).get(program_id, 0.0)

    def get_source(self, college_code: str | None) -> str | None:
        """Returns "official", "self_reported", or None if this college has no data at all."""
        if not college_code:
            return None
        return self._source_by_college.get(college_code)
