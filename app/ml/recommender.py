"""
Combines the structured (XGBoost) and text-similarity (SBERT) signals
into one ranked recommendation list. This is Phase 4 in CLAUDE.md — keep
it dumb and simple until Phases 2 and 3 actually produce real scores.
"""
from __future__ import annotations

from app.ml.xgboost_model import XGBoostRecommender
from app.ml.text_similarity import TextSimilarityMatcher
from app.ml.tna_matcher import Tna2025Matcher

# Weighting between the signals — tune once all are producing real
# (non-placeholder) scores. Sum doesn't need to be 1.0, it's just a
# starting point.
#
# 2026-09-03 (DURING live TAM testing) - rebalanced from an even 0.5/0.5
# split after a real respondent's result exposed a genuine problem: a
# CCS faculty member typed "I want to improve my Communication skills"
# and got recommendations for OBE Curriculum Design / Inclusive
# Classroom Strategies / Test Construction instead - checked directly
# via /similarity_check, and "Public Speaking and Presentation Skills"
# (0.33) and "Effective Business Communication and Report Writing"
# (0.29) were both genuinely strong text matches to what he actually
# typed, yet neither made the top 5. XGBoost's structured_score - a
# generic, role-based prior trained on synthetic (not real) bootstrap
# labels, see CLAUDE.md - was confidently pushing Pedagogy/Research
# categories regardless of what he'd specifically asked for, and (for
# CCS specifically) the self-reported-TNA fallback was compounding it by
# boosting whatever earlier CCS test respondents had asked about instead
# of his own input. The structured signal is still a reasonable
# fallback when text has nothing to go on (see the Fisheries case
# documented in seed_training_programs.py's v7 note, where text_score
# is near-zero for everything and structured is the only real signal
# left) - so this doesn't remove it, just stops it from routinely
# outvoting a clear, specific match to what the person actually said.
# A more principled, data-driven retune is still Phase 6 (see CLAUDE.md)
# - this is a same-day mitigation, verified against both failure cases
# below before shipping, not a final calibration.
STRUCTURED_WEIGHT = 0.4
TEXT_WEIGHT = 0.6
# Additive boost toward programs matching something the user's college
# officially requested in the 2025 Training Needs Assessment (see
# app/ml/tna_matcher.py). Not renormalized against the other two weights -
# a college with no reference data at all always gets a 0.0 boost, so its
# score is simply STRUCTURED+TEXT, identical to before this feature
# existed. Never a penalty, only ever an upside.
TNA_WEIGHT = 0.2
# Only 4 of 13 colleges submitted anything to the official 2025 list. For
# every other college, Tna2025Matcher falls back to what that college's
# own employees have already said they want via their own assessment
# submissions (assessments.desired_skills) - real data, just not
# reviewed/aggregated by college leadership the way an official TNA
# submission has been. Weighted lower than TNA_WEIGHT to reflect that
# lower level of institutional validation, not because it's less real.
SELF_REPORTED_WEIGHT = 0.12

