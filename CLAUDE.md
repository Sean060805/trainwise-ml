# TrainWise ML Recommendation Engine

## What this project is

A Python microservice that adds machine-learning-based training
recommendations to **TrainWise**, an existing PHP/MySQL Employee Training
Needs Assessment system (LSPU capstone project). This service is a
**separate codebase** from the PHP app — it does not modify PHP files
directly. It exposes a small HTTP API that the PHP app calls.

Capstone paper title: "TrainWise: A Web and Mobile-Based Employee Training
Needs Assessment and Recommendation System Using XGBoost and Natural
Language Processing." The proposed engine combines:
- **XGBoost** on structured employee data (department, role, employee type,
  years of service, assessment answers) to predict/rank relevant training
  categories.
- **Sentence-BERT (SBERT)** to compare the free text a user submits
  (`desired_skills`, `comments` in the `assessments` table) against training
  program descriptions, using semantic similarity rather than keyword match.

## Current state — read this before writing code

**Phases 1-6 below are done, not aspirational.** This section used to say
"no Python code exists yet" — that was stale; correcting it here so it
doesn't mislead the next session the way it misled this one.

- The PHP app calls this service end-to-end: `training_recommendations.php`
  and `user_page.php` (in the sibling `trainwise` repo) both call
  `refreshMLRecommendations()` in `ml_recommendations.php`, which POSTs to
  `/recommend` and writes the results into the PHP app's own
  `training_recommendations` table (not a new table — see that repo's
  CLAUDE.md for the FK-type gotcha that cost real debugging time there).
- `training_programs` table was originally seeded with 18 rows across 8
  categories (`scripts/seed_training_programs.py`) and has since grown:
  **as of 2026-09-21 the live DB holds 325 rows across 23 categories**
  (Administration, Agriculture, Assessment, Business, Communication,
  Criminal Justice, Customer Service, Engineering, Fisheries, Food Science
  and Nutrition, Gender & Development, Hospitality and Tourism, Law,
  Leadership, Mathematics, Natural Sciences, Nursing and Health, Pedagogy,
  Physical Education and Sports, Research, Student Affairs, Technical
  Education, Technology). The service indexes 321 of them at startup
  (`/health` reports `programs_indexed`) because it only loads
  `training_type IN ('Workshop','Seminar','Webinar','Conference')` —
  self-paced Online Courses are never recommended, by design.
  The category names are load-bearing: they must match exactly between
  `app/ml/features.py::CATEGORIES` (verified identical to the DB's 23 on
  2026-09-21), the `training_programs.category` column, and
  `scripts/generate_synthetic_training_data.py::BASE_SCORES`. If you
  rename/add one, update all three and retrain (`features.py` documents the
  exact `SELECT DISTINCT category` query to use) or categories silently
  score 0.
- XGBoost is trained: `models_store/xgboost_model.joblib` holds one
  `XGBRegressor` per category, trained on
  `data/processed/synthetic_training_data.csv` (rule-based synthetic
  labels — see that script's docstring for why, and
  `reports/xgboost_evaluation.md` for the evaluation writeup). Real
  assessment data in the live DB is still mostly placeholder text
  (`desired_skills = 'sample'`, `'hi'`), which is exactly why the synthetic
  bootstrap approach exists — there was no real labeled set to train on.
  **This is a cold-start model, not a validated one against real staff
  judgment** — see the report's Interpretation section before claiming
  more than that in the paper.
- SBERT (`multi-qa-MiniLM-L6-cos-v1` — an asymmetric query-vs-passage
  model, well-suited to this task) is loaded and functional, ranking
  programs by cosine similarity against `desired_skills` + `comments` +
  `training_history` + `specialization`. Validated against 18 hand-curated
  (query, expected program) pairs — one per catalog program — in
  `reports/sbert_evaluation.md`: 89% Top-1, 94% Top-3, MRR 0.918 (report
  regenerated 2026-09-14 against the grown 318-program catalog; on the
  original 18-program catalog it was 89% / 100% / 0.944 - the one Top-3
  miss now is a data-protection query where a DPO-compliance program
  outranks the expected security-awareness one). Raw
  similarity scores (~0.5-0.7) sit well below the paper's Table 11 target
  of â‰¥0.75 despite strong ranking quality — that's normal for this kind
  of query-vs-passage cosine similarity, not a sign of a bad model; see
  the report before citing that 0.75 figure as a pass/fail bar.
- **XGBoost 3.x does NOT gracefully handle an unseen categorical value at
  predict time** — contrary to what an earlier version of this file and
  a code comment both claimed. It raises `XGBoostError` and would 500 the
  entire `/recommend` call for that user. Found 2026-08-19 via
  `scripts/benchmark_response_time.py` using a real messy `department`
  value from the live DB; fixed in `app/ml/xgboost_model.py` with a
  try/except that logs and falls back to "no structured signal for this
  category" (text-only score still applies) instead of crashing. Real
  implication: `DEPARTMENT_CODE_MAP` in `app/ml/features.py` only has
  full-name synonyms for some departments (e.g. CCS, CBAA) and not others
  (e.g. CAS has no full-name entry), and live data has outright mangled
  values (`"College of Arts and ScienceCollege of Arts and Sciences"`).
  Any department that doesn't land on an exact map hit effectively gets
  **zero structured signal** post-fix (previously: a crash). Worth a pass
  at expanding `DEPARTMENT_CODE_MAP` against real DB values before
  TAM/ISO testing, so XGBoost actually contributes for most real users
  instead of silently no-op'ing for many of them.
