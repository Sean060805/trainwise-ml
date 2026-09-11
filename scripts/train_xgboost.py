"""
Trains one XGBoost regressor per training category on the synthetic
bootstrap dataset (see generate_synthetic_training_data.py — run that
first if data/processed/synthetic_training_data.csv doesn't exist yet).

For each category:
  1. Splits into 80% train / 20% test (matches the capstone paper's
     stated data-splitting methodology).
  2. Runs a 3-fold cross-validated grid search over a small
     hyperparameter grid (n_estimators, max_depth, learning_rate) on
     the training split only, to pick the best-performing config.
  3. Evaluates the chosen model on the held-out test split (never seen
     during grid search) with MAE, RMSE, and R^2.

Saves a dict of {category_name: trained_model} to
models_store/xgboost_model.joblib, which app/ml/xgboost_model.py loads
at startup, plus a written evaluation report to
reports/xgboost_evaluation.md documenting the results.

    python scripts/train_xgboost.py
"""
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

from app.config import settings
from app.ml.features import CATEGORIES, FEATURE_COLUMNS, CATEGORICAL_COLUMNS

DATA_PATH = "data/processed/synthetic_training_data.csv"
MODEL_PATH = os.path.join(settings.model_dir, "xgboost_model.joblib")
REPORT_PATH = os.path.join("reports", "xgboost_evaluation.md")

PARAM_GRID = {
    "n_estimators": [100, 200, 300],
    "max_depth": [3, 4, 5],
    "learning_rate": [0.03, 0.05, 0.1],
}


def load_data() -> pd.DataFrame:
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"{DATA_PATH} not found — run "
            "scripts/generate_synthetic_training_data.py first."
        )
    df = pd.read_csv(DATA_PATH)
    for col in CATEGORICAL_COLUMNS:
        df[col] = df[col].astype("category")
    return df


def train_one_category(df: pd.DataFrame, category: str) -> tuple[XGBRegressor, dict]:
    X = df[FEATURE_COLUMNS]
    y = df[category]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    base_model = XGBRegressor(
        enable_categorical=True,
        tree_method="hist",
        random_state=42,
    )
    search = GridSearchCV(
        base_model,
        PARAM_GRID,
        scoring="neg_mean_absolute_error",
        cv=3,
        n_jobs=1,
    )
    search.fit(X_train, y_train)
    best_model = search.best_estimator_

    predictions = best_model.predict(X_test)
    metrics = {
        "category": category,
        "best_params": search.best_params_,
        "cv_mae": -search.best_score_,
        "test_mae": mean_absolute_error(y_test, predictions),
        "test_rmse": mean_squared_error(y_test, predictions) ** 0.5,
        "test_r2": r2_score(y_test, predictions),
        "n_train": len(X_train),
        "n_test": len(X_test),
    }
    return best_model, metrics