# 2026-09-03, continued — the 0.4/0.6 rebalance above was NOT enough on
# its own. Re-tested live against the exact same CCS/"Communication"
# case after shipping it: results were still wrong (OBE Curriculum
# Design 0.50, Inclusive Classroom Strategies 0.48, ... Public Speaking
# and Business Communication still outside the top 5). Diagnosed with a
# direct component breakdown (scripts/debug_klyde.py) instead of
# guessing further:
#   structured_score  Pedagogy 0.742  Assessment 0.646  Technology 0.638
#                      Communication 0.250
#   text_score         Public Speaking 0.332  Business Comm 0.287
#                      OBE 0.191  Inclusive 0.235  Data Analytics 0.196
# The structured gap between Pedagogy and Communication (0.49 raw) times
# STRUCTURED_WEIGHT (0.4) outweighs the text gap between Public Speaking
# and OBE (0.14 raw) times TEXT_WEIGHT (0.6) — 0.20 vs 0.08 — even before
# the self-reported TNA boost (also highest for Pedagogy, since it
# reflects OTHER CCS respondents' past requests) adds more on the same
# side. Closing that with a single global weight would require something
# like TEXT_WEIGHT >= 3.5x STRUCTURED_WEIGHT, which would neuter the
# structured/role-based prior everywhere, including cases that genuinely
# need it as a fallback (a vague query, or the pre-catalog-fix Fisheries
# case where text_score was near-zero for everything — see
# seed_training_programs.py's v7 note).
#
# Fix: make the split CONDITIONAL on how specific the user's own request
# actually was, using the single best text match found anywhere in the
# catalog for this query as the signal. A clear, well-matched request
# should mostly override the generic role-based prior; a vague one
# should still fall back to it — which is exactly how a human advisor
# would reason about the same two cases ("you told me exactly what you
# want and it's a strong match, I'll go with that; you didn't give me
# much to go on, I'll go with what's typical for your role").
#
# TOP_TEXT_CONFIDENT_THRESHOLD=0.30 sits between the observed noise floor
# for genuinely-unrelated pairs (0.10-0.25 across every case checked this
# session) and Klyde's genuine match (0.332) — same small-sample-
# calibration caveat as every other threshold in this file (n=2 real
# cases: Klyde, and Dexter's post-fix 0.4327 top match, which also
# correctly lands in confident mode without changing his already-correct
# #1 result). STRUCTURED_WEIGHT_CONFIDENT/TEXT_WEIGHT_CONFIDENT sum to
# 1.0, same as the normal pair, so this only changes the RATIO, not the
# ceiling. The TNA/self-reported boost is scaled down too in confident
# mode, not just structured — it's the same kind of generic, other-
# people's-signal the structured score is, and was independently
# confirmed to be part of what was drowning out Klyde's specific request
# (Inclusive Classroom's self-reported boost, 0.542, was the single
# highest of any candidate checked). Verified against both real cases
# before shipping (see CLAUDE.md) — same same-day-mitigation caveat as
# above, not a final calibration, Phase 6 still owns the real fix.
#
# 2026-09-09 - lowered from 0.30 to 0.28 after the DESIRED_TEXT_WEIGHT/
# SPECIALIZATION_WEIGHT/HISTORY_WEIGHT split (see that comment below) was
# added. That change fixed a real CAS Biology case but, checked directly
# against Klyde's own real case again (not assumed still fine), his
# combined text score moved from 0.332 (the old single concatenated
# embedding) to 0.293 (weighted-separate scoring: "Communication skills"
# alone against the catalog, without "Computer Science" merged into the
# same embedding, naturally scores a little lower on its own) - just
# under the old 0.30 line, which silently dropped his case back into
# normal mode and let a Computer Networking program (Technology, his own
# specialization, boosted further by CCS's real official TNA data) outrank
# his actual, correct top text match again. The RAW ranking was never
# wrong here - Public Speaking and Presentation Skills was still text-
# score #1 in every check - only the confident-mode gate misfired.
# Re-verified with this new value against all three real cases this file
# already tracks: Klyde's Public Speaking match (0.293) now clears it,
# Bryant's Biology match (0.323) and Dexter's Aquaculture match (0.361)
# were already well clear either way. Still a small-sample calibration,
# same caveat as every other threshold here.
TOP_TEXT_CONFIDENT_THRESHOLD = 0.28
STRUCTURED_WEIGHT_CONFIDENT = 0.08
TEXT_WEIGHT_CONFIDENT = 0.92
TNA_WEIGHT_CONFIDENT = 0.04
SELF_REPORTED_WEIGHT_CONFIDENT = 0.02

# Below this cosine similarity, don't claim a TNA-2025 connection in the
# explanation even though the (small) score boost still silently applies.
#
# NOT the same value as ml_recommendations.php's
# TOPICAL_SIMILARITY_EXCLUSION_THRESHOLD (0.42) - that threshold compares
# two items from the SAME small, homogeneous training_programs catalog.
# This one compares training_programs descriptions against the much more
# heterogeneous, independently-worded TNA-2025 title list, and reusing
# 0.42 here produced a real false positive during manual verification
# (2026-08-27): "Test Construction and Item Analysis" (an educational
# testing-methodology program) matched CCJE's "Specialization training in
# questioned document examination/polygraphy" (forensic document
# authentication) at 0.461 - a spurious lexical-overlap artifact
# ("examination"/"specialization"/"analysis"), not a real topical
# connection. Raised to 0.47 to exclude that case while keeping the two
# clearly genuine matches found in the same test ("Curriculum
# development" -> OBE Curriculum Design, 0.482; "Research and
# statistics" -> Research Methods and Statistical Analysis, 0.473).
# This is a small-sample manual calibration (n=4), not a validated
# threshold - worth revisiting with a larger labeled set before relying
# on it heavily.
TNA_EXPLANATION_THRESHOLD = 0.47

