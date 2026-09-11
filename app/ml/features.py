"""
Shared feature engineering for the XGBoost structured-data model.

CRITICAL: both scripts/generate_synthetic_training_data.py (offline,
builds the training set) and app/ml/xgboost_model.py (online, scores a
real request) import bucket_features() from HERE. If they ever compute
features differently, the model will be trained on one distribution and
scored on another, silently. Don't duplicate this logic — extend it here.

Raw fields these buckets are built from (see users table):
  department, designation, position, teaching_status, yearsInLSPU,
  educationalAttainment
"""
from __future__ import annotations

# The training categories, matching training_programs.category exactly
# (see scripts/seed_training_programs.py). If you add/rename a category
# in the catalog, update this list too, and retrain.
#
# 2026-09-09 - rebuilt from scratch against the REAL, live catalog
# categories (SELECT DISTINCT category FROM training_programs) instead of
# trusting this list. Found a real, previously undiscovered gap: 13 of the
# catalog's 23 real categories (Agriculture, Business, Customer Service,
# Engineering, Fisheries, Food Science and Nutrition, Hospitality and
# Tourism, Law, Mathematics, Natural Sciences, Nursing and Health,
# Physical Education and Sports, Technical Education) had NEVER had a
# trained regressor at all - every program in them has been running in
# the untrained-category fallback (structured weight reallocated to text,
# see recommender.py's category_is_trained comment) this entire time, not
# just the Natural Sciences/Fisheries entries added tonight. Separately,
# 4 of the old entries here (Records Management, Finance & Compliance,
# Public Service, Health & Nutrition) don't match ANY real catalog
# category string - dead weight from an earlier naming scheme that never
# got reconciled when the catalog was actually seeded, training real
# regressors for categories no program has ever belonged to. Both problems
# fixed the same way: this list is now exactly
# `SELECT DISTINCT category FROM training_programs WHERE training_type IN
# ('Workshop','Seminar','Webinar','Conference')`, checked directly against
# the live database rather than assumed. Retrain after any future catalog
# category change using that same query, not by editing this list by hand.
CATEGORIES = [
    "Administration",
    "Agriculture",
    "Assessment",
    "Business",
    "Communication",
    "Criminal Justice",
    "Customer Service",
    "Engineering",
    "Fisheries",
    "Food Science and Nutrition",
    "Gender & Development",
    "Hospitality and Tourism",
    "Law",
    "Leadership",
    "Mathematics",
    "Natural Sciences",
    "Nursing and Health",
    "Pedagogy",
    "Physical Education and Sports",
    "Research",
    "Student Affairs",
    "Technical Education",
    "Technology",
]

# Maps the many real spellings/variants seen in the DB (see the messy
# `department` column — some rows store "CCS", others store the full
# college name, sometimes duplicated like "College of Arts and
# ScienceCollege of Arts and Sciences") down to a canonical short code.
# Extend this as you find more variants in real data.
DEPARTMENT_CODE_MAP = {
    "ccs": "CCS", "college of computer studies": "CCS",
    "cas": "CAS", "college of arts and sciences": "CAS",
    # exact mangled duplicate seen in the live DB (department id=66) -
    # see scripts/audit_department_values.py if you want to re-check
    # this against current data before relying on it.
    "college of arts and sciencecollege of arts and sciences": "CAS",
    "cbaa": "CBAA", "college of business, administration and accountancy": "CBAA",
    "ccje": "CCJE", "college of criminal justice education": "CCJE",
    "coe": "COE", "college of engineering": "COE",
    "cit": "CIT", "college of industrial technology": "CIT",
    "cfnd": "CFND", "college of food, nutrition and dietetics": "CFND",
    "cof": "COF", "college of fisheries": "COF",
    "chmt": "CHMT",
    "cte": "CTE", "college of teacher education": "CTE",
    "conah": "CONAH", "college of nursing and allied health": "CONAH",
    "col": "COL", "college of law": "COL",
    "ca": "CA", "college of agriculture": "CA",
    # Not a college - a non-teaching administrative unit, but real users
    # are assigned to it (3 of 18 live accounts as of 2026-08-19), so it
    # needs its own canonical code rather than falling through to a
    # truncated raw-string "category" that XGBoost never saw in training.
    "main admin": "ADMIN",
    # 2026-09-02 - the PHP side's profile/registration forms now offer
    # non-teaching staff a curated dropdown of specific offices instead of
    # free text (see CLAUDE.md). Each resolves to the same ADMIN bucket
    # XGBoost was trained on, rather than falling to UNKNOWN the way an
    # arbitrary self-typed office string still does. Kept in sync with
    # TNA_COLLEGE_CODE_MAP in ml_recommendations.php.
    "registrar's office": "ADMIN",
    "accounting/budget office": "ADMIN",
    "human resource management office (hrmo)": "ADMIN",
    "supply/property office": "ADMIN",
    "library": "ADMIN",
    # 2026-09-07 - real 13 offices, given directly by HR (Dr. Imee
    # Prescilla P. Sanchez, HRMO), replacing the placeholder 5 above as
    # the dropdown's actual options. The placeholder 5 stay mapped too -
    # any account registered before this date still has one of those
    # exact values stored.
    "office of the campus director": "ADMIN",
    "guidance counselor": "ADMIN",
    "disbursing and cashiering": "ADMIN",
    "records office": "ADMIN",
    "general services unit": "ADMIN",
    "library services": "ADMIN",
    "supply": "ADMIN",
    "admission and registrarship": "ADMIN",
    "accounting office": "ADMIN",
    "budget and finance": "ADMIN",
    "human resource management": "ADMIN",
    "medical and dental services": "ADMIN",
    "procurement": "ADMIN",
}

