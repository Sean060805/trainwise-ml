"""
Wraps the trained XGBoost models that score training-category relevance
from structured employee data. See scripts/train_xgboost.py for how the
model file this loads gets created, and CLAUDE.md Phase 2 for the design
rationale (synthetic bootstrap labels, cold-start strategy).
"""
from __future__ import annotations

import logging
import os
import joblib
import pandas as pd

from app.config import settings
from app.ml.features import CATEGORIES, FEATURE_COLUMNS, CATEGORICAL_COLUMNS, bucket_features

MODEL_PATH = os.path.join(settings.model_dir, "xgboost_model.joblib")

logger = logging.getLogger(__name__)


class XGBoostRecommender:
    def __init__(self):
        self.models: dict = {}
        if os.path.exists(MODEL_PATH):
            self.models = joblib.load(MODEL_PATH)

    def is_trained(self) -> bool:
        return len(self.models) > 0

    def predict_category_scores(self, raw_user_features: dict) -> dict[str, float]:
        """
        raw_user_features: dict with department, designation, position,
        teaching_status, years_in_lspu, educational_attainment (any may
        be missing/None — bucket_features() handles that).

        Returns {category_name: relevance_score} for each known
        training category. Returns {} if no model has been trained yet
        (caller should treat that as "fall back to text-only ranking").
        """
        if not self.is_trained():
            return {}

        engineered = bucket_features(raw_user_features)
        row = pd.DataFrame([engineered], columns=FEATURE_COLUMNS)
        for col in CATEGORICAL_COLUMNS:
            row[col] = row[col].astype("category")

        scores = {}
        for category in CATEGORIES:
            model = self.models.get(category)
            if model is None:
                continue
            # XGBoost needs the same categorical levels seen at train
            # time. A brand-new department value not seen during
            # training comes through as an unseen category level -
            # contrary to what an earlier version of this comment
            # claimed, XGBoost's native categorical support does NOT
            # silently handle this: it raises XGBoostError and would
            # 500 the entire /recommend request for that user (found via
            # scripts/benchmark_response_time.py against a real messy
            # department value, e.g. "College of Arts and Science..."
            # duplicated string seen in the live DB). Degrade to "no
            # structured signal for this category" instead of crashing -
            # the text-similarity score still applies for these users.
            try:
                prediction = model.predict(row)[0]
            except Exception as e:
                logger.warning(
                    "XGBoost prediction failed for category '%s' (likely an "
                    "unseen categorical value in %s): %s",
                    category, engineered, e,
                )
                continue
            scores[category] = float(max(0.0, min(1.0, prediction)))

        return scores

