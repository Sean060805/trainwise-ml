"""
Checks every distinct `department` value currently in the live `users`
table against DEPARTMENT_CODE_MAP (app/ml/features.py) and reports any
that fall through to the fallback branch in canonical_department() -
i.e. any real department XGBoost will get zero structured signal for,
because it was never one of the canonical codes used to build the
synthetic training set.

Run this periodically (new employees/departments get added over time)
and add any reported gaps to DEPARTMENT_CODE_MAP, then re-run
scripts/generate_synthetic_training_data.py and
scripts/train_xgboost.py if you added a genuinely new canonical code
(not just a new spelling of an existing one).

    python scripts/audit_department_values.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import fetch_all
from app.ml.features import canonical_department, DEPARTMENT_CODE_MAP

KNOWN_CODES = set(DEPARTMENT_CODE_MAP.values())


def main():
    rows = fetch_all("SELECT department, COUNT(*) as cnt FROM users GROUP BY department ORDER BY cnt DESC")

    print(f"{'Raw value':<65} {'Count':<7} {'Maps to':<10} {'Status'}")
    print("-" * 100)

    gaps = []
    for row in rows:
        raw = row["department"]
        count = row["cnt"]
        canonical = canonical_department(raw)
        is_gap = canonical not in KNOWN_CODES and canonical != "UNKNOWN"
        status = "GAP - falls through to unmapped fallback" if is_gap else "ok"
        print(f"{str(raw):<65} {count:<7} {canonical:<10} {status}")
        if is_gap:
            gaps.append((raw, count, canonical))

    print()
    if gaps:
        total_affected = sum(c for _, c, _ in gaps)
        print(f"{len(gaps)} unmapped department value(s), affecting {total_affected} user(s):")
        for raw, count, canonical in gaps:
            print(f"  - {raw!r} ({count} user(s)) -> currently canonicalizes to {canonical!r}, "
                  f"which XGBoost never saw in training and will silently skip.")
        print(
            "\nAdd these to DEPARTMENT_CODE_MAP in app/ml/features.py. If any map to a "
            "genuinely NEW canonical code (not an existing one like CCS/CAS/etc.), also "
            "re-run generate_synthetic_training_data.py and train_xgboost.py so that "
            "code has training coverage."
        )
    else:
        print("No gaps - every current department value maps to a known canonical code.")


if __name__ == "__main__":
    main()