# Below this RAW text-similarity score, don't claim a "closely matches
# what you described" connection in the explanation, even if the text
# signal happens to edge out the structured signal (see _explain below -
# that weaker case still gets an explanation, just a less specific one).
#
# 2026-09-03 - added because TAM pre-test walkthroughs showed genuinely
# strong, near-paraphrase matches (a Registrar's Office employee asking
# for "records management and document handling" matching "Records
# Management and Documentation Standards") were only ever explained as
# "Common for your role/department" - accurate but undersells a match
# that direct, on a construct (Actual Usage #4) that specifically asks
# whether recommendations "reflect the information I provided in my
# assessment." Calibrated against real /similarity_check numbers from
# that same walkthrough, not guessed:
#   genuine strong matches:  0.555 (rubric design -> Student Assessment
#     and Evaluation Techniques), 0.510 (outcomes-based teaching ->
#     OBE Curriculum Design), 0.394 (records management -> Records
#     Management and Documentation Standards - didn't clear this bar,
#     see below)
#   generic/filler matches:  0.438 (records management ask -> Effective
#     Business Communication, unrelated), 0.431 (rubric design ask ->
#     Data Analytics and Dashboards, unrelated), 0.307 (records
#     management ask -> Cybersecurity Awareness, unrelated)
# The genuine and filler clusters overlap in the 0.39-0.44 range with
# only 6 data points, so 0.50 is set deliberately high enough to clear
# every filler score measured, at the cost of not upgrading the 0.394
# Records Management case (it keeps its existing, still-accurate,
# non-embarrassing explanation instead). Additive/no-regression by
# design: this only ever upgrades an explanation, never downgrades one -
# revisit with a larger sample before lowering it.
TEXT_MATCH_STRONG_THRESHOLD = 0.50

# 2026-09-03 - the honesty fix that came out of the Dexter/COF incident.
# Before this, the final fallback branch below ("Common for your role/
# department") fired identically whether structured_score was ACTUALLY
# a reasonable call (text_score moderate, structured just happened to be
# a bit higher) or the catalog genuinely had NOTHING relevant to what the
# person asked and structured was the only thing carrying the result at
# all - Dexter's original bad recommendations ("Inclusive Classroom
# Strategies" etc. for a Fisheries-specific request) got exactly this
# same confident-sounding wording, which is what made his group ask "is
# there an error?" - the system LOOKED sure of itself while being wrong.
# That specific content gap is fixed now (see seed_training_programs.py
# v7), but the catalog can never be proven complete - the honest fix is
# to say so when it happens again instead of presenting a best-guess with
# the same confidence as a real match.
#
# NO_GENUINE_MATCH_THRESHOLD=0.20 is calibrated against this session's
# real measurements: Dexter's pre-fix best-match-anywhere scored 0.0495
# (clear noise), and every genuinely-unrelated pair checked this session
# landed in the 0.10-0.25 range. Set below TOP_TEXT_CONFIDENT_THRESHOLD
# (0.30, used for the weight-split decision above) deliberately - a score
# between 0.20 and 0.30 isn't strong enough to swing the weighting, but
# it's still enough real overlap that "Common for your role/department"
# remains an honest, non-misleading description of why this particular
# program was picked. Below 0.20, there's no meaningful textual basis for
# this program at all - only the structured/role prior put it here.
# Same small-sample-calibration caveat as every other threshold in this
# file - revisit with more real data.
#
# LOW_CONFIDENCE_REASON is a fixed, exact-matchable string (not just
# prose) on purpose - training_recommendations.php/user_page.php check
# for this exact text to render it with a distinct, honest visual
# treatment instead of the standard confident styling. Keep the PHP
# side in sync if this string ever changes.
#
# 2026-09-03, continued again - labeling a genuinely-irrelevant program
# honestly (the version above) turned out to be a half-measure, per
# direct user feedback: the ML system's whole premise is that
# desired_skills/training_history is the primary signal and the profile
# (role/department/years) is secondary context for it, not a co-equal
# source of recommendations - "no sense in recommending him that" a
# program has zero relation to what he actually typed, caveat or not.
# Fixed properly below: EXCLUDE a candidate entirely rather than show it
# with a warning label, whenever the person gave a real, specific
# description and this program doesn't genuinely relate to it by either
# available signal (their own text, or their college's real institutional
# demand). This means fewer than top_k recommendations can now come back
# - and that's the intended, honest result: a thin catalog for someone's
# actual need should look thin, not padded out to 5 with filler.
#
# The one deliberate exception is has_real_query in recommend() below - a
# genuinely blank submission (nothing typed anywhere) has no personal
# text to hold anything accountable to, so the structured/role-based
# fallback still fills all top_k slots exactly as before. That's the one
# remaining real use of LOW_CONFIDENCE_REASON - see recommend()'s
# has_real_query comment.
NO_GENUINE_MATCH_THRESHOLD = 0.20
LOW_CONFIDENCE_REASON = "No close match yet — shown as a general suggestion based on your role"

