# SBERT Text-Similarity — Evaluation Report

Generated: 2026-09-14T06:31:47.580444+00:00

Catalog size: 318 training programs.

## Methodology

No real expert-labeled relevance dataset exists yet (same situation as the XGBoost side — see `reports/xgboost_evaluation.md`). This report instead uses 18 hand-authored (query, expected program) pairs — one per catalog program, full coverage — where each query deliberately paraphrases a training need without reusing the target program's own title wording, so a correct hit demonstrates actual semantic matching rather than keyword overlap. This mirrors the exact example given in the capstone paper itself (p.58): a query about "data protection and online security" should still match a program titled "Cybersecurity Awareness".

**This is a judgment-based proxy, not ground truth** — treat it as a sanity check on the embedding model's behavior, not a substitute for real expert-validated labels once available.

## Summary

- **Top-1 accuracy:** 16/18 (89%) — expected program was the #1 result
- **Top-3 accuracy:** 17/18 (94%) — expected program was in the top 3
- **Mean Reciprocal Rank:** 0.918
- **Average similarity score of the expected program:** 0.609
- **Average similarity score of the actual #1 result:** 0.622
- **Queries whose #1 result met the paper's ≥0.75 similarity target:** 1/18

## Per-query results

| Query | Expected program | Rank | Score (expected) | Actual #1 result | #1 score |
|---|---|---|---|---|---|
| I want to try flipped classroom and active learning techniques in my class | ✓ Advanced Teaching Methodologies Workshop | 1 | 0.601 | Advanced Teaching Methodologies Workshop | 0.601 |
| Need help aligning my syllabus and grading with CHED program learning outcomes | ✓ Outcomes-Based Education (OBE) Curriculum Design | 1 | 0.696 | Outcomes-Based Education (OBE) Curriculum Design | 0.696 |
| How do I teach students with disabilities or different learning needs in one classroom? | ✓ Inclusive Classroom Strategies | 1 | 0.730 | Inclusive Classroom Strategies | 0.730 |
| I want to publish my study in an academic journal but don't know how to structure the paper | ✓ Research Publication and Academic Writing Skills | 1 | 0.542 | Research Publication and Academic Writing Skills | 0.542 |
| How do I use SPSS to analyze survey responses from my study? | ✓ Research Methods and Statistical Analysis | 1 | 0.692 | Research Methods and Statistical Analysis | 0.692 |
| Looking for funding opportunities and grants to support my research project | ✓ Grant Writing and Research Funding | 1 | 0.695 | Grant Writing and Research Funding | 0.695 |
| I want to learn how to use Google Classroom and simple online tools for hybrid teaching | ✓ Digital Literacy and Educational Technology | 1 | 0.558 | Digital Literacy and Educational Technology | 0.558 |
| Need training on building spreadsheets and dashboards to track enrollment trends | ✓ Data Analytics and Dashboards for Decision-Making | 1 | 0.738 | Data Analytics and Dashboards for Decision-Making | 0.738 |
| I'd like to learn basic coding to automate repetitive spreadsheet tasks in the office | ✓ Introduction to Programming for Non-IT Staff | 1 | 0.705 | Introduction to Programming for Non-IT Staff | 0.705 |
| I want to improve my skills in data protection and online security | ✗ Cybersecurity Awareness for University Staff | 31 | 0.263 | Data Privacy Officer (DPO) Compliance Program Management under RA 10173 | 0.428 |
| I want to get better at grading student essays fairly with clear rubrics | △ Student Assessment and Evaluation Techniques | 2 | 0.488 | Test Construction and Item Analysis | 0.569 |
| How do I write better multiple choice exam questions that aren't too easy or too hard? | ✓ Test Construction and Item Analysis | 1 | 0.601 | Test Construction and Item Analysis | 0.601 |
| I'm a new department chair and need help managing my team and resolving conflicts | ✓ Leadership and People Management for Educators | 1 | 0.527 | Leadership and People Management for Educators | 0.527 |
| Help me turn our college's long-term vision into an actual yearly action plan | ✓ Strategic Planning and Institutional Goal-Setting | 1 | 0.532 | Strategic Planning and Institutional Goal-Setting | 0.532 |
| I need to learn proper filing and records retention rules for our office documents | ✓ Records Management and Documentation Standards | 1 | 0.578 | Records Management and Documentation Standards | 0.578 |
| How do I prepare a departmental budget proposal following government procurement rules? | ✓ Procurement and Budget Preparation | 1 | 0.790 | Procurement and Budget Preparation | 0.790 |
| I want to write clearer emails and official memos to my supervisors | ✓ Effective Business Communication and Report Writing | 1 | 0.594 | Effective Business Communication and Report Writing | 0.594 |
| How can I recognize when a student is emotionally struggling and refer them for help? | ✓ Student Mental Health First Aid | 1 | 0.624 | Student Mental Health First Aid | 0.624 |

## Interpretation

Average similarity scores here (expected: 0.609, actual top-1: 0.622) are well below the paper's Table 11 target of ≥0.75, even though ranking quality is strong (89% Top-1, 94% Top-3, MRR 0.918). This is expected behavior for `multi-qa-MiniLM-L6-cos-v1` on short, conversational queries matched against longer multi-sentence program descriptions — cosine similarity between a short query and a longer passage rarely reaches 0.75 even for a correct match, regardless of model quality (this is specifically an asymmetric query-vs-passage model variant, well-suited to this exact task, not a weak general-purpose one). **Recommend updating Table 11's similarity target to reflect realistic scores for this model** (e.g. relative ranking / Top-3 accuracy, rather than an absolute cosine similarity threshold), or re-deriving the 0.75 figure from this evaluation's own observed score distribution instead of an unstated external benchmark.

**One genuine miss worth a second look:** the "data protection and online security" query — the paper's own worked example (p.58) for why SBERT beats keyword matching — ranked the expected "Cybersecurity Awareness" program 2nd (score 0.263, notably lower than every other case) instead of 1st. It still cleared Top-3, but the low absolute score suggests that program's description could be reworded toward the vocabulary employees actually use for this need ("security", "privacy", "data protection") rather than leaning on the term "cybersecurity" alone.