def write_report(rows: list[dict], n_total: int):
    os.makedirs("reports", exist_ok=True)
    lines = []
    lines.append("# XGBoost Structured-Data Model — Evaluation Report\n\n")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n")
    lines.append(f"Dataset: `{DATA_PATH}` ({n_total} synthetic bootstrap rows)\n\n")

    lines.append("## Methodology\n\n")
    lines.append(
        "- 80/20 train/test split per category (`random_state=42`), matching "
        "the capstone paper's stated data-splitting methodology.\n"
        "- Hyperparameter selection via 3-fold cross-validated grid search on "
        "the training split only. Grid: `n_estimators` in {100, 200, 300}, "
        "`max_depth` in {3, 4, 5}, `learning_rate` in {0.03, 0.05, 0.1} — "
        "27 configurations evaluated per category, selected by lowest mean "
        "absolute error across folds.\n"
        "- Final reported metrics (MAE, RMSE, R²) are computed on the "
        "held-out 20% test split, which the grid search never saw.\n\n"
    )

    lines.append("## Note on metric choice\n\n")
    lines.append(
        "The capstone paper's Table 11 specifies Accuracy/Precision/Recall/"
        "F1-Score for the XGBoost component — these are classification "
        "metrics. This model is implemented as a **regressor** (it predicts "
        "a continuous 0–1 relevance score per category, used to rank "
        "training programs), which is the standard design for a "
        "recommender system's structured-data scoring component and is not "
        "naturally a classification task. MAE, RMSE, and R² are the correct "
        "metrics for that framing. **Recommend updating Table 11 to reflect "
        "MAE/RMSE/R² instead of Accuracy/Precision/Recall/F1.**\n\n"
    )

    lines.append("## Per-category results\n\n")
    lines.append("| Category | Best params | CV MAE | Test MAE | Test RMSE | Test R² | Train rows | Test rows |\n")
    lines.append("|---|---|---|---|---|---|---|---|\n")
    for r in rows:
        p = r["best_params"]
        params_str = f"n_estimators={p['n_estimators']}, max_depth={p['max_depth']}, lr={p['learning_rate']}"
        lines.append(
            f"| {r['category']} | {params_str} | {r['cv_mae']:.4f} | "
            f"{r['test_mae']:.4f} | {r['test_rmse']:.4f} | {r['test_r2']:.4f} | "
            f"{r['n_train']} | {r['n_test']} |\n"
        )

    avg_mae = sum(r["test_mae"] for r in rows) / len(rows)
    avg_rmse = sum(r["test_rmse"] for r in rows) / len(rows)
    avg_r2 = sum(r["test_r2"] for r in rows) / len(rows)
    lines.append(
        f"\n**Average across all {len(rows)} categories:** "
        f"MAE = {avg_mae:.4f}, RMSE = {avg_rmse:.4f}, R² = {avg_r2:.4f}\n\n"
    )

    lines.append("## Interpretation\n\n")
    lines.append(
        "Scores are on a 0–1 relevance scale, so an MAE of ~0.03–0.06 means "
        "predictions are typically within a few percentage points of the "
        "synthetic target score. Because the targets are rule-based/"
        "synthetic (see `scripts/generate_synthetic_training_data.py`), "
        "these numbers confirm the model successfully learned the encoded "
        "domain rules — they do **not** by themselves prove those rules "
        "match real LSPU staff training needs. Treat this as validation of "
        "the *modeling pipeline*, not of the *domain rules*. Revisit the "
        "rules in `generate_synthetic_training_data.py` against real "
        "institutional judgment, and retrain once real usage/feedback data "
        "accumulates.\n"
    )

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)


def main():
    print("Loading synthetic training data...")
    df = load_data()
    print(f"Loaded {len(df)} rows.")

    models = {}
    report_rows = []
    print(f"\n{'Category':<20} {'Best params':<45} {'Test MAE':<10} {'Test R2':<10}")
    print("-" * 90)
    for category in CATEGORIES:
        model, metrics = train_one_category(df, category)
        models[category] = model
        report_rows.append(metrics)
        p = metrics["best_params"]
        params_str = f"n_est={p['n_estimators']},depth={p['max_depth']},lr={p['learning_rate']}"
        print(f"{category:<20} {params_str:<45} {metrics['test_mae']:<10.4f} {metrics['test_r2']:<10.4f}")

    os.makedirs(settings.model_dir, exist_ok=True)
    joblib.dump(models, MODEL_PATH)
    write_report(report_rows, len(df))

    print(f"\nSaved {len(models)} category models -> {MODEL_PATH}")
    print(f"Saved evaluation report -> {REPORT_PATH}")
    print(
        "\nNote: low MAE here mainly confirms the model learned the "
        "synthetic rules (expected, since that's literally the training "
        "signal) — it does NOT yet confirm the rules themselves are "
        "correct for real LSPU staff. Validate the rules in "
        "generate_synthetic_training_data.py against real institutional "
        "judgment, and revisit once real usage data exists."
    )


if __name__ == "__main__":
    main()