# 2026-09-09 - how the three pieces of a person's own text (as opposed to
# their role/department, which is the separate structured signal above)
# are weighted against EACH OTHER before they ever become "the" text
# score. Before this, app/routers/recommend.py concatenated
# desired_skills + comments + training_history + specialization into one
# string and embedded it as a single query - found live, via a real CAS
# Biology instructor's result, that this lets a secondary field's
# incidental wording redirect the whole match: his training_history entry
# happened to say "...and Data Analysis," which pulled the combined
# embedding toward IT/data-science catalog entries even though his actual
# desired_skills text ("Specialized Chemical & Microscopic Analysis") was
# specific and on-topic on its own. See TextSimilarityMatcher.
# rank_programs_multi() for the mechanism: each piece is now scored
# against the catalog separately and combined as a weighted sum, so a
# lower-weighted field can only ever nudge the result, never redirect it.
#
# DESIRED_TEXT_WEIGHT is highest because desired_skills (plus any
# comments) is the one field that is an explicit, current statement of
# what the person wants - the closest thing this system has to the person
# speaking for themselves right now. HISTORY_WEIGHT is lowest:
# training_history describes a PAST completed training, not a current
# need, and it's exactly this kind of free-text field (a full sentence
# with its own incidental vocabulary) that caused the CAS case - it still
# contributes, since a person's training history is real context, but it
# can no longer outweigh what they're actually asking for today.
# Same small-sample-calibration caveat as every other threshold in this
# file: checked against the CAS case this fixes plus every other real
# case already verified this session (Dexter/COF, Klyde/CCS) to confirm
# none of them regressed - not a large-scale validated tuning.
DESIRED_TEXT_WEIGHT = 0.85
HISTORY_WEIGHT = 0.15

# 2026-09-09, continued - fixing the concatenation bug (above) still
# wasn't enough on its own. Re-checked live: a CAS Biology instructor's
# own exact words, "Specialized Chemical & Microscopic Analysis," on
# their own, with nothing else concatenated in, STILL ranked "Emerging
# Technologies in Engineering Practice" and "Test Construction and Item
# Analysis" above the actual Chemistry program in the catalog. That's not
# a weighting problem - it's the SBERT model itself keying on the shared
# word "Analysis" rather than the topic, at the raw text_score level,
# before any of this file's weighting ever applies. No amount of
# reweighting text vs. structured vs. TNA can fix a similarity number
# that's already wrong.
#
# Fix: specialization (e.g. "Biology") was originally folded into the
# text channel above, compared against full program DESCRIPTIONS - long
# paragraphs full of the same generic academic vocabulary causing the
# problem. Moved instead to TextSimilarityMatcher.category_affinity(),
# which compares specialization against short, topically CLEAN category
# LABELS ("Natural Sciences", "Technology") instead. Checked directly:
# "Biology" scores 0.50 against "Natural Sciences" with a wide, clean
# margin to the next-closest category (0.41) and everything else below
# 0.30 - a far less noisy signal than description-level matching.
#
# CATEGORY_AFFINITY_WEIGHT is additive on top of the structured/text
# split, same convention as TNA_WEIGHT (not renormalized against it) -
# a category affinity score is available for anyone with a declared
# specialization, so treating it as pure upside rather than something
# that has to fight text/structured for a share of a fixed budget keeps
# it from accidentally shrinking either of those when it's absent.
# Swept 0.0-0.35 against all three real cases this file tracks
# (Bryant/CAS, Klyde/CCS, Dexter/COF) before picking these values: 0.15-
# 0.25 correctly pulled both Natural Sciences programs into Bryant's top
# 5 (his own text alone never did) while leaving Klyde's and Dexter's
# already-correct results alone; 0.30+ started pulling Klyde back toward
# his OWN specialization (Computer Science -> Networking) even though he
# explicitly asked for something outside it - the same failure shape
# specialization caused in the text channel before, just re-emerging at
# a higher weight in this cleaner channel instead. CONFIDENT is set
# lower than normal mode for the same reason TEXT_WEIGHT_CONFIDENT is
# high: when someone gave a specific, on-topic request, that request
# should still lead over a general subject-area affinity, not be
# outweighed by it.
CATEGORY_AFFINITY_WEIGHT = 0.22
CATEGORY_AFFINITY_WEIGHT_CONFIDENT = 0.18

