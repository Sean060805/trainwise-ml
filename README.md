# TrainWise ML Recommendation Service

Python microservice adding XGBoost + SBERT-based training recommendations
to the TrainWise PHP app. See `CLAUDE.md` for full project context,
architecture, and build phases — read that first if you're using Claude
Code.

## Setup

1. Create and activate a virtual environment:

   Windows (PowerShell):
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

   macOS/Linux:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in your local DB credentials
   (same database the PHP app uses).

4. Create the training programs catalog table (doesn't exist yet):
   ```
   python scripts/seed_training_programs.py
   ```

5. Run the API:
   ```
   uvicorn app.main:app --reload --port 8000
   ```

6. Check it's alive: open http://localhost:8000/health — should show
   `programs_indexed` > 0 once seeding worked. Interactive API docs at
   http://localhost:8000/docs.

## Project layout

```
app/
  main.py          FastAPI app entrypoint
  config.py        Environment/config loading
  database.py       MySQL connection helpers
  schemas.py        Request/response models
  ml/
    xgboost_model.py    Structured-data model (stub — Phase 2)
    text_similarity.py  SBERT semantic matching (Phase 3)
    recommender.py      Combines both (Phase 4)
  routers/
    recommend.py    POST /recommend endpoint
scripts/            One-off scripts: seeding, data export, training
data/                CSV exports (gitignored, not committed)
models_store/       Saved model files (gitignored, not committed)
tests/
```

## Current status

Scaffold only — see `CLAUDE.md` for the phase-by-phase build order.
Nothing is trained yet; `/recommend` will run but returns text-similarity-
only scores until the XGBoost model exists.

