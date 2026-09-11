"""
Creates the `training_programs` table (doesn't exist in the current DB —
see CLAUDE.md) and seeds it with a catalog for the pipeline to index and
rank against.

v2: expanded from 6 to 18 programs across 9 categories, with longer,
more distinctive descriptions. The original 6-entry catalog had two
problems visible in testing: too few programs to meaningfully rank, and
descriptions short/generic enough that SBERT couldn't reliably tell them
apart on paraphrased queries. This version fixes both.

v3: added reference_link - a real, verified free course/seminar URL per
program (mostly Coursera/edX/IBM SkillsBuild, plus the official GPPB
ProHub for the procurement program) so the recommendation carries an
actual place to go take the training, not just a description. Per
adviser feedback, the Start/Decline buttons on the employee-facing page
are disabled until a link exists for that specific recommendation - see
training_recommendations.php.

v4: added 2 more programs (20 total) - Introduction to Artificial
Intelligence and Machine Learning, and Public Speaking and Presentation
Skills. Found via a real test account (department "OSAS", desired
training "Machine Learning and AI Basics" / "Public Speaking") whose
recommendations came back weak because neither topic had a genuine
match anywhere in the catalog - SBERT could only ever return its
*closest* available program, not a *correct* one. This isn't the same
class of issue as the cold-start department gap (see canonical_department
in app/ml/features.py) - that was a missing categorical bucket with an
existing safe fallback; this is a genuine content gap in the catalog
itself, which only gets fixed by adding the missing programs.

v5: added 2 more Student Affairs programs (22 total). Student Affairs
was down to a single program (Student Mental Health First Aid) - anyone
whose recommendation profile leaned that direction had no second
genuinely-relevant option, only lower-relevance filler from other
categories. Both new entries are deliberately distinct from the
existing one and from each other: incident/conduct handling vs.
proactive career guidance, neither overlapping with "recognize distress
and refer to counseling."

v6 (2026-09-03, pre-TAM-test fix): added 5 non-teaching-office programs
(27 total). Found via a real TAM pre-test walkthrough with a synthetic
Registrar's Office account: of the (at the time) 16 Workshop/Seminar-
eligible programs, only 2 (Records Management, Procurement and Budget
Preparation) spoke to non-teaching office work at all - everything else
was teaching/pedagogy or academic-research flavored. With 5 of the
2026-09-02 non-teaching-office dropdown's 5 curated offices (Registrar's,
Accounting/Budget, HRMO, Supply/Property, Library) having little or
nothing to genuinely match against, half the TAM panel (10 non-teaching
respondents) risked weak/generic recommendations on the exact
questionnaire items ("appropriate for my work," "relevant to my
training needs") this system is being tested on tomorrow. One new
program targets each of the 5 offices' actual day-to-day work, plus one
broadly-applicable front-line/customer-facing addition (several of
those offices interact directly with students/faculty at a counter).
NOTE: also discovered while making this change that the live DB only
had 18 rows (v3-era) even though this script had already been edited up
through v5 (22 entries) - the v4/v5 edits were apparently never actually
run against the live DB. This re-run brings the DB fully current in one
pass, not just adding the 5 new v6 entries.

v7 (2026-09-03, DURING live TAM testing - real respondent #1, College of
Fisheries): added 20 college-specific programs across the 10 colleges
that had zero genuine subject-matter coverage (47 total). Found live:
a real COF faculty respondent asked for "Induced Breeding of African
Catfish" - checked directly against every program in the catalog via
/similarity_check, and the single best match anywhere scored 0.05
(noise; a real match scores 0.4-0.7). Same root cause as v4's OSAS/
"Machine Learning" gap and v6's non-teaching-office gap: SBERT can only
ever return its *closest* available program, never a *correct* one that
doesn't exist. Rather than wait for another respondent from CA, CBAA,
COE, CIT, CIHTM, CONAH, COL, or CCJE/CFND (which have *official*
2025 TNA data, but that only *boosts* an existing catalog match, it
doesn't manufacture one from nothing - checked their TNA titles too,
e.g. CCJE's forensic-document-examination content has nothing to boost
either) to hit the exact same wall, added 2 programs per college
covering that college's actual professional subject matter - not
generic pedagogy/research filler, which every college already has
plenty of via the Pedagogy/Research/Assessment categories. Kept
deliberately distinct in subject and category from everything already
in the catalog and from each other, matching this file's own established
"long, specific, distinctive descriptions" standard (see the v2 note
above) - the goal is more colleges with a genuine match, not more
similar-sounding filler that would make it *harder* for SBERT to tell
programs apart.

v8 (2026-09-03, later same day - testing paused after the Dexter/COF
incident, so there was time to do this properly instead of flagging it
for later): the 20 v7 reference_link URLs were guessed slugs, never
opened in a browser, unlike every earlier batch in this file. Checked
all 18 non-null ones directly - 16 of 18 were dead (404). Replaced each
with a real course found via search and confirmed live before being
added (same standard as v2's original "verified" claim). 3 could not
find a genuinely matching real course (Aquaculture Systems and Fish
Breeding Techniques - the one course found was coldwater/salmonid-
specific, a real topical mismatch against this program's tropical/
brackish-water subject; Legal Research, Writing, and Case Analysis
Methodology; Criminology Research Methods and Crime Data Analysis - its
one real prior candidate, a Saint Petersburg State University course,
is no longer on Coursera at all since Coursera suspended cooperation
with Russian universities in 2022) - set to None rather than force a
wrong link, same convention already used for 2 other v7 entries.

v10 (2026-09-06, spot-check after COF/Dexter was confirmed fixed): added 1
Law program (48 total). Ran audit_catalog_coverage.py again plus a manual
spot-check of plausible real queries against the two colleges with zero
data on file yet (COL, CHMT) - CHMT came back fine, but COL's "Human
Rights Law and International Humanitarian Law" scored 0.25 against the
whole catalog (closest match: an unrelated nursing program) - the same
"no genuine match exists yet" pattern as Fisheries and Gender & Development,
just caught proactively via a hypothetical test query instead of a real
respondent, since COL has never had one. Kept distinct from the two
existing Law programs (Legal Research/Writing skill-building, and staying
current on Jurisprudence) - this one is substantive human-rights/IHL
subject content. reference_link found via a real search (not a guessed
slug - two guessed slugs in this file already went dead, see v8) and
fetched directly to confirm the page is live before adding it.

v11 (2026-09-06, full-catalog link audit): checked every reference_link
in this file, not just ones tied to a live incident - fetched each URL
directly and read the actual page content against what the program's
description promises, following the same standard v8 introduced.
Result: 2 dead (404) and 8 live-but-wrong (real course, wrong subject -
e.g. "Leadership and People Management for Educators" pointed at an ASQ
Six Sigma Black Belt exam-prep course; "Records Management" pointed at
a generic Meta data-analyst intro with zero retention-schedule content;
"Community Nutrition and Dietary Counseling" pointed at a consumer
personal-diet specialization, not a professional-counseling one).
A live-but-wrong link is worse than a guessed-and-dead one (v8's
problem) - it looks authoritative and only fails once someone actually
clicks through, which for a capstone demo means a panelist or a real
TAM respondent. Also finally searched for the 2 entries that had been
sitting as bare `None` since v7 with no documented search at all
(Technical-Vocational Competency-Based Training, Updates in Philippine
Jurisprudence) - both had real, better-than-average matches available
(official government/accredited platforms) that a Coursera-only search
habit had missed.
Net changes: 4 replaced with a verified better link (Advanced Teaching
Methodologies -> Blended Learning Toolkit; Modern Library Systems ->
WebJunction's cataloging catalog, replacing its dead link; Sustainable
Tourism -> Sustainable High-End Tourism, a partial improvement, still
company-level rather than destination-level - noted, not oversold;
Community Nutrition -> Nutrition and Weight Management for Fitness
Professionals), 2 filled in for the first time with a verified real
link (Technical-Vocational -> e-TESDA's official Trainers Methodology
I; Updates in Philippine Jurisprudence -> Access MCLE Online's
jurisprudence-updates category), 6 set to None having confirmed no
stable, free, evergreen match exists (HR and Payroll Administration,
Leadership and People Management for Educators, Records Management,
Supply and Property Management, Hospitality Service Excellence,
Forensic Science and Criminal Investigation) - same "None is more
honest than wrong" principle as v8's 3 pre-existing None entries,
which were re-checked and left as-is (still no better option found).
7 programs with a real link that's on-topic but not a precise 1:1
match (e.g. Test Construction covers item construction but not
difficulty/discrimination index by name; Fisheries Resource Management
is fisheries-as-one-module-of-ocean-governance rather than fisheries-
specific) were deliberately left alone - this file's own established
standard already accepts "real, live, roughly relevant" elsewhere
(Grant Writing, Research Methods), and chasing a perfect match for
every entry has real diminishing returns against a near-term TAM
testing deadline.

Re-running this script is safe — it clears and reseeds every time, since
training_recommendations stores its own denormalized copy of the link at
recommendation time (see ml_recommendations.php refreshMLRecommendations),
so existing recommendations already shown to users aren't affected by a
reseed. Once PHP integration (Phase 5) is live and real recommendation
history exists, switch this to additive/idempotent seeding instead of
TRUNCATE.

    python scripts/seed_training_programs.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import execute, fetch_all

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS training_programs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100),
    training_type VARCHAR(100),
    target_department VARCHAR(255) DEFAULT NULL,
    reference_link VARCHAR(500) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# (title, description, category, training_type, target_department, reference_link)
PROGRAMS = [
    # -- Pedagogy --
    (
        "Advanced Teaching Methodologies Workshop",
        "A hands-on workshop covering blended learning, the flipped classroom "
        "model, and active-learning strategies such as think-pair-share and "
        "case-based discussion. Faculty leave with a redesigned lesson plan "
        "for one of their own courses, built around a specific teaching "
        "technique from the workshop.",
        "Pedagogy",
        "Workshop",
        None,
        # v11 (2026-09-06) - the old link ("Advanced Instructional
        # Strategies in the Virtual Classroom") was narrowly about K-12
        # *online* teaching only, not general blended/flipped-classroom
        # strategies. Verified live: this one explicitly covers active
        # learning and blended course design for faculty.
        "https://www.coursera.org/learn/blended-learning-toolkit",
    ),
    (
        "Outcomes-Based Education (OBE) Curriculum Design",
        "Focused on aligning course syllabi, learning outcomes, and "
        "assessments with institutional and program-level competencies. "
        "Covers writing measurable learning outcomes, constructive "
        "alignment, and mapping courses to CHED program outcomes.",
        "Pedagogy",
        "Seminar",
        None,
        "https://www.coursera.org/learn/instructional-design-foundations-applications",
    ),
    (
        "Inclusive Classroom Strategies",
        "Practical strategies for teaching students with diverse learning "
        "needs, including differentiated instruction, accommodations for "
        "students with disabilities, and culturally responsive teaching "
        "approaches for a mixed-ability classroom.",
        "Pedagogy",
        "Workshop",
        None,
        "https://www.coursera.org/learn/diversity-and-inclusion-education",
    ),

    # -- Research --
    (
        "Research Publication and Academic Writing Skills",
        "Covers the structure of a publishable research paper, journal "
        "selection strategy, responding to peer review, and avoiding "
        "common academic writing pitfalls. Ends with participants drafting "
        "an abstract for their own ongoing research.",
        "Research",
        "Seminar",
        None,
        "https://www.coursera.org/learn/how-to-write-a-scientific-paper",
    ),
    (
        "Research Methods and Statistical Analysis",
        "Introduces quantitative and qualitative research design, sampling "
        "methods, and statistical tools (SPSS/R) for analyzing survey and "
        "experimental data commonly used in institutional and classroom "
        "action research.",
        "Research",
        "Workshop",
        None,
        "https://www.coursera.org/specializations/social-science",
    ),
    (
        "Grant Writing and Research Funding",
        "Guidance on identifying funding opportunities (CHED, DOST, "
        "international grants), structuring a competitive proposal, and "
        "budgeting for a funded research project.",
        "Research",
        "Seminar",
        None,
        "https://www.coursera.org/specializations/grant-writing-for-health-researchers",
    ),

    # -- Technology --
    (
        "Digital Literacy and Educational Technology",
        "A practical, easy-to-follow course for teachers who want everyday "
        "help using computers, apps, and online tools in their classes — "
        "no technical background needed. Covers learning management "
        "systems (LMS), creating simple interactive lesson content, and "
        "everyday apps like Google Workspace and Canva for hybrid and "
        "online teaching.",
        "Technology",
        "Online Course",
        None,
        "https://skillsbuild.org/adult-learners",
    ),
    (
        "Data Analytics and Dashboards for Decision-Making",
        "Practical training on building spreadsheets, pivot tables, and "
        "dashboards (Excel, Google Sheets, Looker Studio) to track "
        "institutional metrics such as enrollment trends, program "
        "outcomes, and accreditation indicators.",
        "Technology",
        "Workshop",
        "CCS",
        "https://skillsbuild.org/adult-learners/explore-learning/data-analyst",
    ),
    (
        "Introduction to Programming for Non-IT Staff",
        "A hands-on coding course teaching programming fundamentals — "
        "variables, loops, and functions — through writing your own "
        "Python scripts to automate repetitive office tasks such as "
        "spreadsheet macros and batch file renaming. For staff who want "
        "to build and run small scripts themselves.",
        "Technology",
        "Online Course",
        None,
        "https://www.edx.org/learn/python/ibm-python-basics-for-data-science",
    ),
    (
        "Cybersecurity Awareness for University Staff",
        "Covers phishing recognition, password hygiene, safe handling of "
        "student records under the Data Privacy Act, and basic incident "
        "reporting procedures for university systems.",
        "Technology",
        "Seminar",
        None,
        "https://skillsbuild.org/learning-catalog",
    ),
    (
        "Introduction to Artificial Intelligence and Machine Learning",
        "An entry-level, non-technical introduction to how AI and machine "
        "learning actually work - no coding or math background required. "
        "Covers how AI makes predictions, understands language and images, "
        "and where it's already showing up in everyday tools, plus a "
        "hands-on simulation building and testing a simple machine "
        "learning model.",
        "Technology",
        "Online Course",
        None,
        "https://skillsbuild.org/adult-learners/explore-learning/artificial-intelligence",
    ),

    # -- Assessment --
    (
        "Student Assessment and Evaluation Techniques",
        "Covers formative and summative assessment design, rubric "
        "development, and giving constructive, actionable feedback on "
        "student work across different subject areas.",
        "Assessment",
        "Workshop",
        None,
        "https://www.coursera.org/learn/assessmentforlearning",
    ),
    (
        "Test Construction and Item Analysis",
        "Focused on writing valid, reliable multiple-choice and essay "
        "test items, and using item analysis (difficulty index, "
        "discrimination index) to improve exam quality over time.",
        "Assessment",
        "Workshop",
        None,
        "https://www.coursera.org/learn/assessment-higher-education",
    ),

    # -- Leadership --
    (
        "Leadership and People Management for Educators",
        "Develops leadership competencies for department chairs and "
        "program coordinators: delegation, conflict resolution, running "
        "effective meetings, and giving performance feedback to faculty "
        "under their supervision.",
        "Leadership",
        "Seminar",
        None,
        # v11 (2026-09-06) - the old link was actually an ASQ Six Sigma
        # Black Belt exam-prep course (manufacturing quality management),
        # not educator leadership. Searched for a real substitute - every
        # candidate found was either another generic business-leadership
        # course (same sector mismatch, just less obviously wrong) or a
        # guessed URL that 404'd. None is more honest than a wrong or
        # unstable link.
        None,
    ),
    (
        "Strategic Planning and Institutional Goal-Setting",
        "A workshop on translating institutional vision into department-"
        "level action plans, setting measurable annual targets, and "
        "monitoring progress against a strategic plan.",
        "Leadership",
        "Workshop",
        None,
        "https://www.coursera.org/learn/strategic-planning",
    ),

    # -- Administration --
    (
        "Records Management and Documentation Standards",
        "Covers proper filing, retention schedules, and digitization of "
        "academic and administrative records in compliance with COA and "
        "university audit requirements.",
        "Administration",
        "Seminar",
        None,
        # v11 (2026-09-06) - the old link was a generic Meta data-analyst
        # intro (data collection/storage/ML) with zero content on
        # retention schedules, digitization, or COA compliance. Real
        # options found (ICA, Wayne State, ACC) were professional-
        # association/university courses, not stable free evergreen
        # links matching this file's convention. None is more honest.
        None,
    ),
    (
        "Procurement and Budget Preparation",
        "Practical guidance on preparing departmental budget proposals, "
        "understanding government procurement procedures (RA 9184), and "
        "tracking budget utilization throughout the fiscal year.",
        "Administration",
        "Workshop",
        None,
        "https://learning.gppb.gov.ph/",
    ),

    # -- Communication --
    (
        "Effective Business Communication and Report Writing",
        "Focused on writing clear memos, official reports, and emails; "
        "structuring formal correspondence; and presenting information "
        "concisely to different audiences (superiors, peers, students).",
        "Communication",
        "Seminar",
        None,
        "https://www.coursera.org/learn/business-writing",
    ),
    (
        "Public Speaking and Presentation Skills",
        "A practical, framework-based approach to preparing and delivering "
        "presentations with confidence - structuring a talk, engaging an "
        "audience, managing nerves, and presenting clearly in meetings, "
        "seminars, or public events. Distinct from business writing: this "
        "is about spoken delivery, not written correspondence.",
        "Communication",
        "Workshop",
        None,
        "https://www.coursera.org/learn/public-speaking",
    ),

    # -- Student Affairs --
    (
        "Student Mental Health First Aid",
        "Trains faculty and staff to recognize early signs of student "
        "distress, respond appropriately in the moment, and refer "
        "students to the guidance office or counseling services.",
        "Student Affairs",
        "Seminar",
        None,
        "https://www.coursera.org/learn/psychological-first-aid",
    ),
    (
        "Conflict Resolution and De-escalation for Student Affairs",
        "Practical techniques for handling tense situations with "
        "students directly - de-escalating heated conversations, "
        "managing behavioral or disciplinary incidents fairly, and "
        "resolving conflicts between students or between a student and "
        "staff, without it turning into a formal case.",
        "Student Affairs",
        "Workshop",
        None,
        "https://www.coursera.org/learn/conflict-resolution-skills",
    ),
    (
        "Career Counseling and Guidance for Students",
        "For guidance staff and advisers who help students plan their "
        "career path - covers structuring a career coaching conversation, "
        "helping students identify their strengths and options, and "
        "connecting academic choices to real career outcomes.",
        "Student Affairs",
        "Online Course",
        None,
        "https://www.coursera.org/learn/foundations-of-career-navigating-and-coaching",
    ),

    # -- Non-Teaching Office Operations (v6, 2026-09-03) --
    (
        "Supply and Property Management Essentials",
        "Covers inventory control and stock-taking, asset tagging and "
        "tracking, proper disposal/write-off procedures for government "
        "property, and maintaining accurate supply and property records "
        "in compliance with COA regulations.",
        "Administration",
        "Workshop",
        None,
        # v11 (2026-09-06) - the old link was retail demand-forecasting/
        # inventory optimization, not asset tagging or government
        # property disposal procedures. No stable free match found for
        # this specific government-compliance niche. None is more
        # honest than a wrong link.
        None,
    ),
    (
        "HR and Payroll Administration Essentials",
        "Practical training for HR/administrative staff on leave credit "
        "computation, payroll processing basics, employee 201-file "
        "management, and government-mandated benefits (GSIS, Pag-IBIG, "
        "PhilHealth) reporting and compliance.",
        "Administration",
        "Seminar",
        None,
        # v11 (2026-09-06) - the old link 404'd. Real Philippine options
        # (PMAP, Businessmaker Academy) exist but are dated calendar
        # events, not stable evergreen course pages like this file's
        # other links - they'd go stale within weeks. None is more
        # honest than a link that will die again shortly.
        None,
    ),
    (
        "Modern Library Systems and Information Management",
        "Covers digital cataloging and integrated library systems, "
        "managing electronic/online resource subscriptions, and "
        "day-to-day patron circulation services for a modern academic "
        "library.",
        "Administration",
        "Workshop",
        None,
        # v11 (2026-09-06) - the old link 404'd. Replaced with
        # WebJunction's cataloging catalog (operated by OCLC for library
        # professionals) - real, live, free/guest-accessible, and
        # actually cataloging-specific (RDA, MARC-to-BIBFRAME, LC
        # Classification), a better fit than a generic Coursera hit
        # would have been.
        "https://learn.webjunction.org/course/index.php?categoryid=19",
    ),
    (
        "Basic Bookkeeping and Financial Recordkeeping for Non-Accountants",
        "An accessible introduction to double-entry bookkeeping, "
        "disbursement vouchers, and financial recordkeeping for staff in "
        "accounting/budget-adjacent roles without a formal accounting "
        "background - complements Procurement and Budget Preparation "
        "with the recordkeeping side rather than the planning side.",
        "Administration",
        "Workshop",
        None,
        "https://www.coursera.org/learn/bookkeeping-basics",
    ),
    (
        "Customer Service Excellence for Front-Line Staff",
        "For staff who deal directly with students, faculty, or the "
        "public at a counter or help desk (Registrar, Library, Accounting "
        "windows, etc.) - handling queues and difficult requests "
        "professionally, clear in-person and over-the-phone "
        "communication, and de-escalating frustrated visitors.",
        "Customer Service",
        "Seminar",
        None,
        "https://www.coursera.org/learn/customer-service-fundamentals",
    ),

    # -- Agriculture (v7, 2026-09-03) --
    (
        "Sustainable Crop Production and Soil Management",
        "Covers soil health assessment, sustainable fertilization and "
        "crop rotation practices, integrated pest management, and "
        "climate-resilient farming techniques for extension and "
        "instructional use. Participants leave with a soil management "
        "plan applicable to a real farm or demonstration plot.",
        "Agriculture",
        "Workshop",
        None,
        "https://www.coursera.org/learn/sustainable-agriculture",
    ),
    (
        "Livestock and Poultry Production Management",
        "Covers animal husbandry fundamentals, herd/flock health "
        "monitoring, breeding program basics, and production "
        "record-keeping for livestock and poultry operations, with an "
        "emphasis on practices instructors can bring back to farm "
        "laboratory instruction.",
        "Agriculture",
        "Seminar",
        None,
        "https://www.coursera.org/learn/livestock-farming",
    ),

    # -- Fisheries (v7, 2026-09-03) - added after a real TAM respondent
    # (College of Fisheries, "Induced Breeding of African Catfish") found
    # zero genuine matches anywhere in the catalog - see the v7 note above.
    (
        "Aquaculture Systems and Fish Breeding Techniques",
        "Covers hatchery operations, induced spawning and breeding "
        "techniques for freshwater and brackish-water species, "
        "broodstock management, and larval rearing systems for "
        "aquaculture production, plus water quality management "
        "fundamentals for hatchery and grow-out systems.",
        "Fisheries",
        "Workshop",
        None,
        # 2026-09-03 correction pass - the original guessed slug
        # ("/learn/aquaculture") was a 404. Searched for a real
        # replacement specifically for THIS program (it's the exact one
        # tied to the live Dexter/COF incident that started the v7
        # catalog expansion) and found nothing that genuinely matches
        # "induced breeding/hatchery for freshwater and brackish-water
        # species" - the closest real, live course found (US Fish &
        # Wildlife Service's "Coldwater Fish Culture") is specifically
        # about COLDWATER species (trout/salmon), not the tropical/
        # brackish-water species (tilapia, catfish) this program and the
        # real respondent's request are about - linking it would be a
        # genuine topical mismatch, not just an imperfect fit. None is
        # more honest than a wrong link, same reasoning as the two
        # pre-existing None entries below.
        None,
    ),
    (
        "Fisheries Resource Management and Sustainable Practices",
        "Covers fish stock assessment methods, sustainable "
        "capture-fisheries practices, marine and inland resource "
        "conservation, and regulatory compliance for fisheries "
        "management - aimed at fisheries faculty involved in extension "
        "work with local fishing communities.",
        "Fisheries",
        "Seminar",
        None,
        "https://www.coursera.org/learn/large-marine-ecosystems",
    ),

    # -- Business and Accountancy (v7, 2026-09-03) --
    (
        "Financial Statement Analysis and Accounting Standards Update",
        "Covers current Philippine Financial Reporting Standards (PFRS) "
        "updates, financial statement preparation and analysis, and "
        "common audit findings in academic and government accounting "
        "contexts - designed for accountancy faculty who need to stay "
        "current for both instruction and BOA CPD requirements.",
        "Business",
        "Seminar",
        None,
        "https://www.coursera.org/learn/financial-statement-ratio-analysis-accountants",
    ),
    (
        "Entrepreneurship and Small Business Management",
        "Covers business plan development, basic market research, "
        "startup financing options, and small-business operations "
        "management. Faculty leave with a structured business plan "
        "template usable directly in entrepreneurship courses.",
        "Business",
        "Workshop",
        None,
        "https://www.coursera.org/learn/entrepreneurshipfia",
    ),

    # -- Engineering (v7, 2026-09-03) --
    (
        "Engineering Project Management and Technical Design Practice",
        "Covers project planning and scheduling for engineering "
        "projects, technical design documentation standards, risk "
        "management, and stakeholder coordination for capstone and "
        "industry-linked engineering projects.",
        "Engineering",
        "Workshop",
        None,
        "https://www.coursera.org/learn/engineering-project-management-part-1",
    ),
    (
        "Emerging Technologies in Engineering Practice",
        "Surveys current developments in automation, renewable energy "
        "systems, and IoT-based monitoring relevant to civil, "
        "electrical, and mechanical engineering practice, with "
        "discussion of how to incorporate these topics into existing "
        "engineering curricula.",
        "Engineering",
        "Seminar",
        None,
        "https://www.coursera.org/learn/iot",
    ),

    # -- Technical Education (v7, 2026-09-03) --
    (
        "Technical-Vocational Competency-Based Training and Assessment",
        "Covers TESDA-aligned competency-based curriculum design, "
        "hands-on skills assessment methods, and trainer's methodology "
        "for technical-vocational instruction - aimed at industrial "
        "technology faculty who also serve as TESDA-accredited "
        "assessors or trainers.",
        "Technical Education",
        "Workshop",
        None,
        # v11 (2026-09-06) - this had been a bare, never-searched None
        # since v7. e-TESDA's own "Trainers Methodology I" (the actual
        # Philippine government TESDA trainer-certification pathway -
        # planning training sessions, conducting competency assessment,
        # supervising work-based learning) is arguably a stronger fit
        # than a generic MOOC would be for this exact program.
        "https://e-tesda.gov.ph/course/index.php?categoryid=31",
    ),
    (
        "Occupational Safety and Health in Technical Trades",
        "Covers workplace hazard identification, safety equipment and "
        "protocols for shop/laboratory environments, and OSH compliance "
        "requirements for technical-vocational training facilities "
        "under DOLE regulations.",
        "Technical Education",
        "Seminar",
        None,
        "https://www.coursera.org/learn/occupational-safety-and-health-administration-osha-basics",
    ),

    # -- Hospitality and Tourism (v7, 2026-09-03) --
    (
        "Hospitality Service Excellence and Guest Experience Management",
        "Covers service standards for front-of-house hotel and "
        "restaurant operations, guest complaint handling, and "
        "experience-design principles for hospitality management "
        "instruction, with practical service-recovery role-play "
        "exercises.",
        "Hospitality and Tourism",
        "Workshop",
        None,
        # v11 (2026-09-06) - the old link was a finance/budgeting
        # specialization, not front-of-house service or guest-complaint
        # handling. A promising real course (Dubai College of Tourism's
        # "Hotel Front Office Operations") turned out, when actually
        # opened, to be an enrollment-locked link ("not currently
        # available to all learners") - not usable. None is more honest
        # than a link that errors for most visitors.
        None,
    ),
    (
        "Sustainable Tourism and Destination Management",
        "Covers destination marketing, community-based and eco-tourism "
        "development, and sustainability practices for tourism "
        "planning - relevant to hospitality and tourism management "
        "faculty involved in local tourism development projects.",
        "Hospitality and Tourism",
        "Seminar",
        None,
        # v11 (2026-09-06) - the old link was actually titled "Sustainable
        # Tourism - promoting environmental public health" (mosquito
        # control, freshwater use, waste management) - a genuine subject
        # mismatch against "destination marketing and eco-tourism
        # development." Replaced with a closer (though still imperfect -
        # it's company-level luxury-tourism marketing, not destination-
        # level development) real, live match rather than leaving a
        # confirmed-wrong one in place.
        "https://www.coursera.org/learn/sustainable-high-end-tourism",
    ),

    # -- Nursing and Health (v7, 2026-09-03) --
    (
        "Clinical Nursing Skills Update and Patient Safety Standards",
        "Covers current clinical skills competencies, patient safety "
        "protocols, and infection control standards for nursing "
        "instruction, aligned with Philippine Nursing Board competency "
        "standards for clinical instructors.",
        "Nursing and Health",
        "Workshop",
        None,
        "https://www.coursera.org/learn/core-clinical-skills-checklist-nursing-students",
    ),
    (
        "Community and Public Health Nursing Practice",
        "Covers community health assessment, public health program "
        "planning, and health education delivery for community and "
        "public health nursing instruction, with case studies drawn "
        "from barangay-level health programs.",
        "Nursing and Health",
        "Seminar",
        None,
        "https://www.coursera.org/learn/community-public-health",
    ),

    # -- Law (v7, 2026-09-03) --
    (
        "Legal Research, Writing, and Case Analysis Methodology",
        "Covers legal research methodology, case briefing techniques, "
        "and legal writing standards for law faculty, with practical "
        "exercises in analyzing recent Supreme Court decisions for "
        "classroom use.",
        "Law",
        "Workshop",
        None,
        # 2026-09-03 correction pass - the original guessed slug was a
        # 404. Searched for a real replacement matching "legal research
        # methodology, case briefing, legal writing standards" and found
        # nothing that matches closely enough (Coursera's real legal-
        # research offerings found were narrowly AI-tool-focused, e.g.
        # "GenAI for Legal Research" - not a genuine substitute for this
        # program's actual subject). None is more honest than a
        # mismatched link.
        None,
    ),
    (
        "Updates in Philippine Jurisprudence and Legal Practice",
        "Covers recent Supreme Court rulings and legislative updates "
        "relevant to law instruction, professional responsibility "
        "considerations, and continuing legal education requirements "
        "for law faculty who are also practicing/bar-accredited "
        "lawyers.",
        "Law",
        "Seminar",
        None,
        # v11 (2026-09-06) - this had been a bare, never-searched None
        # since v7. Access MCLE Online's "Updates on Substantive and
        # Procedural Laws and Jurisprudence" category is real, live, and
        # Philippine MCLE-accredited - directly on-topic for bar-
        # accredited law faculty needing continuing legal education
        # credit, not just general interest content.
        "https://accessonline.ph/home/viewcourses",
    ),

    # -- Criminal Justice (v7, 2026-09-03) - CCJE has *official* 2025 TNA
    # data, but that only boosts an existing catalog match, it doesn't
    # manufacture one - checked CCJE's TNA titles (e.g. forensic document
    # examination) against the pre-v7 catalog and found the same
    # near-zero-everywhere pattern as the Fisheries case, so this college
    # got the same treatment even though it wasn't the college that
    # actually failed live.
    (
        "Forensic Science and Criminal Investigation Techniques",
        "Covers crime scene processing, evidence collection and "
        "chain-of-custody procedures, and an introduction to forensic "
        "analysis techniques (fingerprinting, ballistics, digital "
        "forensics) for criminal justice instruction.",
        "Criminal Justice",
        "Workshop",
        None,
        # v11 (2026-09-06) - the old link covers lab analytical methods
        # (chromatography, DNA, toxicology), not crime-scene processing,
        # evidence collection, or chain-of-custody procedures as
        # described. Only real alternative found ("Digital Forensics
        # Essentials") is a different subfield entirely (cyber evidence,
        # not physical CSI) - not a genuine substitute. None is more
        # honest than a wrong link.
        None,
    ),
    (
        "Criminology Research Methods and Crime Data Analysis",
        "Covers quantitative and qualitative research methods specific "
        "to criminology, crime statistics analysis, and using crime "
        "data for evidence-based policy discussion in criminal justice "
        "education.",
        "Criminal Justice",
        "Seminar",
        None,
        # 2026-09-03 correction pass - the original guessed slug was a
        # 404. The one real course found under this general topic (a
        # Saint Petersburg State University "Criminology" course) is no
        # longer offered on Coursera at all - Coursera suspended
        # cooperation with Russian universities in March 2022 - and
        # nothing else found genuinely matches "quantitative/qualitative
        # research methods specific to criminology, crime statistics
        # analysis." None is more honest than a mismatched or dead link.
        None,
    ),

    # -- Food Science and Nutrition (v7, 2026-09-03) - CFND also has
    # official 2025 TNA data, same reasoning as CCJE above.
    (
        "Food Safety, Quality Assurance, and HACCP Principles",
        "Covers food safety regulations, Hazard Analysis and Critical "
        "Control Points (HACCP) system implementation, and quality "
        "assurance practices for food production and service "
        "instruction, relevant to food technology and dietetics "
        "faculty.",
        "Food Science and Nutrition",
        "Workshop",
        None,
        "https://alison.com/course/hazard-analysis-critical-control-points-haccp",
    ),
    (
        "Community Nutrition and Dietary Counseling Practice",
        "Covers community-based nutrition assessment, dietary "
        "counseling techniques, and nutrition education program design "
        "for dietetics and nutrition faculty involved in community "
        "outreach and extension work.",
        "Food Science and Nutrition",
        "Seminar",
        None,
        # v11 (2026-09-06) - the old link was a consumer personal-diet
        # specialization, not professional community-assessment/
        # counseling content. Replaced with a course that explicitly
        # covers nutritional assessment, interpreting dietary
        # assessments, and patient counseling - framed for fitness
        # professionals rather than community/public-health dietetics
        # specifically, but the actual skill content (assessment +
        # counseling technique) is a real match.
        "https://www.coursera.org/learn/nutrition-and-weight-management-for-fitness-professionals",
    ),

    # -- Gender & Development (v9, 2026-09-03) - found via
    # scripts/audit_catalog_coverage.py, run proactively (not after a
    # live failure this time) once the official 2025 TNA data was
    # restored. "Gender & Development" has been a trained XGBoost
    # category (see app/ml/features.py CATEGORIES) since the 2026-08-29
    # catalog broadening, but no catalog program was ever added under it
    # - a genuine content gap, not a ranking issue. CCJE's official TNA
    # title "Gender awareness" scored 0.22 against the whole catalog
    # (noise-floor territory) before this was added. GAD (Gender and
    # Development) is also a legally mandated program area for Philippine
    # SUCs under RA 9710 (Magna Carta of Women), so this is a genuinely
    # expected, recurring topic across colleges, not a one-off.
    (
        "Gender and Development (GAD) Mainstreaming and Workplace Orientation",
        "Covers the legal basis for GAD in Philippine government agencies "
        "(RA 9710), gender-fair language and policy review, recognizing "
        "and addressing gender-based workplace discrimination, and "
        "practical steps for mainstreaming GAD considerations into "
        "department programs, budgets, and student services.",
        "Gender & Development",
        "Seminar",
        None,
        "https://www.coursera.org/learn/gender-equality",
    ),

    # -- Law, cont'd (v10, 2026-09-06) - see changelog note above.
    (
        "Human Rights Law and International Humanitarian Law",
        "Covers international human rights instruments and enforcement "
        "mechanisms, the laws governing armed conflict and protection of "
        "vulnerable persons under international humanitarian law, and "
        "their application to Philippine legal practice and human rights "
        "advocacy - for law faculty teaching public international law, "
        "human rights law, or related bar subjects.",
        "Law",
        "Seminar",
        None,
        "https://www.coursera.org/learn/international-humanitarian-law",
    ),

    # -- v12 (2026-09-07), the night before TAM testing begins - found via
    # scripts/audit_catalog_coverage.py, run once more now that real 2024
    # and 2027 TNA data exists for CCS/CHMT/COF (see seed_tna_2024.py/
    # seed_tna_2027.py) on top of 2025's. 5 real, generalizable, clearly-
    # fixable gaps addressed; several other flagged items (e.g. "2024 MSP
    # Calabarzon", "MPA Paskuhan...", "Diskartepreneur and Unlad Tulay ng
    # Barangay") were deliberately left alone - those name one-off named
    # events/programs, not generalizable training topics, same reasoning
    # already applied to "2024 MSP Calabarzon" back in v10's audit.
    (
        "Computer Networking and Systems Administration",
        "Covers network components, OSI/TCP-IP models, IP addressing and "
        "subnetting, Cisco switch and router configuration, and network "
        "management and security fundamentals - for CCS faculty teaching "
        "networking coursework or preparing students for entry-level "
        "networking certification.",
        "Technology",
        "Workshop",
        "CCS",
        "https://www.coursera.org/learn/basics-of-cisco-networking",
    ),
    (
        "Data Structures, Algorithms, and Programming Fundamentals",
        "Covers core data structures (arrays, linked lists, hash tables), "
        "sorting and searching algorithms, time/space complexity analysis, "
        "and hands-on implementation in Python - for CCS faculty teaching "
        "programming fundamentals or algorithm-analysis coursework.",
        "Technology",
        "Workshop",
        "CCS",
        "https://www.coursera.org/learn/packt-foundations-of-data-structures-algorithms-in-python-0odnl",
    ),
    (
        "English Language Proficiency and TESOL/TEFL Instruction",
        "Covers the theory and practical strategies of teaching English "
        "to speakers of other languages, lesson design, classroom "
        "management, and language-assessment design - for faculty "
        "teaching English language courses or preparing students for "
        "English-proficiency certification (IELTS/TOEFL-adjacent skills).",
        "Communication",
        "Seminar",
        None,
        "https://www.coursera.org/specializations/tesol",
    ),
    (
        "Disaster and Earthquake Preparedness",
        "Covers the disaster cycle (mitigation, preparedness, response, "
        "recovery), personal and institutional preparedness planning, "
        "and psychological first aid for supporting others during a "
        "disaster - a recurring request across multiple colleges and "
        "years (COF, ADMIN) in LSPU's own TNA data, not previously "
        "covered by anything in the catalog.",
        "Administration",
        "Seminar",
        None,
        "https://www.coursera.org/learn/disaster-preparedness",
    ),
    (
        "Basic Occupational Safety and Health (BOSH) Training for Safety Officers",
        "The 40-hour Basic Occupational Safety and Health training "
        "required under RA 11058 and DOLE Department Order 198 s. 2018 "
        "to become an accredited company Safety Officer - distinct from "
        "the existing 'Occupational Safety and Health in Technical "
        "Trades' program, which covers general shop/lab safety awareness "
        "rather than the formal Safety Officer accreditation pathway "
        "itself.",
        "Administration",
        "Seminar",
        None,
        "https://academy-ph.tuv.com/product/40-hour-basic-occupational-safety-health-bosh-training-course-10207",
    ),

    # -- v12, cont'd - PRIME-HRM and Civil Service Commission HR systems
    # compliance was ALSO flagged by this same audit pass (ADMIN's TNA
    # data), but no genuinely verifiable link was found: the Civil
    # Service Commission's own official page (csc.gov.ph/programs/
    # prime-hrm) returned HTTP 403 to an automated fetch - likely just
    # that .gov.ph site's own bot-defense, not proof the page is dead,
    # but this file's own standard (verified via a direct fetch that
    # actually loads, not just a search result) couldn't be met for it
    # tonight. Left undone rather than guessed - a real remaining gap,
    # documented rather than papered over the night before TAM testing.
]


def main():
    execute(CREATE_TABLE_SQL)

    # Self-heal: add reference_link to a training_programs table created
    # before v3, without wiping existing rows before the TRUNCATE below.
    existing_columns = {
        row["Field"] for row in fetch_all("SHOW COLUMNS FROM training_programs")
    }
    if "reference_link" not in existing_columns:
        execute("ALTER TABLE training_programs ADD COLUMN reference_link VARCHAR(500) DEFAULT NULL")
        print("Added reference_link column to training_programs.")

    existing = fetch_all("SELECT COUNT(*) as c FROM training_programs")[0]["c"]
    if existing > 0:
        print(f"training_programs currently has {existing} rows — clearing before reseed.")
        execute("TRUNCATE TABLE training_programs")

    for title, description, category, training_type, department, reference_link in PROGRAMS:
        execute(
            "INSERT INTO training_programs "
            "(title, description, category, training_type, target_department, reference_link) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (title, description, category, training_type, department, reference_link),
        )
    print(f"Seeded {len(PROGRAMS)} training programs across "
          f"{len(set(p[2] for p in PROGRAMS))} categories.")


if __name__ == "__main__":
    main()
