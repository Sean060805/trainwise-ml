"""
One-time seed for tna_2025_demand - the official LSPU "Summary of Training
Needs Assessment (TNA) 2025" document (docs/Summary of TNA 2025.pdf in the
trainwise repo), transcribed verbatim as (college_code, title) pairs.

Unlike seed_training_programs.py, this is NOT re-generated/re-truncated on
every run - it's a fixed historical record, not a synthetic catalog. Safe
to re-run: INSERT IGNORE relies on the UNIQUE(college_code, title)
constraint, so re-running only fills gaps, never duplicates or wipes.

Per the subject specialist's explicit guidance (2026-08-26): this data is
too small/curated to train a model on. It's used instead as a second,
higher-trust reference catalog - trainwise-ml's recommender boosts
programs that are topically similar to something a college officially
requested here (see app/ml/tna_matcher.py), grounding the cold-start
recommendation in real institutional demand instead of only synthetic
labels.

CHMT, CCS, and COF (College of Fisheries) submitted nothing for TNA 2025 -
intentionally not seeded. Every downstream lookup must treat "no rows for
this college" as "no boost," never an error or a penalty.

Everything under the PDF's blended "ADMIN" section (library, budgeting,
HRM/PRIME, records, registrar, supply, etc.) is bucketed under one generic
"ADMIN" college_code rather than guessing which specific office each line
belongs to - an explicit scoping decision, not an oversight.

Run:
    python scripts/seed_tna_2025.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import execute, fetch_all

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tna_2025_demand (
    id INT AUTO_INCREMENT PRIMARY KEY,
    college_code VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    source_year INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_college_title (college_code, title)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# 2026-09-07 - despite the table/file name, this now holds official TNA
# demand across multiple years (2024, 2025, 2027 - 2023 and earlier are
# unobtainable; the HR preparer, Dr. Imee P. Sanchez, only started at LSPU
# in Dec 2023 and declined to source records she didn't personally create).
# Table/file name kept as-is rather than renamed - this file remains the
# 2025-specific seed; see seed_tna_2024.py and seed_tna_2027.py for the
# other two years, all writing into this same shared table. The UNIQUE
# constraint stays (college_code, title) WITHOUT year - if the exact same
# title happens to repeat in a later year for the same college, that's
# still one real signal (the college wants it), not two; the college
# still gets the boost either way, and getTna2025Boosts() doesn't
# distinguish years, it just pools every row per college code.

# (college_code, title) - transcribed from docs/Summary of TNA 2025.pdf.
# Near-duplicate/exact-duplicate lines in the source (e.g. CCJE's two
# "Advanced digital evidence processing" variants, CTE's two literal
# repeats, ADMIN's two "budgeting" repeats) are merged case-insensitively
# to one row each - the DB's UNIQUE constraint would reject the plain
# duplicates anyway, but de-duping here keeps the source list itself
# honest about what was actually requested.
TNA_ITEMS = [
    # ---- CCJE (24 unique titles) ----
    ("CCJE", "Criminalistics/forensic science training"),
    ("CCJE", "Advance security management training"),
    ("CCJE", "Security services NCII"),
    ("CCJE", "Quality assurance/accrediting agency training"),
    ("CCJE", "Gender and development training"),
    ("CCJE", "Human rights education"),
    ("CCJE", "Instructional materials development training"),
    ("CCJE", "Curriculum development"),
    ("CCJE", "Research and statistics"),
    ("CCJE", "Dispute resolution"),
    ("CCJE", "Crime prevention and analysis"),
    ("CCJE", "Questioned document examination"),
    ("CCJE", "Leadership formation"),
    ("CCJE", "Gender awareness"),
    ("CCJE", "Specialization training in questioned document examination/polygraphy"),
    ("CCJE", "Training in security course program"),
    ("CCJE", "Law related trainings"),
    ("CCJE", "Training specialization in Lie detection techniques"),
    ("CCJE", "Advanced Digital Evidence Processing"),
    ("CCJE", "Digital Forensics"),
    ("CCJE", "Criminal investigation and detection course by NFSTI or PNP"),
    ("CCJE", "Criminal intelligence course by PNP/AFP"),
    ("CCJE", "Certified fingerprint examiner"),
    ("CCJE", "Syllabus enhancement training"),

    # ---- CFND (20 unique titles) ----
    ("CFND", "Intellectual Property Rights Training"),
    ("CFND", "Technology and Commercialization Training"),
    ("CFND", "Research and Extension Related Trainings"),
    ("CFND", "Clinical Nutrition Short Course"),
    ("CFND", "Teaching Effectiveness"),
    ("CFND", "Quality Assurance"),
    ("CFND", "Public Health Nutrition"),
    ("CFND", "Nutritional Epidemiology"),
    ("CFND", "Food Safety and Quality Control"),
    ("CFND", "Nutrigenomics and Nutritional Biochemistry"),
    ("CFND", "Clinical Nutrition"),
    ("CFND", "Food Processing and Preservation Techniques"),
    ("CFND", "Behavior Change and Nutrition Counselling"),
    ("CFND", "Global Food Security and Policy"),
    ("CFND", "Statistics and Data Analysis in Nutrition"),
    ("CFND", "Environmental Nutrition and Sustainability"),
    ("CFND", "Project Management for Nutrition Programs"),
    ("CFND", "41st Diabetes Philippines Annual Convention"),
    ("CFND", "Nutritionist-Dietitian Association of the Philippines (NDAP) Conventions"),
    ("CFND", "Philippine Society of Nutritionists-Dietitian (PSND) Conventions"),

    # ---- CTE (16 unique titles) ----
    ("CTE", "Seminar/training related to statistical research"),
    ("CTE", "The annual convention of the Mathematical Society of the Philippines (MSP)"),
    ("CTE", "Research conferences/convention (national level)"),
    ("CTE", "Integration of AI in teaching and learning"),
    ("CTE", "Educational management in HEIs"),
    ("CTE", "Trends in educational technology"),
    ("CTE", "Enhancing CTE students' writing skills"),
    ("CTE", "Seminar workshop in public speaking"),
    ("CTE", "Research writing-workshop"),
    ("CTE", "Workshop/training about Philippine Folk Dance"),
    ("CTE", "2nd Graduate School Research Forum at BATSU"),
    ("CTE", "2024 MSP Calabarzon"),
    ("CTE", "Parasitology Training"),
    ("CTE", "Pollution Control Training"),
    ("CTE", "AI Training in Education"),
    ("CTE", "Leadership Training"),

    # ---- ADMIN (blended non-teaching offices: library, budgeting/COA,
    # HRM/PRIME, records, registrar, supply, etc. - bucketed together
    # per the scoping decision above) ----
    ("ADMIN", "Unlocking the power of AI and data management for libraries"),
    ("ADMIN", "Assessing and citing open access resources"),
    ("ADMIN", "Book digitization, online access and lending"),
    ("ADMIN", "Trainings related to Government Budgeting"),
    ("ADMIN", "Philippine Budgeting System"),
    ("ADMIN", "Laws and rules on government expenditures"),
    ("ADMIN", "Best practices and remedies to avoid COA Disallowances"),
    ("ADMIN", "1st PAGBA Quarterly seminar and meeting"),
    ("ADMIN", "Guiding principles on the management of government funds and properties"),
    ("ADMIN", "Policies and procedures on leave administration"),
    ("ADMIN", "Archiving and importance of records protection"),
    ("ADMIN", "Records management workshop and seminar"),
    ("ADMIN", "PRIME - HRM Performance Management for Government Employees and Learning and Development"),
    ("ADMIN", "Updates on Benefits (GSIS & Pag-ibig) for government employees"),
    ("ADMIN", "Leadership/Strategic planning seminar"),
    ("ADMIN", "Records Management Training"),
    ("ADMIN", "Digitization"),
    ("ADMIN", "Medical Training Assistance"),
    ("ADMIN", "Training Water Recycle"),
    ("ADMIN", "Commission on Audit - annual seminar"),
    ("ADMIN", "COA and BIR - related seminars"),
    ("ADMIN", "COA rules and regulations"),
    ("ADMIN", "Updates on tax guidelines"),
    ("ADMIN", "More COA Trainings, bookkeeping, disbursement etc."),
    ("ADMIN", "BIR trainings and seminars (taxes)"),
    ("ADMIN", "National Training - Records Management and archives"),
    ("ADMIN", "Seminar on Electronic Records Management"),
    ("ADMIN", "Document Control and Records Management Training"),
    ("ADMIN", "Basic Customer Service Skill"),
    ("ADMIN", "Basic records management"),
    ("ADMIN", "Public service ethics and accountability"),
    ("ADMIN", "Computer literacy"),
    ("ADMIN", "Training programs related to payroll/compensation and benefits management (DBM-related)"),
    ("ADMIN", "Training and development"),
    ("ADMIN", "Basic customer service skills training"),
    ("ADMIN", "Public service values program"),
    ("ADMIN", "Supply chain management"),
    ("ADMIN", "Inventory management/inventory control"),
    ("ADMIN", "Supply operations management"),
    ("ADMIN", "Inventory control"),
    ("ADMIN", "Financial literacy"),
    ("ADMIN", "University, College and School Registrar Association, Inc. (UCSRA) convention/training/workshop"),
    ("ADMIN", "National Association of Registrars of State Universities and Colleges (NARSUC) convention/training"),
    ("ADMIN", "Civil Service Commission training and workshop for frontline services and other related seminars"),
    ("ADMIN", "Records management and digitization training"),
    ("ADMIN", "ISO-related seminars and trainings"),
    ("ADMIN", "Archiving and Records Management"),
    ("ADMIN", "Essentials of good housekeeping in the Registrar's Office"),
    ("ADMIN", "Implementing Rules and Guidelines for the Registrar's Office"),
    ("ADMIN", "Enablers: The Pathway to Quality Service of the Registrar's Office"),
    ("ADMIN", "Records Management"),
]


def main():
    execute(CREATE_TABLE_SQL)

    # Self-heal for a table created before source_year existed (same
    # pattern as seed_training_programs.py's reference_link column).
    existing_columns = {
        row["Field"] for row in fetch_all("SHOW COLUMNS FROM tna_2025_demand")
    }
    if "source_year" not in existing_columns:
        execute("ALTER TABLE tna_2025_demand ADD COLUMN source_year INT NULL")
        print("Added source_year column to tna_2025_demand.")
        # Backfill: every row already in this table before source_year
        # existed came from this file's own 2025 seed - safe to assume.
        execute("UPDATE tna_2025_demand SET source_year = 2025 WHERE source_year IS NULL")

    inserted = 0
    for college_code, title in TNA_ITEMS:
        before = fetch_all(
            "SELECT COUNT(*) c FROM tna_2025_demand WHERE college_code=%s AND title=%s",
            (college_code, title),
        )[0]["c"]
        execute(
            "INSERT IGNORE INTO tna_2025_demand (college_code, title, source_year) VALUES (%s, %s, 2025)",
            (college_code, title),
        )
        if before == 0:
            inserted += 1

    by_college = {}
    for college_code, _ in TNA_ITEMS:
        by_college[college_code] = by_college.get(college_code, 0) + 1

    print(f"tna_2025_demand: {inserted} new rows inserted, {len(TNA_ITEMS)} total in source list.")
    for college_code, count in sorted(by_college.items()):
        print(f"  {college_code}: {count}")
    print("  CCS, CHMT, COF: 0 (submitted nothing for TNA 2025 - intentional)")


if __name__ == "__main__":
    main()
