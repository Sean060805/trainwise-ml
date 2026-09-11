import json

from fastapi import APIRouter, HTTPException

from app.database import fetch_all
from app.schemas import RecommendationRequest, RecommendationResponse
from app.ml.xgboost_model import XGBoostRecommender
from app.ml.text_similarity import TextSimilarityMatcher
from app.ml.tna_matcher import Tna2025Matcher
from app.ml.recommender import Recommender
from app.ml.features import canonical_department

router = APIRouter()


def extract_training_titles(raw_history: str | None) -> str | None:
    """
    2026-09-09 - assessments.training_history arrives from the PHP side
    as the JSON-serialized array it's actually stored as (e.g.
    '[{"date":"2024-06-10","training":"Basic Molecular Biology
    Techniques and Data Analysis","venue":"Manila","start_time":"08:00",
    ...}]'), not plain text. Before this, that whole JSON string was
    embedded as-is - every key name and brace ("date", "venue",
    "start_time") became part of what SBERT compared against the
    catalog, diluting a signal that's already deliberately weighted low
    (see recommender.py's HISTORY_WEIGHT) with noise that has nothing to
    do with what training was actually taken. Pulls out just the
    "training" field's text from each entry. Fails open - returns the
    original string unchanged if it isn't valid JSON in this shape, so a
    malformed or legacy value degrades to the old behavior instead of
    crashing or silently disappearing.
    """
    if not raw_history:
        return raw_history
    try:
        entries = json.loads(raw_history)
        if isinstance(entries, list):
            titles = [
                e.get("training", "") for e in entries
                if isinstance(e, dict) and e.get("training")
            ]
            if titles:
                return " ".join(titles)
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass
    return raw_history

# IMPORTANT: these are intentionally NOT constructed here at import time.
# Building TextSimilarityMatcher() loads the SBERT model, which on first
# run downloads ~80MB from Hugging Face — if that happened at import
# time, uvicorn would never get to bind the port or print its startup
# banner, and http://localhost:8000 would look "unreachable" the whole
# time it's downloading. Instead, app/main.py's startup event calls
# load_programs_and_index() AFTER the server is already listening, so
# you get visible log output and a responsive port immediately.
_xgb = None
_matcher = None
_tna_matcher = None
_recommender = None


def load_programs_and_index():
    """Called once at startup (see app/main.py) to build the models and warm the SBERT index."""
    global _xgb, _matcher, _tna_matcher, _recommender

    print("[recommend] Initializing models (this runs once, after the server has started)...")
    _xgb = XGBoostRecommender()
    _matcher = TextSimilarityMatcher()  # this is where the SBERT download/load happens
    _tna_matcher = Tna2025Matcher()
    _recommender = Recommender(_xgb, _matcher, _tna_matcher)

    # Workshop/Seminar/Webinar/Conference programs are recommended, per an
    # explicit 2026-08-28 decision (revised 2026-08-29): this pipeline
    # exists to pool group, HR-arranged, scheduled training into one
    # negotiated booking - that's only meaningful for formats that actually
    # need coordination (a provider/venue/registration to arrange). The
    # 2026-08-29 revision added Webinar and Conference to that list after
    # confirming with the project's real HR context that these ARE
    # genuinely HR-coordinated at LSPU (paid registration, limited seats,
    # group representation) - the original assumption that lumped Webinar
    # in with a self-paced Online Course was wrong. A true self-paced
    # Online Course still has no such coordination need - an employee can
    # just take it on their own, which is exactly the free-self-study case
    # the whole redesign moved away from. Filtered at the source (not just
    # hidden in the UI) so Online Course can never be indexed, matched, or
    # recommended at all.
    # 2026-09-08 fix - the 2026-09-01 comment that used to be here claimed
    # training_programs had no reference_link column and that omitting it
    # from this SELECT was the correct fix. That's no longer true (the
    # column exists now, and a whole separate session verified and filled
    # in real links for the catalog - see CLAUDE.md's catalog-audit note)
    # - the column just quietly stopped being read here, meaning every
    # recommendation response has been returning reference_link: null
    # regardless of what's actually on file. target_department was never
    # selected either, despite being genuinely populated for a few
    # programs (e.g. the CCS-only "Data Structures, Algorithms, and
    # Programming Fundamentals") - recommender.py has no way to honor a
    # department restriction it never receives, so those programs leak
    # into every other department's recommendations. Both fixed by
    # selecting the columns that already exist.
    programs = fetch_all("""
        SELECT id, title, description, training_type, category, target_department, reference_link
        FROM training_programs
        WHERE training_type IN ('Workshop', 'Seminar', 'Webinar', 'Conference')
    """)
    if programs:
        program_dicts = [{"id": p["id"], "description": p["description"]} for p in programs]
        _matcher.index_programs(program_dicts)
        # See TextSimilarityMatcher.category_affinity()'s docstring - a
        # person's specialization is compared against these short category
        # labels instead of full program descriptions, which is a much
        # cleaner signal than description-level matching turned out to be.
        _matcher.index_categories(sorted({p["category"] for p in programs if p.get("category")}))

        # Fail open: if tna_2025_demand doesn't exist yet (seed script not
        # run) or the query errors for any reason, index nothing - every
        # get_boost() call then returns 0.0, degrading this feature to
        # "off" rather than crashing startup.
        try:
            tna_rows = fetch_all("SELECT college_code, title FROM tna_2025_demand")
        except Exception as e:
            print(f"[recommend] tna_2025_demand unavailable, TNA boost disabled: {e}")
            tna_rows = []
        titles_by_college: dict[str, list[str]] = {}
        for row in tna_rows:
            titles_by_college.setdefault(row["college_code"], []).append(row["title"])

        # Only 4 of 13 colleges submitted anything official for 2025. For
        # every other college, fall back to what its own employees have
        # already said via their own assessment submissions - real data,
        # just not the official channel. Skipped entirely for a college
        # that already has official data (index() itself also guards
        # this, but no point querying/embedding text we'd throw away).
        try:
            assessment_rows = fetch_all("""
                SELECT u.department, a.desired_skills
                FROM assessments a
                JOIN users u ON u.id = a.user_id
                WHERE a.desired_skills IS NOT NULL AND a.desired_skills != ''
            """)
        except Exception as e:
            print(f"[recommend] assessments lookup for self-reported TNA fallback failed: {e}")
            assessment_rows = []
        self_reported_by_college: dict[str, list[str]] = {}
        for row in assessment_rows:
            code = canonical_department(row["department"])
            if code in titles_by_college:
                continue  # official data already covers this college
            self_reported_by_college.setdefault(code, []).append(row["desired_skills"])

        _tna_matcher.index(titles_by_college, self_reported_by_college, program_dicts)
        if titles_by_college:
            print(f"[recommend] TNA-2025 boost indexed (official) for colleges: {sorted(titles_by_college.keys())}")
        if self_reported_by_college:
            print(f"[recommend] TNA-2025 boost indexed (self-reported fallback) for colleges: {sorted(self_reported_by_college.keys())}")

    print(f"[recommend] Ready — {len(programs)} training programs indexed.")
    return {p["id"]: p for p in programs}


