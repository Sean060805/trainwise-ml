"""
Seed for tna_2025_demand (shared table, multi-year despite the name - see
seed_tna_2025.py's top comment) covering LSPU's "Summary of Training Needs
Assessment (TNA) 2024" document (docs/SUMMARY OF TNA 2024.pdf in the
trainwise repo), transcribed verbatim as (college_code, title) pairs.

Obtained 2026-09-07 directly from HR (Dr. Imee Prescilla P. Sanchez, PhD,
Administrative Officer IV, HRMO) alongside the 2027 data (see
seed_tna_2027.py) - 2023 and earlier could not be obtained; Dr. Sanchez
started at LSPU in Dec 2023 and, as a matter of practice, declined to
source records she didn't personally prepare.

Notably: CCS, CHMT, and COF (College of Fisheries) - the three colleges
that submitted NOTHING for TNA 2025 (see seed_tna_2025.py) - all
submitted real, substantial requests in 2024. This is the direct fix for
the gap that caused the "Dexter/COF" incident documented in
ml_recommendations.php and the trainwise-ml session history: those three
colleges now have real official TNA rows to boost against, not just the
self-reported assessment fallback.

Same idempotent convention as seed_tna_2025.py: INSERT IGNORE against the
shared UNIQUE(college_code, title) constraint, safe to re-run.

Run:
    python scripts/seed_tna_2024.py
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

# (college_code, title) - transcribed from docs/SUMMARY OF TNA 2024.pdf.
# Duplicate/near-duplicate lines within the same college's raw list
# (e.g. CCS repeating "Data Science" many times, CTE repeating "Training
# on the Different Learning Modalities") are merged to one row each, same
# convention as seed_tna_2025.py - the UNIQUE constraint would reject
# plain repeats anyway, but de-duping here keeps this source list honest
# about what was actually distinct. Obvious typos in the source are
# corrected in-line and noted (e.g. "Phyton" -> "Python").
TNA_ITEMS = [
    # ---- CCJE (17 unique titles) ----
    ("CCJE", "Specialization Training in Forensic Ballistics"),
    ("CCJE", "Lean Six Sigma Training and Certification"),
    ("CCJE", "Advance Security Management Course/National Certificate Course for Security Services"),
    ("CCJE", "Training for Accreditation of an Agency"),
    ("CCJE", "Leadership Training"),
    ("CCJE", "Forensic Sciences Training"),
    ("CCJE", "Cyber Crime Investigation"),
    ("CCJE", "Career Development Seminar"),
    ("CCJE", "Syllabus, TOS, Curriculum Mapping"),
    ("CCJE", "Bosh - SO1 Training"),
    ("CCJE", "Criminal Justice in Digital Era"),
    ("CCJE", "Training for Specialization in Forensic Dactyloscopy"),
    ("CCJE", "Research Training (Criminological Research)"),
    ("CCJE", "Law Enforcement-Related Trainings and Investigation Courses"),
    ("CCJE", "Legal Trainings Relating to Criminal Justice"),
    ("CCJE", "Criminalistics Specialist"),
    ("CCJE", "Advanced Digital Evidence Processing"),
    ("CCJE", "Digital Forensics"),

    # ---- COF / College of Fisheries (12 unique titles) - this college
    # submitted zero rows for TNA 2025, see the module docstring above. ----
    ("COF", "Food Safety Training"),
    ("COF", "Advanced Molecular Biology Training"),
    ("COF", "HACCP and GMP on Food"),
    ("COF", "NCII Aquaculture (for renewal)"),
    ("COF", "GSIS and CSC Training for new policies"),
    ("COF", "Renewal of the Fisheries Technology Licensure"),
    ("COF", "Renewal of PRC/LFT and LEFT"),
    ("COF", "Fish Feed Nutrition related trainings"),
    ("COF", "Aquatic Ecology and Biodiversity related trainings"),
    ("COF", "Refresher course in Capture Fisheries - Fishing gears"),
    ("COF", "Refresher course in Capture Fisheries - Seamanship and Navigation"),
    ("COF", "Refresher course in Capture Fisheries - Fishery Laws (RA 8550 & RA 10654)"),

    # ---- CHMT (5 unique titles) - also zero rows for TNA 2025. ----
    ("CHMT", "Research Publication"),
    ("CHMT", "Use of Statistical Analysis Tools"),
    ("CHMT", "Short Course on Sustainable Development"),
    ("CHMT", "Community Guiding to Regional Guiding"),
    ("CHMT", "Train the Trainers"),

    # ---- CCS (19 unique titles) - also zero rows for TNA 2025. ----
    ("CCS", "Training on Machine Learning"),
    ("CCS", "Data Science"),
    ("CCS", "Green Technology"),
    ("CCS", "Technology on Solid Waste Management"),
    ("CCS", "Graphic Design"),
    ("CCS", "UI/UX Design"),
    ("CCS", "Leadership Training Programs"),
    ("CCS", "Internet of Things"),
    ("CCS", "Algorithm and Complexity"),
    ("CCS", "Agri-tech and Green Technology"),
    ("CCS", "Technopreneurship"),
    ("CCS", "Animation and Design"),
    ("CCS", "Data Mining"),
    ("CCS", "Programming using Python"),  # source: "Phyton" (typo, corrected)
    ("CCS", "Cisco Networking Technology"),
    ("CCS", "AI Development"),
    ("CCS", "Training on Hydroinformatics"),  # source: "Hyroinformatics" (typo, corrected)
    ("CCS", "AI and Machine Learning"),
    ("CCS", "Research and Development"),

    # ---- CTE (33 unique titles) ----
    ("CTE", "Training on the Different Learning Modalities"),
    ("CTE", "Mental Health of Faculty Members and Implications to Performance"),
    ("CTE", "Use of Gender-Sensitive Language in the Workplace"),
    ("CTE", "Work-life balance, job satisfaction and performance of faculty in SUC"),
    ("CTE", "Latest trends and updates in the Utilization of SPSS in Research"),
    ("CTE", "Enhancing Soft Skills"),
    ("CTE", "SDG #4 Quality Education"),  # source: "SDH #4" (likely typo for SDG 4)
    ("CTE", "Artificial Intelligence in the Teaching and Learning Process"),
    ("CTE", "Educational Research Practices in VZICAP"),
    ("CTE", "TEFL Webinar Series"),
    ("CTE", "IELTS"),  # source: "IELTA" (likely typo for IELTS)
    ("CTE", "Webinar related to Language"),
    ("CTE", "Scientific Writing and Editing"),
    ("CTE", "Preparing Scientific Posters and Presentations"),
    ("CTE", "Gender, Professional Development and Ethics among Educators"),
    ("CTE", "Multidisciplinary Research Training - workshop"),
    ("CTE", "Health and Wellness Management and Practices"),
    ("CTE", "Intensive Extension Community Service Training"),
    ("CTE", "Research Publication and Mentoring Training - workshop"),
    ("CTE", "Latest Developments and Trends in the Field of TLE"),
    ("CTE", "Sports Officiating Training and Seminar"),
    ("CTE", "Internalization of University Technologies and Innovation"),
    ("CTE", "Quality Assurance related training"),
    ("CTE", "Math Education related training"),
    ("CTE", "Training-workshops on Designing Social Science Research"),
    ("CTE", "Training-workshops for Museum Educators and Guides"),
    ("CTE", "Civic Engagement and Volunteerism Workshop"),
    ("CTE", "21st Century Training-workshop for Social Studies Education"),
    ("CTE", "AI Utilization seminar for Social Studies Educators"),
    ("CTE", "Artificial Intelligence in the Academe/Research Development"),
    ("CTE", "Inclusive Practices in the Tertiary Classroom"),
    ("CTE", "Seminar about Makabansa Curriculum"),
    ("CTE", "Pollution Control Training"),
    ("CTE", "Aseptic Techniques on Microbiology Training"),
    ("CTE", "Environmental Risk Management Training"),

    # ---- ADMIN (blended non-teaching offices, same scoping decision as
    # seed_tna_2025.py - 31 unique titles) ----
    ("ADMIN", "Practical Applications of AI in Libraries"),
    ("ADMIN", "Ethical Considerations and Challenges Associated with AI"),
    ("ADMIN", "Tools for Managing Library Data Effectively"),
    ("ADMIN", "Cooperative acquisition of electronic resources in academic libraries"),
    ("ADMIN", "Collaboration and knowledge sharing among librarians on Data Management Issues"),
    ("ADMIN", "Trainings related to Government Budgeting"),
    ("ADMIN", "Seminar on Records Management Office"),
    ("ADMIN", "Seminar about Record Keeping and Disposal"),
    ("ADMIN", "Seminar about File Security and Proper Data Keeping"),
    ("ADMIN", "Performance Management for Government Employees"),
    ("ADMIN", "Updates on Benefits (GSIS & Pag-ibig) for government employees"),
    ("ADMIN", "Upgrading for Electrical course/refrigeration air-conditioning tech"),
    ("ADMIN", "Advance Internal Audit based on ISO 9001:2015 Requirements and ISO 19011:2018 Guidelines"),
    ("ADMIN", "Employees' Compensation Program Webinar"),
    ("ADMIN", "GFAL Financial Literacy"),
    ("ADMIN", "GSIS New Employees Orientation Webinar"),
    ("ADMIN", "GSIS Updates Webinar"),
    ("ADMIN", "MPA Paskuhan: Reaching Public Service Through New Normal Approach"),
    ("ADMIN", "Disaster Preparedness in School or University"),
    ("ADMIN", "Introduction to Occupational Safety and Health"),
    ("ADMIN", "Disaster Management"),
    ("ADMIN", "Earthquake preparedness"),
    ("ADMIN", "Anti-harassment and Workplace Safety"),
    ("ADMIN", "Workplace Violence and Workplace Substance Abuse"),
    ("ADMIN", "Life Coaching Seminar Workshop Identification of Student at Risk"),
    ("ADMIN", "Gender Sensitivity and Anti-Sexual Harassment Seminar"),
    ("ADMIN", "Emergency Response Procedure"),
    ("ADMIN", "Access Control of Perimeter Security"),
    ("ADMIN", "Patrolling Techniques and Surveillance Methods"),
    ("ADMIN", "First Aid Training"),
    ("ADMIN", "Fire Prevention and Safe Evacuation"),
]


def main():
    execute(CREATE_TABLE_SQL)

    existing_columns = {
        row["Field"] for row in fetch_all("SHOW COLUMNS FROM tna_2025_demand")
    }
    if "source_year" not in existing_columns:
        execute("ALTER TABLE tna_2025_demand ADD COLUMN source_year INT NULL")
        print("Added source_year column to tna_2025_demand.")
        execute("UPDATE tna_2025_demand SET source_year = 2025 WHERE source_year IS NULL")

    inserted = 0
    for college_code, title in TNA_ITEMS:
        before = fetch_all(
            "SELECT COUNT(*) c FROM tna_2025_demand WHERE college_code=%s AND title=%s",
            (college_code, title),
        )[0]["c"]
        execute(
            "INSERT IGNORE INTO tna_2025_demand (college_code, title, source_year) VALUES (%s, %s, 2024)",
            (college_code, title),
        )
        if before == 0:
            inserted += 1

    by_college = {}
    for college_code, _ in TNA_ITEMS:
        by_college[college_code] = by_college.get(college_code, 0) + 1

    print(f"tna_2025_demand (2024 batch): {inserted} new rows inserted, {len(TNA_ITEMS)} total in source list.")
    for college_code, count in sorted(by_college.items()):
        print(f"  {college_code}: {count}")


if __name__ == "__main__":
    main()
