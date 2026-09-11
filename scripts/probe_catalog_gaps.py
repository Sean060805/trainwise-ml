"""
2026-09-10 - proactive catalog-gap probe, built the night before real
pilot testing after a real respondent (Wilson, CCS) typed "machine
learning and AI Automation" and got zero genuinely relevant
recommendations - not because the ML was broken, but because no
Workshop/Seminar-type catalog entry existed for that topic at all (see
CLAUDE.md). Rather than wait for the next real tester to stumble onto
the next gap, this checks a broad, realistic spread of common
professional-development requests - one per real college/office,
plus generic cross-cutting ones - directly against the CURRENT live
catalog's SBERT embeddings, and flags any phrase whose best match
doesn't clear the same "genuine match" bar the live system itself uses
(TOP_TEXT_CONFIDENT_THRESHOLD = 0.28, see recommender.py) so a real gap
is caught and fixed tonight instead of during tomorrow's pilot.

    python scripts/probe_catalog_gaps.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import fetch_all
from app.ml.text_similarity import TextSimilarityMatcher

GENUINE_MATCH_THRESHOLD = 0.28

# One realistic phrase per real college/office (matching this project's
# actual headcount-weighted colleges), plus several generic cross-
# cutting requests any employee might type regardless of department.
PROBE_PHRASES = {
    "CAS (generic sciences)": "I want to improve my chemistry laboratory safety and analytical skills",
    "CAS (math)": "I want training in college-level mathematics teaching strategies",
    "CTE": "I want to learn about classroom management and curriculum development",
    "CCS (AI/ML - already fixed)": "I want to improve my skills in machine learning and AI Automation",
    "CCS (web dev)": "I want to learn full-stack web development and modern frameworks",
    "CCS (cloud)": "I want to learn cloud computing and infrastructure management",
    "COF": "I want training in aquaculture and fish disease management",
    "CCJE": "I want to learn criminal investigation and forensic science techniques",
    "CBAA (accounting)": "I want to improve my financial accounting and taxation skills",
    "CBAA (marketing)": "I want training in digital marketing and brand strategy",
    "CHMT": "I want to learn hotel and restaurant management best practices",
    "CFND": "I want training in clinical nutrition and dietetics counseling",
    "CA": "I want to learn sustainable crop production and agribusiness management",
    "COE": "I want training in renewable energy systems and structural engineering",
    "CIT": "I want to learn industrial automation and electronics troubleshooting",
    "CONAH": "I want to improve my nursing skills and patient care practices",
    "COL": "I want training in legal research and case analysis",
    "ADMIN (records)": "I want to learn records management and document digitization",
    "ADMIN (procurement)": "I want training in government procurement and budget preparation",
    "Generic - leadership": "I want to develop my leadership and team management skills",
    "Generic - public speaking": "I want to improve my public speaking and presentation skills",
    "Generic - customer service": "I want to improve how I handle difficult customers and complaints",
    "Generic - time management": "I want to learn better time management and productivity techniques",
    "Generic - conflict resolution": "I want to learn conflict resolution and mediation skills",
    "Generic - data analysis": "I want to learn how to analyze data and build reports in Excel",
    "Generic - project management": "I want to learn project management and PMP-style methodologies",
    "Generic - grant writing": "I want to learn how to write competitive research grant proposals",
    "Generic - mental health": "I want training in mental health first aid for supporting students",
    "Generic - research methods": "I want to improve my research methodology and statistical analysis skills",
}


def main():
    rows = fetch_all(
        "SELECT id, title, description, category FROM training_programs "
        "WHERE training_type IN ('Workshop', 'Seminar')"
    )
    print(f"Indexing {len(rows)} live Workshop/Seminar programs...")
    matcher = TextSimilarityMatcher()
    matcher.index_programs([{"id": r["id"], "description": r["description"]} for r in rows])
    by_id = {r["id"]: r for r in rows}

    gaps = []
    print(f"\n{'Phrase':<32} {'Top score':<10} {'Best match'}")
    print("-" * 100)
    for label, phrase in PROBE_PHRASES.items():
        ranked = matcher.rank_programs(phrase, top_k=1)
        if not ranked:
            continue
        program_id, score = ranked[0]
        title = by_id[program_id]["title"]
        flag = "  <-- GAP" if score < GENUINE_MATCH_THRESHOLD else ""
        print(f"{label:<32} {score:.4f}     {title}{flag}")
        if score < GENUINE_MATCH_THRESHOLD:
            gaps.append((label, phrase, score, title))

    print("\n" + "=" * 100)
    if gaps:
        print(f"{len(gaps)} REAL GAP(S) FOUND - no genuine catalog match (score < {GENUINE_MATCH_THRESHOLD}):")
        for label, phrase, score, title in gaps:
            print(f"  - {label}: \"{phrase}\" -> best is only \"{title}\" ({score:.4f})")
    else:
        print(f"No gaps found - every probed phrase clears the {GENUINE_MATCH_THRESHOLD} genuine-match threshold.")


if __name__ == "__main__":
    main()
