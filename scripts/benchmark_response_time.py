"""
Measures /recommend response time against a running instance of this
service, under both normal (sequential) and light concurrent load, and
compares against the capstone paper's Table 11 target (<5 seconds per
request).

Requires the API to already be running:
    uvicorn app.main:app --reload --port 8000

Then, in another terminal:
    python scripts/benchmark_response_time.py
"""
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import httpx

BASE_URL = os.getenv("BENCHMARK_BASE_URL", "http://127.0.0.1:8000")
REPORT_PATH = os.path.join("reports", "response_time_benchmark.md")
TARGET_SECONDS = 5.0

SEQUENTIAL_REQUESTS = 20
CONCURRENT_REQUESTS = 10

# Varied, realistic payloads - not all identical, so this isn't just
# measuring one cached/degenerate case.
PAYLOADS = [
    {
        "user_id": 1, "department": "CCS", "designation": "Software Engineer",
        "position": None, "teaching_status": "Teaching", "years_in_lspu": "13",
        "educational_attainment": "Doctorate Degree (Completed)",
        "specialization": "Software Engineering",
        "desired_skills": "I want to improve my skills in data protection and online security",
        "comments": "", "training_history": "",
    },
    {
        "user_id": 2, "department": "College of Arts and Sciences", "designation": "Dean",
        "position": "Dean", "teaching_status": "Non-teaching", "years_in_lspu": "15",
        "educational_attainment": "Master's Degree", "specialization": "Public Administration",
        "desired_skills": "Help me turn our college's long-term vision into a yearly action plan",
        "comments": "Also interested in budget preparation", "training_history": "",
    },
    {
        "user_id": 3, "department": "CIT", "designation": "Instructor",
        "position": None, "teaching_status": "Teaching", "years_in_lspu": "2",
        "educational_attainment": "Bachelor's Degree", "specialization": "Information Technology",
        "desired_skills": "I want to try flipped classroom and active learning techniques",
        "comments": "", "training_history": "Attended a basic Excel workshop last year",
    },
    {
        "user_id": 4, "department": "Unknown Department", "designation": None,
        "position": None, "teaching_status": None, "years_in_lspu": None,
        "educational_attainment": None, "specialization": None,
        "desired_skills": None, "comments": None, "training_history": None,
    },
]


def send_one(client: httpx.Client, payload: dict) -> float:
    start = time.perf_counter()
    resp = client.post(f"{BASE_URL}/recommend", json=payload, timeout=30.0)
    elapsed = time.perf_counter() - start
    resp.raise_for_status()
    return elapsed


def run_sequential(client: httpx.Client) -> list[float]:
    print(f"Running {SEQUENTIAL_REQUESTS} sequential requests...")
    times = []
    for i in range(SEQUENTIAL_REQUESTS):
        payload = PAYLOADS[i % len(PAYLOADS)]
        elapsed = send_one(client, payload)
        times.append(elapsed)
        print(f"  [{i+1}/{SEQUENTIAL_REQUESTS}] {elapsed:.3f}s")
    return times


def run_concurrent() -> list[float]:
    print(f"\nRunning {CONCURRENT_REQUESTS} concurrent requests...")
    times = []
    with httpx.Client() as client:
        with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as pool:
            futures = [
                pool.submit(send_one, client, PAYLOADS[i % len(PAYLOADS)])
                for i in range(CONCURRENT_REQUESTS)
            ]
            for i, fut in enumerate(futures):
                elapsed = fut.result()
                times.append(elapsed)
                print(f"  [{i+1}/{CONCURRENT_REQUESTS}] {elapsed:.3f}s")
    return times


def summarize(times: list[float]) -> dict:
    sorted_times = sorted(times)
    p95_idx = min(len(sorted_times) - 1, int(round(0.95 * (len(sorted_times) - 1))))
    return {
        "n": len(times),
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "min": min(times),
        "max": max(times),
        "p95": sorted_times[p95_idx],
        "under_target": sum(1 for t in times if t < TARGET_SECONDS),
    }


def write_report(seq_times, seq_stats, conc_times, conc_stats):
    os.makedirs("reports", exist_ok=True)
    lines = []
    lines.append("# /recommend Response Time Benchmark\n\n")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n")
    lines.append(f"Target (paper Table 11): **< {TARGET_SECONDS:.0f} seconds per request**\n\n")

    lines.append("## Sequential requests (normal load, one at a time)\n\n")
    lines.append(
        f"- Requests: {seq_stats['n']}\n"
        f"- Mean: {seq_stats['mean']:.3f}s | Median: {seq_stats['median']:.3f}s | "
        f"Min: {seq_stats['min']:.3f}s | Max: {seq_stats['max']:.3f}s | P95: {seq_stats['p95']:.3f}s\n"
        f"- Under target: {seq_stats['under_target']}/{seq_stats['n']}\n\n"
    )

    lines.append("## Concurrent requests (light concurrent load)\n\n")
    lines.append(
        f"- Requests: {conc_stats['n']} fired simultaneously ({CONCURRENT_REQUESTS} worker threads)\n"
        f"- Mean: {conc_stats['mean']:.3f}s | Median: {conc_stats['median']:.3f}s | "
        f"Min: {conc_stats['min']:.3f}s | Max: {conc_stats['max']:.3f}s | P95: {conc_stats['p95']:.3f}s\n"
        f"- Under target: {conc_stats['under_target']}/{conc_stats['n']}\n\n"
    )

    verdict = (
        "PASS" if seq_stats["under_target"] == seq_stats["n"] and conc_stats["under_target"] == conc_stats["n"]
        else "FAIL"
    )
    lines.append(f"## Verdict: {verdict}\n\n")
    lines.append(
        "Note: this measures the FastAPI service directly on localhost, not through "
        "the PHP app's curl call or over a network — real end-user latency (PHP -> "
        "curl -> this API -> back to PHP -> page render) will be somewhat higher. "
        "Re-run this after deploying to whatever environment will actually be used "
        "for TAM/ISO testing if that differs from localhost.\n\n"
    )

    lines.append("## Raw sequential timings (seconds)\n\n")
    lines.append(", ".join(f"{t:.3f}" for t in seq_times) + "\n\n")
    lines.append("## Raw concurrent timings (seconds)\n\n")
    lines.append(", ".join(f"{t:.3f}" for t in conc_times) + "\n")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)


def main():
    print(f"Checking {BASE_URL}/health ...")
    with httpx.Client() as client:
        health = client.get(f"{BASE_URL}/health", timeout=10.0)
        health.raise_for_status()
        print(f"  {health.json()}")

        seq_times = run_sequential(client)

    conc_times = run_concurrent()

    seq_stats = summarize(seq_times)
    conc_stats = summarize(conc_times)

    write_report(seq_times, seq_stats, conc_times, conc_stats)

    print(f"\nSequential: mean={seq_stats['mean']:.3f}s p95={seq_stats['p95']:.3f}s max={seq_stats['max']:.3f}s")
    print(f"Concurrent: mean={conc_stats['mean']:.3f}s p95={conc_stats['p95']:.3f}s max={conc_stats['max']:.3f}s")
    print(f"Saved report -> {REPORT_PATH}")


if __name__ == "__main__":
    main()