- `/recommend` response time: measured, well within the paper's <5s
  target — sequential mean 0.14s (max 0.27s), 10-concurrent mean 0.92s
  (max 1.23s), both localhost-only. See
  `reports/response_time_benchmark.md`. Re-run
  `scripts/benchmark_response_time.py` (needs the API already running)
  if deploying somewhere other than localhost for actual testing.

## Architecture

```
PHP app (existing)  --HTTP POST-->  FastAPI service (this repo)  -->  MySQL (same DB, read)
training_recommendations.php         POST /recommend                  users, assessments,
                                      returns ranked list               training_programs (new)
```

- FastAPI app lives in `app/`.
- ML logic is isolated in `app/ml/` — `xgboost_model.py` (structured),
  `text_similarity.py` (SBERT), `recommender.py` (combines both into a
  final ranked list).
- DB access goes through `app/database.py`, credentials from `.env`
  (never hardcode credentials, never commit `.env`).
- `scripts/` holds one-off/maintenance scripts (seeding the training
  catalog, exporting data for training, running training jobs) — these
  are not part of the live API.

## Build order (do not skip ahead)

1. **Phase 1 — Data layer.** Done. `training_programs` seeded, 18 rows / 8
   categories.
2. **Phase 2 — Structured model (XGBoost).** Done. Regressor per category
   (continuous 0-1 relevance score, not classification — see the metric-
   choice note in `reports/xgboost_evaluation.md`), trained on synthetic
   bootstrap labels.
3. **Phase 3 — Text similarity (SBERT).** Done, functional, unvalidated
   (see above).
4. **Phase 4 — Combine into `recommender.py`.** Done, exposed via
   `POST /recommend`.
5. **Phase 5 — PHP integration.** Done. Both PHP pages call it via
   `ml_recommendations.php`.
6. **Phase 6 — Evaluate and tune.** Done, as of 2026-08-19:
   - XGBoost: 80/20 split, 3-fold CV grid search over n_estimators/
     max_depth/learning_rate per category, MAE/RMSE/R² on held-out test
     set — `reports/xgboost_evaluation.md`. Re-run `python
     scripts/train_xgboost.py` any time the synthetic data or feature
     engineering changes — it regenerates both the model file and the
     report. **If a uvicorn process is already running, restart it after
     retraining** — it loads the `.joblib` file once at startup and
     `--reload` does not watch non-`.py` files, so it won't pick up a new
     model on its own.
   - SBERT: 18-case hand-curated validation set, Top-1/Top-3/MRR —
     `reports/sbert_evaluation.md`. Re-run `python
     scripts/evaluate_sbert.py` if the catalog or model changes.
   - Response time: benchmarked, passes the <5s target —
     `reports/response_time_benchmark.md`. Re-run `python
     scripts/benchmark_response_time.py` (API must already be running).
   - `specialization` and `training_history` are now accepted by
     `/recommend` (see `app/schemas.py`) and folded into the SBERT query
     text (not XGBoost features — too high-cardinality for clean
     categorical encoding); PHP's `ml_recommendations.php` sends both.
   - Real bug found and fixed during this pass: XGBoost 3.x crashes
     (not degrades) on an unseen categorical value — see the note above.
   - `DEPARTMENT_CODE_MAP` gap closed: audited every distinct
     `department` value actually in the live `users` table
     (`scripts/audit_department_values.py` - re-run this periodically as
     new employees/departments get added) and added the two real gaps
     found: the mangled duplicate-string CAS variant, and `"Main Admin"`
     (3 of 18 live users - not a college, needed its own new canonical
     code, `ADMIN`). Since `ADMIN` is a genuinely new code, also
     regenerated the synthetic dataset and retrained (both scripts pick
     departments up dynamically from `DEPARTMENT_CODE_MAP.values()`, so
     this was just re-running the normal Phase 6 commands, not special
     handling). Verified end-to-end against the live API: both
     previously-crashing real values now return 200 with sensible
     recommendations. `scripts/audit_department_values.py` currently
     reports zero gaps against live data.
   - Student Affairs rule strengthened: it previously never varied with
     any input feature (flat base score + noise), which is why it was
     the one weak category in the first evaluation pass (R² 0.49 - the
     model had nothing to learn beyond the mean). Added two feature-tied
     adjustments in `generate_synthetic_training_data.py::rule_based_scores()`:
     junior teaching staff (+0.20 - most direct day-to-day student
     contact) and leadership roles (+0.15 - typical escalation point for
     student welfare concerns). Retrained: **Student Affairs R² 0.49 ->
     0.86**, average across all 8 categories **0.88 -> 0.92**. Same
     caveat as always applies - this is still a judgment call pending
     real HR/department-head input, documented in
     `reports/xgboost_evaluation.md`.

## Conventions

- Python 3.10+. Virtual environment in `venv/` (gitignored).
- Keep `app/ml/*` framework-agnostic (no FastAPI imports inside ML code) so
  it can be tested and iterated on without spinning up the API.
- All DB credentials and secrets via `.env` (see `.env.example`). Never put
  real credentials in this file, in code, or in commits.
- Run the API locally with: `uvicorn app.main:app --reload --port 8000`
- Run tests with: `pytest`

## Do not do

- Don't modify files inside the PHP project directly from this repo.
- Don't hardcode the 5 sample training titles from the PHP file as if
  they were a real catalog — they're placeholders to replace, not a
  design reference.
- Don't assume the live `assessments` data is representative — most of it
  is placeholder/test data ("sample", "hi", "update").

