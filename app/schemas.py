"""
Pydantic models defining the API's request/response contract.
Keep this in sync with what training_recommendations.php sends/expects.
"""
from pydantic import BaseModel


class RecommendationRequest(BaseModel):
    user_id: int
    # Structured signals (mirrors users table columns)
    department: str | None = None
    designation: str | None = None
    position: str | None = None
    teaching_status: str | None = None
    years_in_lspu: str | None = None
    educational_attainment: str | None = None
    # specialization is collected as "structured data" per the capstone
    # paper, but it's free text with very high cardinality (specific
    # field names, not a small fixed set) rather than a clean XGBoost
    # category, so it's routed into the SBERT text query instead of the
    # structured feature set - see recommend.py.
    specialization: str | None = None
    # Free text signals (from assessments table)
    desired_skills: str | None = None
    comments: str | None = None
    training_history: str | None = None


class TrainingRecommendation(BaseModel):
    program_id: int
    title: str
    description: str
    training_type: str | None = None
    score: float  # combined relevance score, 0-1
    reason: str | None = None  # short human-readable explanation
    reference_link: str | None = None  # where to actually take the training


class RecommendationResponse(BaseModel):
    user_id: int
    recommendations: list[TrainingRecommendation]


class SimilarityCandidate(BaseModel):
    id: int  # opaque caller-side id (e.g. a training_recommendations.id), echoed back unchanged
    text: str


class SimilarityCheckRequest(BaseModel):
    query_text: str
    candidates: list[SimilarityCandidate]


class SimilarityResult(BaseModel):
    id: int
    score: float  # cosine similarity, roughly 0-1 for this model


class SimilarityCheckResponse(BaseModel):
    results: list[SimilarityResult]

