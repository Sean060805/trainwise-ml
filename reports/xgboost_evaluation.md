# XGBoost Structured-Data Model — Evaluation Report

Generated: 2026-09-08T18:08:46.391416+00:00

Dataset: `data/processed/synthetic_training_data.csv` (3600 synthetic bootstrap rows)

## Methodology

- 80/20 train/test split per category (`random_state=42`), matching the capstone paper's stated data-splitting methodology.
- Hyperparameter selection via 3-fold cross-validated grid search on the training split only. Grid: `n_estimators` in {100, 200, 300}, `max_depth` in {3, 4, 5}, `learning_rate` in {0.03, 0.05, 0.1} — 27 configurations evaluated per category, selected by lowest mean absolute error across folds.
- Final reported metrics (MAE, RMSE, R²) are computed on the held-out 20% test split, which the grid search never saw.

## Note on metric choice

The capstone paper's Table 11 specifies Accuracy/Precision/Recall/F1-Score for the XGBoost component — these are classification metrics. This model is implemented as a **regressor** (it predicts a continuous 0–1 relevance score per category, used to rank training programs), which is the standard design for a recommender system's structured-data scoring component and is not naturally a classification task. MAE, RMSE, and R² are the correct metrics for that framing. **Recommend updating Table 11 to reflect MAE/RMSE/R² instead of Accuracy/Precision/Recall/F1.**

## Per-category results

| Category | Best params | CV MAE | Test MAE | Test RMSE | Test R² | Train rows | Test rows |
|---|---|---|---|---|---|---|---|
| Administration | n_estimators=200, max_depth=3, lr=0.03 | 0.0395 | 0.0391 | 0.0497 | 0.9766 | 2880 | 720 |
| Agriculture | n_estimators=100, max_depth=3, lr=0.05 | 0.0392 | 0.0398 | 0.0495 | 0.9091 | 2880 | 720 |
| Assessment | n_estimators=100, max_depth=3, lr=0.05 | 0.0408 | 0.0408 | 0.0514 | 0.9644 | 2880 | 720 |
| Business | n_estimators=100, max_depth=3, lr=0.05 | 0.0413 | 0.0409 | 0.0497 | 0.8858 | 2880 | 720 |
| Communication | n_estimators=100, max_depth=3, lr=0.05 | 0.0407 | 0.0383 | 0.0482 | 0.9090 | 2880 | 720 |
| Criminal Justice | n_estimators=100, max_depth=3, lr=0.05 | 0.0393 | 0.0401 | 0.0497 | 0.8953 | 2880 | 720 |
| Customer Service | n_estimators=100, max_depth=3, lr=0.03 | 0.0398 | 0.0420 | 0.0516 | 0.4864 | 2880 | 720 |
| Engineering | n_estimators=100, max_depth=3, lr=0.05 | 0.0398 | 0.0413 | 0.0513 | 0.8777 | 2880 | 720 |
| Fisheries | n_estimators=100, max_depth=3, lr=0.05 | 0.0403 | 0.0398 | 0.0498 | 0.8764 | 2880 | 720 |
| Food Science and Nutrition | n_estimators=100, max_depth=3, lr=0.05 | 0.0404 | 0.0398 | 0.0495 | 0.8875 | 2880 | 720 |
| Gender & Development | n_estimators=100, max_depth=3, lr=0.05 | 0.0402 | 0.0420 | 0.0526 | 0.4439 | 2880 | 720 |
| Hospitality and Tourism | n_estimators=100, max_depth=3, lr=0.05 | 0.0404 | 0.0390 | 0.0484 | 0.8945 | 2880 | 720 |
| Law | n_estimators=100, max_depth=3, lr=0.05 | 0.0391 | 0.0391 | 0.0486 | 0.8809 | 2880 | 720 |
| Leadership | n_estimators=100, max_depth=3, lr=0.05 | 0.0413 | 0.0412 | 0.0521 | 0.9516 | 2880 | 720 |
| Mathematics | n_estimators=100, max_depth=3, lr=0.03 | 0.0395 | 0.0390 | 0.0478 | 0.6448 | 2880 | 720 |
| Natural Sciences | n_estimators=100, max_depth=3, lr=0.05 | 0.0384 | 0.0396 | 0.0495 | 0.7354 | 2880 | 720 |
| Nursing and Health | n_estimators=100, max_depth=3, lr=0.05 | 0.0411 | 0.0390 | 0.0493 | 0.8795 | 2880 | 720 |
| Pedagogy | n_estimators=100, max_depth=3, lr=0.05 | 0.0410 | 0.0405 | 0.0505 | 0.9795 | 2880 | 720 |
| Physical Education and Sports | n_estimators=100, max_depth=3, lr=0.03 | 0.0389 | 0.0389 | 0.0484 | 0.3716 | 2880 | 720 |
| Research | n_estimators=100, max_depth=3, lr=0.05 | 0.0411 | 0.0380 | 0.0478 | 0.9532 | 2880 | 720 |
| Student Affairs | n_estimators=100, max_depth=3, lr=0.05 | 0.0408 | 0.0396 | 0.0502 | 0.8625 | 2880 | 720 |
| Technical Education | n_estimators=100, max_depth=3, lr=0.05 | 0.0404 | 0.0377 | 0.0478 | 0.8262 | 2880 | 720 |
| Technology | n_estimators=100, max_depth=3, lr=0.05 | 0.0408 | 0.0398 | 0.0498 | 0.7258 | 2880 | 720 |

**Average across all 23 categories:** MAE = 0.0398, RMSE = 0.0497, R² = 0.8182

## Interpretation

Scores are on a 0–1 relevance scale, so an MAE of ~0.03–0.06 means predictions are typically within a few percentage points of the synthetic target score. Because the targets are rule-based/synthetic (see `scripts/generate_synthetic_training_data.py`), these numbers confirm the model successfully learned the encoded domain rules — they do **not** by themselves prove those rules match real LSPU staff training needs. Treat this as validation of the *modeling pipeline*, not of the *domain rules*. Revisit the rules in `generate_synthetic_training_data.py` against real institutional judgment, and retrain once real usage/feedback data accumulates.
