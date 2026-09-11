"""
Unit tests for the pure feature-engineering functions in app/ml/features.py.
These have no DB or model dependency, so they run instantly and pin down
the bucketing rules the XGBoost model was trained against.
"""
from app.ml.features import (
    attainment_bucket,
    bucket_features,
    canonical_department,
    is_leadership_role,
    is_teaching,
    years_bucket,
)


class TestCanonicalDepartment:
    def test_known_short_code(self):
        assert canonical_department("CCS") == "CCS"

    def test_known_full_name_case_insensitive(self):
        assert canonical_department("college of computer studies") == "CCS"

    def test_mangled_duplicate_string_from_live_db(self):
        # Real corrupted value seen in the live DB (department id=66) -
        # this is exactly the input that used to crash XGBoost prediction
        # before the try/except in xgboost_model.py was added.
        assert canonical_department(
            "College of Arts and ScienceCollege of Arts and Sciences"
        ) == "CAS"

    def test_non_college_admin_unit(self):
        assert canonical_department("main admin") == "ADMIN"

    def test_unrecognized_department_falls_back_to_unknown_bucket(self):
        # Any department not in DEPARTMENT_CODE_MAP must land on
        # "UNKNOWN", the generic bucket XGBoost was actually trained on,
        # not a truncated copy of the raw text (which would always be an
        # unseen category).
        assert canonical_department("Some Brand New Department That Never Existed Before") == "UNKNOWN"
        assert canonical_department("OSAS") == "UNKNOWN"

    def test_curated_non_teaching_offices_resolve_to_admin(self):
        # 2026-09-02 - the profile/registration forms now offer non-teaching
        # staff a curated dropdown of 5 specific offices instead of free
        # text (see CLAUDE.md), each an explicit DEPARTMENT_CODE_MAP alias
        # to ADMIN - the opposite of the fallback case above. An
        # unrecognized, self-typed office (still possible via the "Other"
        # fallback) still correctly falls to UNKNOWN per the test above.
        assert canonical_department("Registrar's Office") == "ADMIN"
        assert canonical_department("Accounting/Budget Office") == "ADMIN"
        assert canonical_department("Human Resource Management Office (HRMO)") == "ADMIN"
        assert canonical_department("Supply/Property Office") == "ADMIN"
        assert canonical_department("Library") == "ADMIN"

    def test_none_returns_unknown(self):
        assert canonical_department(None) == "UNKNOWN"

    def test_empty_string_returns_unknown(self):
        assert canonical_department("") == "UNKNOWN"


class TestYearsBucket:
    def test_junior_boundary(self):
        assert years_bucket(0) == "junior"
        assert years_bucket(2) == "junior"

    def test_mid_boundary(self):
        assert years_bucket(3) == "mid"
        assert years_bucket(7) == "mid"

    def test_senior_boundary(self):
        assert years_bucket(8) == "senior"
        assert years_bucket(30) == "senior"

    def test_string_input_from_form_field(self):
        # years_in_lspu comes from a PHP form field, so it arrives as a string
        assert years_bucket("13") == "senior"

    def test_garbage_input_does_not_crash(self):
        assert years_bucket("not a number") == "unknown"
        assert years_bucket(None) == "unknown"


class TestAttainmentBucket:
    def test_doctorate_variants(self):
        assert attainment_bucket("Doctorate Degree (Completed)") == "doctorate"
        assert attainment_bucket("PhD in Education") == "doctorate"

    def test_masters(self):
        assert attainment_bucket("Master's Degree") == "masters"

    def test_bachelors(self):
        assert attainment_bucket("Bachelor of Science") == "bachelors"

    def test_unrecognized_text_falls_back_to_unknown(self):
        assert attainment_bucket("Vocational Diploma") == "unknown"

    def test_none_returns_unknown(self):
        assert attainment_bucket(None) == "unknown"


class TestLeadershipAndTeaching:
    def test_leadership_detected_in_designation(self):
        assert is_leadership_role("Department Chair", None) is True

    def test_leadership_detected_in_position(self):
        assert is_leadership_role(None, "College Dean") is True

    def test_non_leadership_role(self):
        assert is_leadership_role("Instructor", "Faculty Member") is False

    def test_both_none_does_not_crash(self):
        assert is_leadership_role(None, None) is False

    def test_is_teaching_exact_match(self):
        assert is_teaching("Teaching") is True

    def test_is_teaching_case_insensitive(self):
        assert is_teaching("teaching") is True

    def test_is_teaching_non_teaching(self):
        assert is_teaching("Non-teaching") is False

    def test_is_teaching_none(self):
        assert is_teaching(None) is False


class TestBucketFeatures:
    def test_full_profile_produces_expected_keys(self):
        raw = {
            "department": "CCS",
            "designation": "Software Engineer",
            "position": None,
            "teaching_status": "Teaching",
            "years_in_lspu": "13",
            "educational_attainment": "Doctorate Degree (Completed)",
        }
        result = bucket_features(raw)
        assert result == {
            "department": "CCS",
            "is_tech_department": True,
            "is_nutrition_department": False,
            "is_criminal_justice_department": False,
            "is_central_admin_department": False,
            "teaching_status": "Teaching",
            "years_bucket": "senior",
            "attainment_bucket": "doctorate",
            "is_leadership": False,
        }

    def test_missing_fields_do_not_crash(self):
        result = bucket_features({})
        assert result["department"] == "UNKNOWN"
        assert result["is_tech_department"] is False
        assert result["teaching_status"] == "Non-teaching"
        assert result["years_bucket"] == "unknown"
        assert result["attainment_bucket"] == "unknown"
        assert result["is_leadership"] is False

    def test_non_tech_department_flagged_correctly(self):
        result = bucket_features({"department": "College of Arts and Sciences"})
        assert result["department"] == "CAS"
        assert result["is_tech_department"] is False

    def test_nutrition_department_flagged_correctly(self):
        result = bucket_features({"department": "CFND"})
        assert result["is_nutrition_department"] is True
        assert result["is_criminal_justice_department"] is False
        assert result["is_central_admin_department"] is False

    def test_criminal_justice_department_flagged_correctly(self):
        result = bucket_features({"department": "College of Criminal Justice Education"})
        assert result["department"] == "CCJE"
        assert result["is_criminal_justice_department"] is True
        assert result["is_nutrition_department"] is False

    def test_central_admin_department_flagged_correctly(self):
        result = bucket_features({"department": "Main Admin"})
        assert result["department"] == "ADMIN"
        assert result["is_central_admin_department"] is True
        assert result["is_nutrition_department"] is False
        assert result["is_criminal_justice_department"] is False
