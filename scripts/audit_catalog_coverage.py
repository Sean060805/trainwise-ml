"""
Proactive catalog-coverage audit — the preventive counterpart to how the
Dexter/COF gap was found (reactively, after a live respondent hit it).

For every college, checks the catalog against REAL evidence of demand:
  (a) every real assessments.desired_skills text already on file for that
      college (self-reported, evidence a real person actually asked)
  (b) every official 2025 TNA title for that college, where one exists

... and flags anything whose best catalog match is at or below the noise
floor observed this session (0.10-0.25 for genuinely unrelated pairs,
0.30+ for a real match - see recommender.py's TOP_TEXT_CONFIDENT_THRESHOLD
comment) as a still-open content gap.

A college with neither data source has nothing to check - flagged
separately as "no data yet," not as "covered," since absence of evidence
isn't evidence of coverage.

Throwaway diagnostic, not part of the app.
Run: venv\\Scripts\\python.exe scripts\\audit_catalog_coverage.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import fetch_all
from app.ml.text_similarity import TextSimilarityMatcher
from app.ml.features import canonical_department, DEPARTMENT_CODE_MAP

GAP_THRESHOLD = 0.25  # at/below this, treat as "no genuine match" (noise-floor territory)

matcher = TextSimilarityMatcher()
programs = fetch_all("""
    SELECT id, title, description FROM training_programs
    WHERE training_type IN ('Workshop', 'Seminar', 'Webinar', 'Conference')
""")
matcher.index_programs([{"id": p["id"], "description": p["description"]} for p in programs])
titles_by_id = {p["id"]: p["title"] for p in programs}

all_colleges = sorted(set(DEPARTMENT_CODE_MAP.values()))

tna_rows = fetch_all("SELECT college_code, title FROM tna_2025_demand")
tna_by_college = {}
for row in tna_rows:
    tna_by_college.setdefault(row["college_code"], []).append(row["title"])

assessment_rows = fetch_all("""
    SELECT u.department, a.desired_skills
    FROM assessments a JOIN users u ON u.id = a.user_id
    WHERE a.desired_skills IS NOT NULL AND a.desired_skills != ''
""")
self_reported_by_college = {}
for row in assessment_rows:
    code = canonical_department(row["department"])
    self_reported_by_college.setdefault(code, []).append(row["desired_skills"])

print(f"Catalog: {len(programs)} programs indexed. Gap threshold: {GAP_THRESHOLD}\n")

any_gap_found = False
for college in all_colleges:
    official = tna_by_college.get(college, [])
    self_reported = self_reported_by_college.get(college, [])
    if not official and not self_reported:
        print(f"=== {college}: NO DATA YET (0 official TNA rows, 0 real respondents) - unknown, not verified ===\n")
        continue

    print(f"=== {college} ({len(official)} official TNA titles, {len(self_reported)} real respondent(s)) ===")
    gaps_this_college = []
    for source_label, queries in [("official TNA", official), ("self-reported", self_reported)]:
        for q in queries:
            ranked = matcher.rank_programs(q, top_k=1)
            if not ranked:
                continue
            best_id, best_score = ranked[0]
            flag = "GAP" if best_score <= GAP_THRESHOLD else "ok"
            if flag == "GAP":
                gaps_this_college.append((source_label, q, best_score, titles_by_id[best_id]))
    if gaps_this_college:
        any_gap_found = True
        for source_label, q, score, best_title in gaps_this_college:
            q_short = (q[:70] + "...") if len(q) > 70 else q
            print(f"  GAP  [{source_label}] {score:.4f}  {q_short!r}  (closest: {best_title!r})")
    else:
        print(f"  no gaps found against {len(official) + len(self_reported)} real query text(s)")
    print()

if not any_gap_found:
    print("No content gaps found against any real evidence on file right now.")
