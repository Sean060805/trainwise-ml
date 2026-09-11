"""
Seed for tna_2025_demand (shared table, multi-year despite the name - see
seed_tna_2025.py's top comment) covering LSPU's "Summary of Training Needs
Assessment (TNA) 2027" document (docs/SUMMARY OF TNA 2027.pdf in the
trainwise repo) - the most recent/forward-looking of the three years
obtained, transcribed verbatim as (college_code, title) pairs.

Obtained 2026-09-07 directly from HR (Dr. Imee Prescilla P. Sanchez, PhD,
Administrative Officer IV, HRMO) alongside the 2024 data (see
seed_tna_2024.py).

CFND submitted nothing in this particular round (the source sheet shows
a "CFND" section header immediately followed by "CIHTM" with no items
between them) - left unseeded here, same "no rows = no boost, never an
error" handling as every other college/year gap in this table.

Also seeds tna_top_priorities - a SEPARATE, institution-wide (not
per-college) top-10 ranked list that appeared on page 1 of this specific
document, described by Dr. Sanchez as the top 10 most-requested training
areas across the whole university. This is a different signal than the
per-college rows above (aggregate institutional priority, not a specific
college's request) so it gets its own table rather than being force-fit
into tna_2025_demand's per-college shape. See admin_page.php /
training_pipeline.php for where this is surfaced to HR.

Same idempotent convention as seed_tna_2025.py: INSERT IGNORE, safe to
re-run.

Run:
    python scripts/seed_tna_2027.py
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

CREATE_TOP_PRIORITIES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tna_top_priorities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_year INT NOT NULL,
    rank_position INT NOT NULL,
    training_area VARCHAR(255) NOT NULL,
    key_topics TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_year_rank (source_year, rank_position)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# (college_code, title) - transcribed from docs/SUMMARY OF TNA 2027.pdf,
# page 2 onward. Duplicate/near-duplicate lines merged, same convention
# as seed_tna_2024.py/seed_tna_2025.py.
TNA_ITEMS = [
    # ---- CCJE (10 unique titles) ----
    ("CCJE", "Digital Forensic - Cybercrime Investigation Training"),
    ("CCJE", "Forensic Science Training (Forensic Ballistics)"),
    ("CCJE", "Advance Security Management Course/Training"),
    ("CCJE", "Quality Assurance -related course training"),
    ("CCJE", "Research and Extension related training"),
    ("CCJE", "Questioned Document Examination Workshop"),
    ("CCJE", "Leadership training"),
    ("CCJE", "Forensic Dactyloscopy training"),
    ("CCJE", "Extension"),
    ("CCJE", "Patent development"),

    # ---- COF / College of Fisheries (11 unique titles) ----
    ("COF", "Induced breeding of African catfish"),
    ("COF", "Refresher course in Fisheries Technology"),  # source: "Rfresher" (typo, corrected)
    ("COF", "Horticulture-related trainings, seminars, and conferences"),
    ("COF", "Training on DRRM, BLS"),
    ("COF", "Training on Aquaculture and Post-harvest"),
    ("COF", "Governance, legal framework and educational policy"),
    ("COF", "Student mental health, safety and crisis intervention"),
    ("COF", "Leadership, strategic management and quality assurance"),
    ("COF", "Diversity, equity, inclusion and student welfare"),
    ("COF", "Institutional research in student affairs"),
    ("COF", "Research dissemination and policy translation"),

    # ---- CHMT / CIHTM (3 unique titles) ----
    ("CHMT", "Global Professional Advancement (CTMP and CHMP Certification)"),
    ("CHMT", "Training on Gender Analysis Tools, Diversity and Inclusion Training for Students with Special Needs & PWDs, Training the Trainers, Seminar/Workshop on Women Empowerment, Preventing Violence Against Women, Work Ethics and Anti-Sexual Harassment"),
    ("CHMT", "Training and Seminars Geared Towards Research and Extension, Capability Development Workshops"),

    # ---- CCS (18 unique titles) ----
    ("CCS", "Emerging technologies"),
    ("CCS", "Information technology education"),
    ("CCS", "Micro-credentials"),
    ("CCS", "Green technology"),
    ("CCS", "Data analytics"),
    ("CCS", "Cyber security"),
    ("CCS", "Business analytics"),
    ("CCS", "Big data"),
    ("CCS", "Advanced statistical tests"),
    ("CCS", "Artificial intelligence"),
    ("CCS", "Object Orientation Programming"),
    ("CCS", "Occupational Health and Safety (OHS)"),
    ("CCS", "Data privacy, cyber security"),
    ("CCS", "Database management systems"),
    ("CCS", "Robotics training, Artificial intelligence literacy"),
    ("CCS", "Data Science and Analytics bootcamps"),
    ("CCS", "Cloud computing and AI infrastructure, Modern Dev Ops and Agile Framework"),
    ("CCS", "Quantum Computing seminars and other science and technology related seminar"),

    # ---- CTE (11 unique titles) ----
    ("CTE", "Entrepreneurship and financial literacy training - DTI/DepEd"),
    ("CTE", "Product development and packaging for school-based enterprises"),
    ("CTE", "Cookery, baking and food processing trainings - TESDA/DTI"),
    ("CTE", "TESDA-based technical trainings on dressmaking"),
    ("CTE", "Production of household products such as soap making, candle making, disinfectant"),
    ("CTE", "Trainings and seminars that give CPD units to the faculty"),
    ("CTE", "Graduate research for empowerment, advancement and transformation"),
    ("CTE", "Book publication"),
    ("CTE", "Filipino-related seminar-workshops"),
    ("CTE", "Sports officiating training workshop"),
    ("CTE", "Specialized training-workshop in research (Social Science)"),

    # ---- CBAA (10 unique titles) ----
    ("CBAA", "Research Training and Seminar"),
    ("CBAA", "Accounting seminars"),
    ("CBAA", "Accounting information systems seminars"),
    ("CBAA", "Strategic Management and business planning"),
    ("CBAA", "Business innovation and entrepreneurship"),
    ("CBAA", "Quality Management Systems (ISO 9001:2015)"),
    ("CBAA", "Artificial Intelligence for business leaders"),
    ("CBAA", "Extension Program and Project Proposals In-house Review and Presentation"),
    ("CBAA", "Diskartepreneur and Unlad Tulay ng Barangay"),
    ("CBAA", "Human Resource Management seminar"),

    # ---- ADMIN (blended non-teaching offices - by far the largest list
    # this year, reflecting the top-10 priorities below being heavily
    # records/finance/procurement/HR weighted) ----
    ("ADMIN", "Technology and Systems: modern integrated library systems, discovery layers and database migration"),
    ("ADMIN", "Emerging Literacies and AI: guiding responsible AI usage, data privacy, and managing digital mis/disinformation"),
    ("ADMIN", "Legal and Policy Standards: intellectual property and copyright training for educators and information specialists"),
    ("ADMIN", "COA Rules and Regulations updates"),
    ("ADMIN", "Government accounting and budgeting"),
    ("ADMIN", "Cash management and treasury operations"),
    ("ADMIN", "Competency-based recruitment seminar/training"),
    ("ADMIN", "Supervisory track training"),
    ("ADMIN", "Mental health management training/health and wellness seminar"),
    ("ADMIN", "Records disposal/ PAGBA HR Issues"),
    ("ADMIN", "PAGBA seminar which strengthens public financial management"),
    ("ADMIN", "Cash management system"),
    ("ADMIN", "PICPA seminar"),
    ("ADMIN", "Government disbursement policies, rules and procedures"),
    ("ADMIN", "Updates on COA circulars and issuances"),
    ("ADMIN", "Payroll processing and salary administration"),
    ("ADMIN", "Electronic payment systems and digital disbursement"),
    ("ADMIN", "Commission on Audit - annual seminar"),
    ("ADMIN", "Training/seminar relevant to RA No. 12009 (NGPA 12009)"),
    ("ADMIN", "Training/seminar regarding Annual Procurement Plan and PPMP"),
    ("ADMIN", "Training/seminar regarding PhilGEPS"),
    ("ADMIN", "Mastering Early Procurement Strategies"),
    ("ADMIN", "Training/updates on Agency Procurement Compliance and Performance Indicator (APCPI)"),
    ("ADMIN", "Disposal and Derecognition"),
    ("ADMIN", "Avoiding COA Disallowances"),
    ("ADMIN", "Appraising or Valuation of Serviceable PPE and Inventories with GSIS"),
    ("ADMIN", "Trainings related to government budgeting (PAGBA, COA, AGIA)"),
    ("ADMIN", "Basic computer skills and digital record keeping materials"),
    ("ADMIN", "Inventory management"),
    ("ADMIN", "Preventive maintenance of building facility"),
    ("ADMIN", "Customer service and effective communication"),
    ("ADMIN", "Building and facilities management (modern technologies)"),
    ("ADMIN", "Fleet, asset and property management"),
    ("ADMIN", "Basic Life Support (BLS)"),
    ("ADMIN", "Advanced Cardiac Life Support (ACLS)"),
    ("ADMIN", "Standard first aid"),
    ("ADMIN", "Risk mitigation in records management"),
    ("ADMIN", "Preparedness and business continuity"),
    ("ADMIN", "Electronic records management"),
    ("ADMIN", "Effective records management"),
    ("ADMIN", "Seminar-workshop on records disaster and preparedness"),
    ("ADMIN", "Competency-based behavioral event interview"),
    ("ADMIN", "Digital transformation"),
    ("ADMIN", "HR analytics"),
    ("ADMIN", "Workplace wellness"),
    ("ADMIN", "Basic records management"),
    ("ADMIN", "Records disposition administration"),
    ("ADMIN", "Digitalization - records management"),
    ("ADMIN", "Policies and procedures on Leave Administration"),
    ("ADMIN", "Payroll processing and documentation"),
    ("ADMIN", "PRIME-HRM all system"),
    ("ADMIN", "RACCCS"),
    ("ADMIN", "Laws and regulations on government expenditures"),
    ("ADMIN", "Leadership and Ethics"),
    ("ADMIN", "Modernized Philippine Government Electronic Procurement System"),
    ("ADMIN", "Managing the Life Cycle of Government Assets"),
    ("ADMIN", "Decoding COA rules, circulars and common audit findings"),
    ("ADMIN", "Preparation of APP-CSE on the PhilGEPS"),
    ("ADMIN", "University, College and School Registrar Association, Inc. (UCSRA) convention/training/workshop"),
    ("ADMIN", "National Association of Registrars of State Universities and Colleges (NARSUC) convention/training"),
    ("ADMIN", "Civil Service Commission training and workshop for frontline services and other related seminars"),
    ("ADMIN", "Records management and digitization training"),
    ("ADMIN", "ISO-related seminars and trainings"),
]

# (rank, training_area, key_topics) - page 1 of docs/SUMMARY OF TNA 2027.pdf,
# described by Dr. Sanchez as the top 10 most-requested training areas
# institution-wide (aggregated across colleges, not per-college).
TOP_PRIORITIES = [
    (1, "Digital Transformation, Artificial Intelligence and Emerging Technologies",
        "AI, AI literacy, emerging technologies, digital transformation, cloud computing, robotics, DevOps, Agile, quantum computing, IT systems"),
    (2, "Research, Extension and Innovation",
        "Research methodology, research dissemination, institutional research, extension programs, project development, research publication, patent development, innovation"),
    (3, "Leadership, Management and Governance",
        "Leadership, supervisory management, strategic management, business planning, governance, ethics, educational policy, management development"),
    (4, "Records Management, Digitization and Information Management",
        "Records management, electronic records, records digitization, records disposal, records retention, digital archiving, disaster preparedness and business continuity"),
    (5, "Financial Management, Accounting, Budgeting and COA Compliance",
        "Government accounting, budgeting, cash management, treasury operations, disbursement, payroll, COA rules, audit findings, COA compliance"),
    (6, "Procurement, Property and Asset Management",
        "RA No. 12009/NGPA, PhilGEPS, APP, PPMP, APCPI, procurement strategies, inventory, disposal and derecognition, PPE valuation, asset lifecycle management"),
    (7, "Cybersecurity, Data Privacy and Digital Forensics",
        "Cybersecurity, data privacy, cybercrime investigation, digital forensic investigation, information security"),
    (8, "Quality Assurance, ISO and Institutional Development",
        "Quality assurance, ISO 9001:2015, quality management systems, institutional compliance, accreditation and continuous improvement"),
    (9, "Human Resource Management, Civil Service and Professional Development",
        "Competency-based recruitment, behavioral event interviews, HR analytics, PRIME-HRM, RACCCS, CSC policies, leave administration, professional development and CPD"),
    (10, "Health, Wellness, Safety, Gender and Inclusive Student/Employee Welfare",
        "Mental health, workplace wellness, BLS, ACLS, first aid, DRRM, occupational health and safety, GAD, diversity and inclusion, student welfare and crisis intervention"),
]


def main():
    execute(CREATE_TABLE_SQL)
    execute(CREATE_TOP_PRIORITIES_TABLE_SQL)

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
            "INSERT IGNORE INTO tna_2025_demand (college_code, title, source_year) VALUES (%s, %s, 2027)",
            (college_code, title),
        )
        if before == 0:
            inserted += 1

    priorities_inserted = 0
    for rank, area, topics in TOP_PRIORITIES:
        before = fetch_all(
            "SELECT COUNT(*) c FROM tna_top_priorities WHERE source_year=2027 AND rank_position=%s",
            (rank,),
        )[0]["c"]
        execute(
            "INSERT IGNORE INTO tna_top_priorities (source_year, rank_position, training_area, key_topics) VALUES (2027, %s, %s, %s)",
            (rank, area, topics),
        )
        if before == 0:
            priorities_inserted += 1

    by_college = {}
    for college_code, _ in TNA_ITEMS:
        by_college[college_code] = by_college.get(college_code, 0) + 1

    print(f"tna_2025_demand (2027 batch): {inserted} new rows inserted, {len(TNA_ITEMS)} total in source list.")
    for college_code, count in sorted(by_college.items()):
        print(f"  {college_code}: {count}")
    print("  CFND: 0 (submitted nothing in this round)")
    print(f"tna_top_priorities: {priorities_inserted} new rows inserted, {len(TOP_PRIORITIES)} total.")


if __name__ == "__main__":
    main()
