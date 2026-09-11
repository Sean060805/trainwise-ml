"""
Generates a synthetic, rule-labeled training set for the XGBoost model.

WHY THIS EXISTS (read CLAUDE.md Phase 2 first): the live `assessments`
table doesn't have enough real, non-placeholder examples to learn a
category-relevance model from directly. Rather than blocking on data
that doesn't exist yet, this script encodes a hand-authored set of
domain rules (department/role/seniority -> which training categories
matter) as explicit, readable Python below, then uses those rules to
generate many labeled (features -> category scores) examples with
random noise added, so XGBoost learns a *smoothed, generalized* version
of the rules rather than memorizing a lookup table.

This is a legitimate, commonly used bootstrap strategy for cold-start
recommender systems — document it as such in your paper. It is NOT
meant to be the permanent label source: once real usage/feedback data
accumulates (e.g. which recommended trainings users actually complete
or rate highly), replace or blend this with a model trained on that
real signal instead. Search "cold start recommender system" /
"synthetic label bootstrapping" if you want citations for the paper.

Edit RULES below to match your own institutional judgment before your
final defense — the numbers here are a reasonable starting point, not
gospel. Then regenerate and retrain:

    python scripts/generate_synthetic_training_data.py
    python scripts/train_xgboost.py
"""
import sys
import os
import itertools
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd

from app.ml.features import (
    CATEGORIES,
    FEATURE_COLUMNS,
    DEPARTMENT_CODE_MAP,
    TECH_ADJACENT_DEPARTMENTS,
    NUTRITION_ADJACENT_DEPARTMENTS,
    CRIMINAL_JUSTICE_ADJACENT_DEPARTMENTS,
    CENTRAL_ADMIN_DEPARTMENTS,
)

OUTPUT_PATH = "data/processed/synthetic_training_data.csv"
SAMPLES_PER_COMBINATION = 5
NOISE_STD = 0.05
RANDOM_SEED = 42

# Base relevance score (0-1) per category, before any adjustments. A
# category not listed here defaults to 0.1 (see rule_based_scores below) -
# only categories that should differ from that generic low default need an
# entry.
#
# 2026-09-09 - rebuilt alongside CATEGORIES' own rewrite (see features.py's
# comment) to cover all 23 real catalog categories instead of 14, 4 of
# which didn't match anything real. Gender & Development keeps a real,
# non-trivial base for everyone (CSC GAD mandate applies regardless of
# role) - Public Service is dropped entirely since no catalog category
# maps to it. Every new subject-specific category (Agriculture, Business,
# Engineering, Fisheries, Food Science and Nutrition, Hospitality and
# Tourism, Law, Mathematics, Natural Sciences, Nursing and Health,
# Physical Education and Sports, Technical Education) is deliberately left
# out of BASE_SCORES and instead driven entirely by DEPARTMENT_CATEGORY_
# BOOST below, the same shape as Technology/is_tech_department already
# used - a Fisheries training isn't broadly relevant outside COF the way
# Pedagogy is broadly relevant to every teacher.
BASE_SCORES = {
    "Teaching": {
        "Pedagogy": 0.75, "Assessment": 0.65, "Research": 0.40,
        "Technology": 0.40, "Student Affairs": 0.35, "Communication": 0.25,
        "Leadership": 0.15, "Administration": 0.15,
        "Gender & Development": 0.30,
    },
    "Non-teaching": {
        "Administration": 0.75, "Communication": 0.55, "Technology": 0.45,
        "Student Affairs": 0.25, "Leadership": 0.15, "Pedagogy": 0.10,
        "Research": 0.10, "Assessment": 0.15,
        "Gender & Development": 0.30,
    },
}

# 2026-09-09 - replaces the old one-off is_tech_department / is_nutrition_
# department / is_criminal_justice_department / is_central_admin_department
# boolean feature columns. Checked directly against this session's real
# 14-category retrain output before making this change, not guessed: all
# four of those boolean flags scored EXACTLY 0.0 feature importance,
# meaning XGBoost's native categorical split on the raw `department`
# column already captured everything they were meant to add. Adding nine
# MORE one-off boolean columns for the new subject-specific colleges would
# almost certainly repeat that same zero-importance finding at a larger
# scale, so this keys the boost directly off `department` in the rule
# logic below instead of manufacturing more redundant feature columns.
# Departments not listed here simply get no category-specific boost -
# CTE and CAS deliberately spread modest boosts across several plausible
# sub-disciplines rather than one dominant category, since both colleges
# cover genuinely heterogeneous specializations (CTE: general/technical/PE
# education tracks; CAS: sciences, math, humanities, social sciences).
DEPARTMENT_CATEGORY_BOOST = {
    "CCS": {"Technology": 0.25},
    "CIT": {"Technology": 0.20, "Technical Education": 0.45},
    "COE": {"Technology": 0.10, "Engineering": 0.55},
    "CFND": {"Food Science and Nutrition": 0.55},
    "CCJE": {"Criminal Justice": 0.55},
    "COF": {"Fisheries": 0.55},
    "CBAA": {"Business": 0.55},
    "CHMT": {"Hospitality and Tourism": 0.55},
    "COL": {"Law": 0.55},
    "CA": {"Agriculture": 0.55},
    "CONAH": {"Nursing and Health": 0.55},
    "CAS": {"Natural Sciences": 0.35, "Mathematics": 0.25, "Communication": 0.15},
    "CTE": {"Physical Education and Sports": 0.15, "Mathematics": 0.10},
    "ADMIN": {"Administration": 0.30, "Customer Service": 0.20},
}