@router.post("/recommend", response_model=RecommendationResponse)
def recommend(payload: RecommendationRequest):
    from app.main import PROGRAMS_BY_ID  # populated at startup

    if not PROGRAMS_BY_ID:
        raise HTTPException(
            status_code=503,
            detail="No training_programs in the database yet — run scripts/seed_training_programs.py first.",
        )

    user_features = {
        "department": payload.department,
        "designation": payload.designation,
        "position": payload.position,
        "teaching_status": payload.teaching_status,
        "years_in_lspu": payload.years_in_lspu,
        "educational_attainment": payload.educational_attainment,
    }
    # specialization and training_history are structured/free-text fields
    # the paper lists as inputs but which don't fit XGBoost's categorical
    # features cleanly (see schemas.py).
    #
    # 2026-09-09 - these used to be concatenated together with
    # desired_skills/comments into one combined query string before being
    # embedded as a single SBERT query. Found live, via a real CAS Biology
    # instructor's result, that this let training_history's incidental
    # wording ("...and Data Analysis") redirect the whole match toward
    # unrelated IT catalog entries, even though his actual desired_skills
    # text was specific and on topic on its own. Now kept as separate,
    # explicitly lower-weighted signals - see recommender.py's
    # DESIRED_TEXT_WEIGHT/SPECIALIZATION_WEIGHT/HISTORY_WEIGHT.
    #
    # 2026-09-03 - training_history often arrives as the literal string
    # "[]" (an empty JSON array serialized as text, from the PHP side's
    # default "no prior trainings logged" state) rather than being
    # empty/None. That guard is still needed here for the same reason as
    # before: "[]" is a non-empty string, so without it, it would still
    # count as real history text and pull in HISTORY_WEIGHT's share for
    # nothing.
    training_history = payload.training_history
    if training_history is not None and training_history.strip() in ("[]", ""):
        training_history = None
    training_history = extract_training_titles(training_history)
    query_text = " ".join(filter(None, [
        payload.desired_skills,
        payload.comments,
    ]))

    college_code = canonical_department(payload.department)
    ranked = _recommender.recommend(
        user_features=user_features,
        query_text=query_text,
        specialization_text=payload.specialization or "",
        history_text=training_history or "",
        programs_by_id=PROGRAMS_BY_ID,
        college_code=college_code,
    )

    return RecommendationResponse(user_id=payload.user_id, recommendations=ranked)