# Below this, a category-affinity score doesn't count as a genuine
# subject-area connection - used both to decide whether it can rescue a
# candidate from the exclusion filter below and whether _explain() may
# credit it as the reason. Calibrated against the real category_affinity()
# numbers checked directly this session: genuine matches landed at 0.50
# ("Biology" -> "Natural Sciences"), 0.55 ("Computer Science" ->
# "Technology"), and 0.45 ("Aquaculture" -> "Agriculture"/"Fisheries"),
# while the closest a genuinely unrelated pair came was 0.35 ("Computer
# Science" -> "Natural Sciences"). Set at 0.40, above that unrelated-pair
# ceiling and below every genuine match found so far - same small-sample
# caveat as every other threshold in this file.
CATEGORY_AFFINITY_EXPLANATION_THRESHOLD = 0.40


class Recommender:
    def __init__(
        self,
        xgb: XGBoostRecommender,
        matcher: TextSimilarityMatcher,
        tna_matcher: Tna2025Matcher | None = None,
    ):
        self.xgb = xgb
        self.matcher = matcher
        self.tna_matcher = tna_matcher

    def recommend(
        self,
        user_features: dict,
        query_text: str,
        programs_by_id: dict[int, dict],
        top_k: int = 5,
        college_code: str | None = None,
        specialization_text: str = "",
        history_text: str = "",
    ) -> list[dict]:
        # query_text is the person's own current, explicit statement of
        # what they want (desired_skills + comments) - kept as the
        # required positional parameter, and still what every existing
        # caller/test passes, since it alone reproduces the old behavior
        # exactly when history_text is left blank (see
        # rank_programs_multi()'s weight-redistribution). history_text is
        # a separate, lower-weighted signal - see DESIRED_TEXT_WEIGHT's
        # comment above for why. specialization_text is NOT part of this
        # text channel (see CATEGORY_AFFINITY_WEIGHT's comment above for
        # why it moved to its own, cleaner comparison instead).
        text_ranked = dict(self.matcher.rank_programs_multi(
            [
                (query_text, DESIRED_TEXT_WEIGHT),
                (history_text, HISTORY_WEIGHT),
            ],
            top_k=len(programs_by_id),
        ))
        structured_scores = self.xgb.predict_category_scores(user_features)
        # {category_name: similarity} for this person's specialization
        # against each catalog category's label - {} (never raises) if
        # specialization_text is blank or the matcher wasn't given
        # categories to index. See CATEGORY_AFFINITY_WEIGHT's comment.
        category_affinity_scores = (
            self.matcher.category_affinity(specialization_text)
            if hasattr(self.matcher, "category_affinity") else {}
        )

        # See TOP_TEXT_CONFIDENT_THRESHOLD's comment above — a strong best
        # match anywhere in the catalog means the user gave a specific
        # enough request to mostly trust text over the generic structured/
        # TNA priors; a weak one means there's nothing specific to trust,
        # so those priors keep their normal, larger say.
        top_text_score = max(text_ranked.values()) if text_ranked else 0.0
        confident = top_text_score >= TOP_TEXT_CONFIDENT_THRESHOLD
        structured_weight = STRUCTURED_WEIGHT_CONFIDENT if confident else STRUCTURED_WEIGHT
        text_weight = TEXT_WEIGHT_CONFIDENT if confident else TEXT_WEIGHT
        tna_weight_official = TNA_WEIGHT_CONFIDENT if confident else TNA_WEIGHT
        self_reported_weight = SELF_REPORTED_WEIGHT_CONFIDENT if confident else SELF_REPORTED_WEIGHT
        category_weight = CATEGORY_AFFINITY_WEIGHT_CONFIDENT if confident else CATEGORY_AFFINITY_WEIGHT

        # See LOW_CONFIDENCE_REASON's comment above - a genuinely blank
        # submission (nothing typed anywhere) has nothing personal to hold
        # a program accountable to, so every candidate stays eligible and
        # the structured/role-based fallback fills top_k exactly as
        # before. A real, specific description instead makes relevance
        # mandatory, not optional - see the exclusion check in the loop
        # below.
        #
        # 2026-09-09 - broadened from "just query_text" to any of the
        # three text signals. Someone who left desired_skills blank but
        # has a specialization or training history on file still has
        # real, personal information the system can hold a candidate
        # accountable to - only a truly empty submission (nothing typed
        # anywhere at all) should fall back to the unfiltered, role-based
        # top_k fill.
        has_real_query = bool(
            (query_text and query_text.strip())
            or (specialization_text and specialization_text.strip())
            or (history_text and history_text.strip())
        )

        results = []
        for program_id, program in programs_by_id.items():
            text_score = text_ranked.get(program_id, 0.0)
            # Structured score is per-category (see app/ml/features.py
            # CATEGORIES), looked up by each program's category column.
            # IMPORTANT: a category absent from structured_scores (no
            # trained model for it - e.g. a category added to the catalog
            # after XGBoost was last trained, see the 2026-08-29 catalog
            # broadening) is NOT the same thing as a trained model scoring
            # it 0.0. Conflating the two was a real bug: it silently
            # halved every new category's ceiling score (STRUCTURED_WEIGHT
            # applied to a hard 0.0, as if the model had confidently said
            # "irrelevant"), so even a near-perfect text match on a brand
            # new program could never rank competitively against an old,
            # well-trained category. "No signal" should mean "rely on
            # text fully," not "confirmed irrelevant" - so an unrecognized
            # category gets STRUCTURED_WEIGHT's share reallocated to text
            # instead. Retraining XGBoost on the broadened catalog (so
            # these categories get a real, non-placeholder score) is a
            # Phase 6 concern - this keeps new categories fairly
            # competitive in the meantime rather than structurally buried.
            category = program.get("category", "")
            category_is_trained = category in structured_scores
            structured_score = structured_scores.get(category, 0.0)
            category_affinity_score = category_affinity_scores.get(category, 0.0)

            # 2026-09-08 fix - target_department exists on a handful of
            # programs specifically because they're only meaningful for one
            # college (e.g. "Data Structures, Algorithms, and Programming
            # Fundamentals" is CCS-only - its own description says so) and
            # were never meant to compete for a slot in every other
            # college's recommendations. The column was being read into
            # `program` but nothing ever checked it (found live: it
            # recommended that exact program to a CAS Biology instructor).
            # A hard exclusion, not a scoring penalty - unlike a topical
            # mismatch, which is a matter of degree, "not your college"
            # is binary. Only excludes when college_code is actually known
            # - never over-excludes on missing/uncanonicalizable data.
            target_dept = (program.get("target_department") or "").strip().upper()
            if target_dept and college_code and target_dept != college_code.strip().upper():
                continue

            tna_boost = 0.0
            tna_source = None
            if self.tna_matcher:
                tna_boost = self.tna_matcher.get_boost(college_code, program_id)
                tna_source = self.tna_matcher.get_source(college_code)

            # See has_real_query's comment above - a real, specific
            # description makes genuine relevance mandatory. Excluded
            # outright (not included-with-a-caveat) when neither this
            # person's own text, their college's real institutional
            # demand, NOR their declared specialization's subject area
            # actually connects to this program - "closest available" is
            # not the same as "relevant," and offering it anyway is
            # exactly the mistake this whole fix corrects. The
            # category-affinity clause was added 2026-09-09 alongside
            # CATEGORY_AFFINITY_WEIGHT, same threshold as the honesty
            # check in _explain() below.
            if (
                has_real_query
                and text_score < NO_GENUINE_MATCH_THRESHOLD
                and tna_boost < TNA_EXPLANATION_THRESHOLD
                and category_affinity_score < CATEGORY_AFFINITY_EXPLANATION_THRESHOLD
            ):
                continue

            tna_weight = self_reported_weight if tna_source == "self_reported" else tna_weight_official
            # effective_text_weight/effective_structured_weight mirror
            # whichever formula branch actually runs below (an untrained
            # category reallocates structured_weight's whole budget onto
            # text, per category_is_trained's comment above) - passed into
            # _explain() so its contribution comparisons are computed
            # against the SAME weights that actually produced this score,
            # not the raw pre-reallocation ones.
            if category_is_trained:
                effective_structured_weight = structured_weight
                effective_text_weight = text_weight
            else:
                effective_structured_weight = 0.0
                effective_text_weight = structured_weight + text_weight
            combined = (
                (effective_structured_weight * structured_score)
                + (effective_text_weight * text_score)
                + (tna_weight * tna_boost)
                + (category_weight * category_affinity_score)
            )
            results.append(
                {
                    "program_id": program_id,
                    "title": program["title"],
                    "description": program["description"],
                    "training_type": program.get("training_type"),
                    "score": round(combined, 4),
                    "reason": self._explain(
                        text_score, structured_score, tna_boost, tna_source,
                        effective_text_weight, effective_structured_weight, tna_weight,
                        category_affinity_score, category_weight,
                    ),
                    "reference_link": program.get("reference_link"),
                }
            )

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    @staticmethod
    def _explain(
        text_score: float,
        structured_score: float,
        tna_boost: float = 0.0,
        tna_source: str | None = None,
        text_weight: float = 0.0,
        structured_weight: float = 0.0,
        tna_weight: float = 0.0,
        category_affinity_score: float = 0.0,
        category_weight: float = 0.0,
    ) -> str:
        # 2026-09-09 - a real CAS instructor's result exposed a genuine
        # mismatch: his top recommendation was explained as "related to
        # what colleagues in your college have asked for," but that
        # signal was contributing about 2% of his actual score (see
        # SELF_REPORTED_WEIGHT_CONFIDENT) - the generic, role-based
        # structured prior contributed roughly four times as much,
        # unmentioned. The old check only asked "is the raw TNA
        # similarity above the line," never "did TNA actually drive this
        # result more than the alternative explanation would have." Fixed
        # by comparing WEIGHTED contributions throughout this function
        # instead of raw scores - a signal only gets named as the reason
        # when it actually was the reason, not just present. Every
        # "special" branch below now has to out-contribute EVERY other
        # signal, not just structured, for the same reason: crediting
        # category affinity while a stronger text match went unmentioned
        # would just be this exact bug again, one signal over.
        text_contribution = text_weight * text_score
        structured_contribution = structured_weight * structured_score
        tna_contribution = tna_weight * tna_boost
        category_contribution = category_weight * category_affinity_score

        if text_score >= TEXT_MATCH_STRONG_THRESHOLD:
            return "Closely matches what you described in your assessment"
        if (
            tna_boost >= TNA_EXPLANATION_THRESHOLD
            and tna_contribution >= structured_contribution
            and tna_contribution >= text_contribution
            and tna_contribution >= category_contribution
        ):
            # Deliberately worded as a similarity-based inference ("related
            # to") rather than an assertion of fact ("officially
            # requested") - this is a small-sample-calibrated SBERT
            # similarity match, not a verified lookup, and can still be
            # wrong on an untested pair. See TNA_EXPLANATION_THRESHOLD's
            # comment for a real false-positive case found in testing.
            if tna_source == "self_reported":
                return "Related to what colleagues in your college have asked for in their own assessments"
            # 2026-09-07 fix - this used to hardcode "2025" specifically,
            # which became actively false the moment 2024/2027 TNA data was
            # added: CCS, CHMT, and COF (the exact three colleges that data
            # was added FOR, since they submitted nothing in 2025) would
            # show "your college requested this in the 2025 TNA" for a
            # match that only exists in the 2024 or 2027 data. The
            # underlying table pools every year together per college
            # without tracking which specific year backs any one title, so
            # no single year can be named accurately here - dropped it
            # rather than guess or risk the wrong one.
            return "Related to a training your college has officially requested in a Training Needs Assessment"
        # 2026-09-09 - new branch, added alongside CATEGORY_AFFINITY_WEIGHT.
        # Only claims credit when category affinity is both a genuine
        # subject-area match (see CATEGORY_AFFINITY_EXPLANATION_THRESHOLD)
        # and actually the largest contributor - same discipline as the
        # TNA check just above.
        if (
            category_affinity_score >= CATEGORY_AFFINITY_EXPLANATION_THRESHOLD
            and category_contribution >= structured_contribution
            and category_contribution >= text_contribution
        ):
            return "Related to your declared specialization"
        if text_contribution >= structured_contribution:
            return "Matches the training you described"
        if text_score < NO_GENUINE_MATCH_THRESHOLD:
            return LOW_CONFIDENCE_REASON
        return "Common for your role/department"

