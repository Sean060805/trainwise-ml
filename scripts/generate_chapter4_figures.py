"""
Generates the figures needed for the capstone paper's Chapter 4 (Results
and Discussion) ML evaluation section: XGBoost actual-vs-predicted fit,
XGBoost feature importance, and an SBERT similarity/ranking summary.

Uses the actual trained models and the actual held-out test split (same
random_state=42 as train_xgboost.py, so these are the real test-set
predictions, not illustrative/fake data.

    python scripts/generate_chapter4_figures.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split

from app.config import settings
from app.ml.features import CATEGORIES, FEATURE_COLUMNS, CATEGORICAL_COLUMNS

DATA_PATH = "data/processed/synthetic_training_data.csv"
MODEL_PATH = os.path.join(settings.model_dir, "xgboost_model.joblib")
FIG_DIR = os.path.join("reports", "figures")

# LSPU-adjacent palette, consistent with the rest of the paper's figures
ROYAL = "#1A4B8C"
GOLD = "#C99A3D"
FOREST = "#0D6B4D"
INK = "#1B2A41"
GRID = "#E4D9C3"


def load_data():
    df = pd.read_csv(DATA_PATH)
    for col in CATEGORICAL_COLUMNS:
        df[col] = df[col].astype("category")
    return df


def actual_vs_predicted_figure(df, models):
    # 2026-09-08 fix - this used to hardcode a 2x4 (8-slot) grid for the
    # original 8 categories. CATEGORIES has since grown to 14 (Records
    # Management, Finance & Compliance, Public Service, Health &
    # Nutrition, Criminal Justice, Gender & Development added) - a fixed
    # 8-slot grid would either throw an IndexError once i reached 8, or
    # silently drop the 6 new categories from the figure entirely if the
    # loop were guarded some other way. Compute the grid size from the
    # actual category count instead of a hardcoded number, so this keeps
    # working if the category set changes again later.
    n = len(CATEGORIES)
    ncols = 4
    nrows = -(-n // ncols)  # ceiling division
    fig, axes = plt.subplots(nrows, ncols, figsize=(4 * ncols, 4 * nrows))
    axes = axes.flatten()

    for i, category in enumerate(CATEGORIES):
        X = df[FEATURE_COLUMNS]
        y = df[category]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = models[category]
        preds = model.predict(X_test)

        ax = axes[i]
        ax.scatter(y_test, preds, alpha=0.25, s=14, color=ROYAL, edgecolors="none")
        ax.plot([0, 1], [0, 1], linestyle="--", color=GOLD, linewidth=1.5, label="Perfect prediction")
        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.02, 1.02)
        ax.set_title(category, fontsize=11, color=INK, fontweight="bold")
        ax.set_xlabel("Actual (synthetic target)", fontsize=8.5, color=INK)
        ax.set_ylabel("Predicted", fontsize=8.5, color=INK)
        ax.tick_params(labelsize=8)
        ax.grid(True, color=GRID, linewidth=0.6)
        ax.set_facecolor("#FFFFFF")

    # Hide any unused subplot slots (14 categories doesn't fill a 4-wide
    # grid evenly - 14/4 = 3.5, so the grid rounds up to 16 slots and the
    # last 2 would otherwise render as empty axes).
    for j in range(n, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle("XGBoost Regressor — Actual vs. Predicted Relevance Score (Held-Out Test Set)",
                 fontsize=13, color=INK, fontweight="bold", y=1.01)
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "xgboost_actual_vs_predicted.png")
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved {out}")


def feature_importance_figure(models):
    # Average normalized feature importance across all 8 category regressors
    all_importances = []
    feature_names = None
    for category, model in models.items():
        booster_importance = model.feature_importances_
        if feature_names is None:
            feature_names = list(model.feature_names_in_) if hasattr(model, "feature_names_in_") else FEATURE_COLUMNS
        total = booster_importance.sum()
        normalized = booster_importance / total if total > 0 else booster_importance
        all_importances.append(normalized)

    avg_importance = np.mean(all_importances, axis=0)
    order = np.argsort(avg_importance)[::-1]
    sorted_features = [feature_names[i] for i in order]
    sorted_importance = avg_importance[order]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = [ROYAL if i > 0 else GOLD for i in range(len(sorted_features))]
    bars = ax.barh(sorted_features[::-1], sorted_importance[::-1], color=colors[::-1])
    ax.set_xlabel(f"Average Normalized Feature Importance (across {len(models)} category models)", fontsize=9.5, color=INK)
    ax.set_title("XGBoost — Feature Importance", fontsize=13, color=INK, fontweight="bold")
    ax.grid(True, axis="x", color=GRID, linewidth=0.6)
    ax.set_facecolor("#FFFFFF")
    for bar, val in zip(bars, sorted_importance[::-1]):
        ax.text(val + 0.005, bar.get_y() + bar.get_height() / 2, f"{val:.3f}",
                va="center", fontsize=8.5, color=INK)
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "xgboost_feature_importance.png")
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved {out}")

    return list(zip(sorted_features, sorted_importance))


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    df = load_data()
    models = joblib.load(MODEL_PATH)

    actual_vs_predicted_figure(df, models)
    ranking = feature_importance_figure(models)

    print("\nFeature importance ranking (most to least influential):")
    for name, val in ranking:
        print(f"  {name:<22} {val:.4f}")


if __name__ == "__main__":
    main()
