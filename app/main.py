from fastapi import FastAPI

from app.routers import recommend, similarity

app = FastAPI(
    title="TrainWise ML Recommendation Service",
    description="XGBoost + SBERT training recommendation engine for TrainWise.",
    version="0.1.0",
)

app.include_router(recommend.router)
app.include_router(similarity.router)

# Populated at startup by recommend.load_programs_and_index() — a plain
# module-level dict keeps this simple; swap for proper dependency
# injection later if the app grows.
PROGRAMS_BY_ID: dict[int, dict] = {}


@app.on_event("startup")
def on_startup():
    global PROGRAMS_BY_ID
    PROGRAMS_BY_ID = recommend.load_programs_and_index()


@app.get("/health")
def health():
    return {"status": "ok", "programs_indexed": len(PROGRAMS_BY_ID)}