def rule_based_scores(features: dict, rng: random.Random) -> dict:
    """The actual domain rules. Edit these to match real institutional judgment."""
    scores = dict(BASE_SCORES[features["teaching_status"]])

    for category, boost in DEPARTMENT_CATEGORY_BOOST.get(features["department"], {}).items():
        scores[category] = scores.get(category, 0.1) + boost

    if features["is_leadership"]:
        scores["Leadership"] += 0.45
        scores["Administration"] += 0.20
        # Chairs/coordinators are typically the escalation point when a
        # faculty member under them raises a student welfare concern.
        scores["Student Affairs"] += 0.15
        scores["Gender & Development"] += 0.10

    if features["years_bucket"] == "senior":
        scores["Research"] += 0.20
        scores["Leadership"] += 0.10
    elif features["years_bucket"] == "junior" and features["teaching_status"] == "Teaching":
        scores["Pedagogy"] += 0.15
        scores["Assessment"] += 0.10
        # Junior faculty are still building classroom experience and have
        # the most direct, unmediated day-to-day contact with students -
        # most likely to be the first to notice a student in distress and
        # need guidance on how to respond/refer.
        scores["Student Affairs"] += 0.20

    if features["attainment_bucket"] == "doctorate":
        scores["Research"] += 0.30
    elif features["attainment_bucket"] == "masters":
        scores["Research"] += 0.15

    # Add noise, clip to [0, 1]
    for cat in CATEGORIES:
        base = scores.get(cat, 0.1)
        noisy = base + rng.gauss(0, NOISE_STD)
        scores[cat] = max(0.0, min(1.0, noisy))

    return scores


def main():
    rng = random.Random(RANDOM_SEED)

    departments = sorted(set(DEPARTMENT_CODE_MAP.values())) + ["UNKNOWN"]
    teaching_statuses = ["Teaching", "Non-teaching"]
    years_buckets = ["junior", "mid", "senior"]
    attainment_buckets = ["bachelors", "masters", "doctorate", "unknown"]
    leadership_flags = [True, False]

    rows = []
    combinations = itertools.product(
        departments, teaching_statuses, years_buckets, attainment_buckets, leadership_flags
    )
    for dept, teaching_status, years_b, attain_b, is_lead in combinations:
        # The four is_*_department flags are still computed here, even
        # though rule_based_scores() no longer reads them (see
        # DEPARTMENT_CATEGORY_BOOST's comment above) - they're still real
        # columns in FEATURE_COLUMNS (features.py's bucket_features() computes
        # them for every live scoring request too), so this CSV's schema has
        # to keep matching that or training breaks. Confirmed zero-importance
        # dead weight, not worth the bigger, riskier change of removing them
        # from the schema entirely tonight.
        features = {
            "department": dept,
            "is_tech_department": dept in TECH_ADJACENT_DEPARTMENTS,
            "is_nutrition_department": dept in NUTRITION_ADJACENT_DEPARTMENTS,
            "is_criminal_justice_department": dept in CRIMINAL_JUSTICE_ADJACENT_DEPARTMENTS,
            "is_central_admin_department": dept in CENTRAL_ADMIN_DEPARTMENTS,
            "teaching_status": teaching_status,
            "years_bucket": years_b,
            "attainment_bucket": attain_b,
            "is_leadership": is_lead,
        }
        for _ in range(SAMPLES_PER_COMBINATION):
            scores = rule_based_scores(features, rng)
            row = dict(features)
            row.update(scores)
            rows.append(row)

    df = pd.DataFrame(rows)
    # Column order: features first, then one column per category
    df = df[FEATURE_COLUMNS + CATEGORIES]

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Generated {len(df)} synthetic rows -> {OUTPUT_PATH}")
    print(f"Feature combinations: {len(departments)} depts x {len(teaching_statuses)} teaching "
          f"x {len(years_buckets)} years x {len(attainment_buckets)} attainment x "
          f"{len(leadership_flags)} leadership = "
          f"{len(departments)*len(teaching_statuses)*len(years_buckets)*len(attainment_buckets)*len(leadership_flags)} "
          f"combos x {SAMPLES_PER_COMBINATION} samples each")
    print("\nSample rows:")
    print(df.head(3).to_string())


if __name__ == "__main__":
    main()

