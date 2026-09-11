"""
Pulls users + assessments (joined) into a CSV under data/raw/ for
offline exploration in a notebook, before committing to a feature
pipeline in app/ml/xgboost_model.py.

    python scripts/export_assessments.py
"""
import sys
import os
import csv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import fetch_all

QUERY = """
SELECT
    u.id AS user_id,
    u.department,
    u.designation,
    u.teaching_status,
    u.yearsInLSPU,
    a.id AS assessment_id,
    a.desired_skills,
    a.comments,
    a.status,
    a.submission_date
FROM users u
JOIN assessments a ON a.user_id = u.id
"""


def main():
    rows = fetch_all(QUERY)
    os.makedirs("data/raw", exist_ok=True)
    out_path = "data/raw/assessments_export.csv"

    if not rows:
        print("No rows found — is the DB running and seeded?")
        return

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()

