"""
Tests for XGBoostRecommender (app/ml/xgboost_model.py) against the real
trained model artifact in models_store/. Focuses on the graceful-
degradation behavior added after the live crash-on-unseen-department bug
(see CLAUDE.md) - this must never raise, only ever return a (possibly
partial) score dict.
"""
from app.ml.features import CATEGORIES
from app.ml.xgboost_model import XGBoostRecommender


def test_trained_model_loads_from_disk():
    model = XGBoostRecommender()
    assert model.is_trained() is True


def test_predict_returns_scores_in_valid_range():
    model = XGBoostRecommender()
    scores = model.predict_category_scores({
        "department": "CCS",
        "designation": "Software Engineer",
        "position": None,
        "teaching_status": "Teaching",
        "years_in_lspu": "13",
        "educational_attainment": "Doctorate Degree (Completed)",
    })
    assert len(scores) > 0
    for category, score in scores.items():
        assert category in CATEGORIES
        assert 0.0 <= score <= 1.0


def test_completely_empty_profile_does_not_crash():
    model = XGBoostRecommender()
    scores = model.predict_category_scores({})
    # Every value must still be a valid, bounded float even with an
    # all-"unknown"/"UNKNOWN" bucketed profile.
    for score in scores.values():
        assert 0.0 <= score <= 1.0


def test_mangled_live_db_department_does_not_crash():
    # The exact corrupted duplicate string that used to 500 the whole
    # /recommend request before the try/except fix in predict_category_scores.
    model = XGBoostRecommender()
    scores = model.predict_category_scores({
        "department": "College of Arts and ScienceCollege of Arts and Sciences",
        "designation": "Instructor",
        "position": None,
        "teaching_status": "Teaching",
        "years_in_lspu": "5",
        "educational_attainment": "Master's Degree",
    })
    for score in scores.values():
        assert 0.0 <= score <= 1.0


def test_brand_new_unseen_department_does_not_crash():
    model = XGBoostRecommender()
    scores = model.predict_category_scores({
        "department": "College of Completely Fictional Studies",
        "designation": "Instructor",
        "position": None,
        "teaching_status": "Teaching",
        "years_in_lspu": "5",
        "educational_attainment": "Bachelor's Degree",
    })
    for score in scores.values():
        assert 0.0 <= score <= 1.0


def test_untrained_model_returns_empty_dict(monkeypatch):
    model = XGBoostRecommender()
    monkeypatch.setattr(model, "models", {})
    assert model.is_trained() is False
    assert model.predict_category_scores({"department": "CCS"}) == {}
