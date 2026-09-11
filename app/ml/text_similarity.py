"""
Wraps Sentence-BERT for comparing a user's free-text training request
(assessments.desired_skills / assessments.comments) against the
training_programs catalog.

The SBERT model itself downloads on first use (~80MB for the default
all-MiniLM-L6-v2) and needs internet access the first time it runs.
After that it's cached locally by the sentence-transformers library.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer, util

from app.config import settings


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    # Cached so the (somewhat slow) model load only happens once per process.
    print(
        f"[text_similarity] Loading SBERT model '{settings.sbert_model_name}' "
        "— first run downloads it from Hugging Face (~80MB), this can take "
        "a minute or two depending on your connection..."
    )
    model = SentenceTransformer(settings.sbert_model_name)
    print("[text_similarity] SBERT model loaded.")
    return model


class TextSimilarityMatcher:
    def __init__(self):
        self.model = get_model()
        self._program_ids: list[int] = []
        self._program_embeddings = None
        self._category_names: list[str] = []
        self._category_embeddings = None

    def index_programs(self, programs: list[dict]) -> None:
        """
        programs: list of {"id": int, "description": str}. Call this once
        at startup (or whenever the catalog changes) — embedding is the
        expensive part, so we don't want to redo it per request.
        """
        self._program_ids = [p["id"] for p in programs]
        descriptions = [p["description"] for p in programs]
        self._program_embeddings = self.model.encode(
            descriptions, convert_to_tensor=True
        )

    def index_categories(self, categories: list[str]) -> None:
        """
        categories: the catalog's distinct training_programs.category
        values (e.g. "Natural Sciences", "Technology"). Call once at
        startup alongside index_programs(). See category_affinity() for
        why this is indexed separately from the program descriptions.
        """
        self._category_names = list(categories)
        self._category_embeddings = (
            self.model.encode(self._category_names, convert_to_tensor=True)
            if self._category_names else None
        )

    def category_affinity(self, specialization_text: str) -> dict[str, float]:
        """
        Returns {category_name: similarity} for a person's declared
        specialization against each catalog category's LABEL.

        2026-09-09 - added after a real, reproducible case: comparing a
        specialization like "Biology" against full program DESCRIPTIONS
        (long paragraphs full of generic academic vocabulary - "analysis",
        "techniques", "assessment") was noisy enough that a genuinely
        unrelated program ("Emerging Technologies in Engineering
        Practice") could out-score the actually-correct one on raw text
        alone. Comparing the same specialization against short, topically
        clean CATEGORY LABELS instead gives a much cleaner signal -
        checked directly: "Biology" scores 0.50 against "Natural
        Sciences" with the next-closest category at 0.41 and everything
        else below 0.30, a wide, unambiguous margin, versus the
        description-level scores which were bunched within 0.05 of each
        other across several unrelated programs. See recommender.py's
        CATEGORY_AFFINITY_WEIGHT for how this is folded into the score.
        """
        if not specialization_text or not specialization_text.strip() or self._category_embeddings is None:
            return {}
        embedding = self.model.encode(specialization_text, convert_to_tensor=True)
        scores = util.cos_sim(embedding, self._category_embeddings)[0].cpu().numpy()
        return {name: float(score) for name, score in zip(self._category_names, scores)}

    def rank_programs(self, query_text: str, top_k: int = 5) -> list[tuple[int, float]]:
        """
        Returns [(program_id, similarity_score), ...] sorted descending,
        for the given free-text query (e.g. a user's desired_skills).
        """
        if self._program_embeddings is None:
            raise RuntimeError("Call index_programs() before rank_programs().")
        if not query_text or not query_text.strip():
            return []

        query_embedding = self.model.encode(query_text, convert_to_tensor=True)
        scores = util.cos_sim(query_embedding, self._program_embeddings)[0]
        scores = scores.cpu().numpy()

        ranked_idx = np.argsort(-scores)[:top_k]
        return [(self._program_ids[i], float(scores[i])) for i in ranked_idx]

    def rank_programs_multi(
        self, weighted_texts: list[tuple[str, float]], top_k: int = 5
    ) -> list[tuple[int, float]]:
        """
        Like rank_programs(), but for several separately-weighted pieces
        of text instead of one combined query string.

        2026-09-09 - added after a real, reproducible case: a CAS Biology
        instructor's desired_skills text ("Specialized Chemical &
        Microscopic Analysis") was specific and on-topic, but the old
        approach concatenated it with his training_history entry ("Basic
        Molecular Biology Techniques and Data Analysis") into ONE string
        before embedding it. The phrase "Data Analysis" in that secondary
        field pulled the combined embedding toward IT/data-science catalog
        entries ("Data Structures, Algorithms..."), even though his actual
        request had nothing to do with them - a single embedding has no
        way to tell "what he's asking for right now" apart from
        "incidental wording in a supporting field."

        Each (text, weight) pair is embedded and scored against the
        catalog SEPARATELY, then combined as a weighted sum of similarity
        scores - never as concatenated text - so a lower-weighted field's
        wording can only ever nudge the result, not silently redirect it.
        A blank text is dropped entirely and its weight is redistributed
        proportionally across whichever texts ARE present, rather than
        just lowering the final score's scale - same "missing signal
        isn't a penalty" principle recommender.py already uses for an
        untrained XGBoost category.
        """
        if self._program_embeddings is None:
            raise RuntimeError("Call index_programs() before rank_programs_multi().")

        present = [(t, w) for t, w in weighted_texts if t and t.strip()]
        if not present:
            return []

        total_weight = sum(w for _, w in present)
        n = len(self._program_ids)
        combined = np.zeros(n)
        for text, weight in present:
            embedding = self.model.encode(text, convert_to_tensor=True)
            scores = util.cos_sim(embedding, self._program_embeddings)[0].cpu().numpy()
            combined += (weight / total_weight) * scores

        ranked_idx = np.argsort(-combined)[:top_k]
        return [(self._program_ids[i], float(combined[i])) for i in ranked_idx]

