"""
General-purpose text similarity endpoint, separate from /recommend's
catalog-indexed matching. Used by TrainWise's HR demand-aggregation
pipeline (get_demand_shortlist.php) to hard-exclude someone from an AI
Shortlist if they've already completed a training that's topically
similar to the one being shortlisted for - not just deprioritize them,
per the 2026-08-26 requirement that this be an actual exclusion.

Deliberately NOT reusing TextSimilarityMatcher - that class is built
around indexing the whole training_programs catalog once at startup and
ranking a query against it. This is a one-off pairwise comparison
between two arbitrary pieces of text (an approved demand's description
vs. an employee's prior completed trainings), so it just uses the same
cached SBERT model directly.
"""
from fastapi import APIRouter
from sentence_transformers import util

from app.ml.text_similarity import get_model
from app.schemas import SimilarityCheckRequest, SimilarityCheckResponse, SimilarityResult

router = APIRouter()


@router.post("/similarity_check", response_model=SimilarityCheckResponse)
def similarity_check(payload: SimilarityCheckRequest):
    if not payload.candidates:
        return SimilarityCheckResponse(results=[])

    model = get_model()
    query_embedding = model.encode(payload.query_text, convert_to_tensor=True)
    candidate_embeddings = model.encode(
        [c.text for c in payload.candidates], convert_to_tensor=True
    )
    scores = util.cos_sim(query_embedding, candidate_embeddings)[0].cpu().numpy()

    return SimilarityCheckResponse(
        results=[
            SimilarityResult(id=c.id, score=float(s))
            for c, s in zip(payload.candidates, scores)
        ]
    )