# Departments where Technology training is inherently more relevant
# regardless of individual role.
TECH_ADJACENT_DEPARTMENTS = {"CCS", "CIT", "COE"}

# Departments where the new domain-specific categories (2026-08-29) are
# inherently more relevant regardless of individual role - mirrors
# TECH_ADJACENT_DEPARTMENTS's reasoning exactly. Deliberately narrow
# (one college each): unlike Technology or Records Management, these
# aren't skills that generalize across the university - a Health &
# Nutrition training is specifically for CFND's own discipline, not a
# broadly useful staff skill.
NUTRITION_ADJACENT_DEPARTMENTS = {"CFND"}
CRIMINAL_JUSTICE_ADJACENT_DEPARTMENTS = {"CCJE"}

# The central non-teaching administrative office (Registrar, Finance, HR,
# Records, etc. - anyone whose department resolves to "ADMIN" rather than
# a teaching college). Records Management, Finance & Compliance, and
# (to a lesser extent) Public Service trainings are disproportionately
# relevant here, mirroring the real 2025 TNA data: ADMIN submitted more
# COA/records/budgeting requests than any single teaching college.
CENTRAL_ADMIN_DEPARTMENTS = {"ADMIN"}

LEADERSHIP_KEYWORDS = ("chair", "head", "dean", "coordinator", "director", "supervisor")


def canonical_department(raw: str | None) -> str:
    """
    Maps a raw department/office string to one of the categorical levels
    XGBoost was actually trained on. Any value not in DEPARTMENT_CODE_MAP
    - including every self-typed non-teaching office (HR, Registrar,
    Library, Motor Pool, etc., entered via the profile's "Other" field,
    since there's no fixed dropdown of offices) - falls back to the
    generic "UNKNOWN" bucket, which the synthetic training set includes
    specifically for this. The old fallback returned a truncated version
    of the raw text instead (e.g. "OSAS"), which is guaranteed to be a
    category the model never saw, silently dropping the entire
    structured/role-based half of that person's recommendation score
    (see CLAUDE.md - this was found via the "OSAS" test account).
    """
    if not raw:
        return "UNKNOWN"
    key = raw.strip().lower()
    return DEPARTMENT_CODE_MAP.get(key, "UNKNOWN")


def years_bucket(raw: str | int | None) -> str:
    try:
        years = int(raw)
    except (TypeError, ValueError):
        return "unknown"
    if years <= 2:
        return "junior"
    if years <= 7:
        return "mid"
    return "senior"


def attainment_bucket(raw: str | None) -> str:
    if not raw:
        return "unknown"
    text = raw.lower()
    if "doctorate" in text or "phd" in text:
        return "doctorate"
    if "master" in text:
        return "masters"
    if "bachelor" in text:
        return "bachelors"
    return "unknown"


def is_leadership_role(designation: str | None, position: str | None) -> bool:
    text = f"{designation or ''} {position or ''}".lower()
    return any(kw in text for kw in LEADERSHIP_KEYWORDS)


def is_teaching(teaching_status: str | None) -> bool:
    return (teaching_status or "").strip().lower() == "teaching"


def bucket_features(raw: dict) -> dict:
    """
    raw: dict with keys department, designation, position, teaching_status,
    years_in_lspu, educational_attainment (any may be None/missing).

    Returns the engineered feature dict that gets fed to XGBoost. Keys
    here must match FEATURE_COLUMNS in app/ml/xgboost_model.py exactly.
    """
    dept = canonical_department(raw.get("department"))
    return {
        "department": dept,
        "is_tech_department": dept in TECH_ADJACENT_DEPARTMENTS,
        "is_nutrition_department": dept in NUTRITION_ADJACENT_DEPARTMENTS,
        "is_criminal_justice_department": dept in CRIMINAL_JUSTICE_ADJACENT_DEPARTMENTS,
        "is_central_admin_department": dept in CENTRAL_ADMIN_DEPARTMENTS,
        "teaching_status": "Teaching" if is_teaching(raw.get("teaching_status")) else "Non-teaching",
        "years_bucket": years_bucket(raw.get("years_in_lspu")),
        "attainment_bucket": attainment_bucket(raw.get("educational_attainment")),
        "is_leadership": is_leadership_role(raw.get("designation"), raw.get("position")),
    }


FEATURE_COLUMNS = [
    "department",
    "is_tech_department",
    "is_nutrition_department",
    "is_criminal_justice_department",
    "is_central_admin_department",
    "teaching_status",
    "years_bucket",
    "attainment_bucket",
    "is_leadership",
]

# Which of the above are categorical (need dtype='category' for XGBoost's
# native categorical support) vs already boolean/numeric.
CATEGORICAL_COLUMNS = ["department", "teaching_status", "years_bucket", "attainment_bucket"]

