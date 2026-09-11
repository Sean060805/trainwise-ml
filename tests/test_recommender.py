"""
Unit tests for Recommender (app/ml/recommender.py) - the logic that
combines the XGBoost structured score and SBERT text score into one
ranked list. Uses fake stand-ins for the XGBoost/SBERT components so
these run instantly with no model loading or database access.
"""
from app.ml.recommender import Recommender


class FakeXGB:
    """Stands in for XGBoostRecommender - returns a fixed score per category."""

    def __init__(self, scores: dict):
        self._scores = scores

    def predict_category_scores(self, user_features):
        return self._scores


class FakeMatcher:
    """Stands in for TextSimilarityMatcher - returns a fixed score per program id."""

    def __init__(self, scores: dict, category_scores: dict | None = None):
        self._scores = scores
        # {category_name: affinity_score} - optional. Left as None (-> an
        # empty dict from category_affinity() below, same as "no
        # specialization on file") for the vast majority of existing tests,
        # which keeps them passing exactly as before this feature existed -
        # only tests that need to exercise it pass category_scores explicitly.
        self._category_scores = category_scores

    def rank_programs(self, query_text, top_k):
        return list(self._scores.items())

    def rank_programs_multi(self, weighted_texts, top_k):
        # Fixed canned scores regardless of input, same as rank_programs()
        # above - existing tests only ever populate query_text (the other
        # signal defaults to "" and gets redistributed onto it), so this
        # keeps them passing unchanged.
        return list(self._scores.items())

    def category_affinity(self, specialization_text):
        return self._category_scores if self._category_scores is not None else {}


class FakeTnaMatcher:
    """Stands in for Tna2025Matcher - returns a fixed boost per (college, program_id),
    and a fixed source ("official"/"self_reported") per college."""

    def __init__(self, boosts: dict, sources: dict | None = None):
        self._boosts = boosts  # {(college_code, program_id): score}
        self._sources = sources or {}  # {college_code: "official" | "self_reported"}

    def get_boost(self, college_code, program_id):
        return self._boosts.get((college_code, program_id), 0.0)

    def get_source(self, college_code):
        return self._sources.get(college_code)


def make_programs(*, categories):
    """categories: {program_id: category_name}"""
    return {
        pid: {
            "title": f"Program {pid}",
            "description": f"Description for program {pid}",
            "training_type": "Workshop",
            "category": category,
        }
        for pid, category in categories.items()
    }


def test_combines_structured_and_text_scores():
    # 2026-09-03 - top text score here (0.4) clears
    # TOP_TEXT_CONFIDENT_THRESHOLD (0.30), so this now exercises the
    # confident-mode weights (0.08/0.92), not the normal 0.4/0.6 pair -
    # see test_normal_mode_weights_apply_when_no_strong_text_match below
    # for a case that stays in normal mode.
    programs = make_programs(categories={1: "Technology"})
    xgb = FakeXGB({"Technology": 0.8})
    matcher = FakeMatcher({1: 0.4})

    recommender = Recommender(xgb, matcher)
    results = recommender.recommend(user_features={}, query_text="anything", programs_by_id=programs)

    # STRUCTURED_WEIGHT_CONFIDENT=0.08, TEXT_WEIGHT_CONFIDENT=0.92 ->
    # (0.08*0.8) + (0.92*0.4) = 0.432
    assert results[0]["score"] == 0.432


def test_sorts_by_combined_score_descending():
    # program 1's text_score (0.25) is deliberately kept above
    # NO_GENUINE_MATCH_THRESHOLD (0.20) so all 3 programs stay eligible -
    # this test is about sort order across 3 results, not exclusion (see
    # the dedicated exclusion tests below).
    programs = make_programs(categories={1: "Technology", 2: "Research", 3: "Pedagogy"})
    xgb = FakeXGB({"Technology": 0.1, "Research": 0.9, "Pedagogy": 0.5})
    matcher = FakeMatcher({1: 0.25, 2: 0.9, 3: 0.5})

    recommender = Recommender(xgb, matcher)
    results = recommender.recommend(user_features={}, query_text="x", programs_by_id=programs)

    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    assert results[0]["program_id"] == 2  # highest on both signals


def test_respects_top_k():
    programs = make_programs(categories={i: "Technology" for i in range(1, 11)})
    xgb = FakeXGB({"Technology": 0.5})
    matcher = FakeMatcher({i: 0.5 for i in range(1, 11)})

    recommender = Recommender(xgb, matcher)
    results = recommender.recommend(user_features={}, query_text="x", programs_by_id=programs, top_k=3)

    assert len(results) == 3


def test_missing_category_score_gives_full_weight_to_text():
    # Program's category isn't in the XGBoost output at all (e.g. model
    # skipped it due to an unseen categorical value, no model trained yet,
    # or - the real case found 2026-08-29 - a category added to the
    # catalog after XGBoost was last trained). This must NOT be treated
    # the same as a trained model confidently scoring it 0.0 - "no
    # signal" reallocates STRUCTURED_WEIGHT's share to text instead of
    # silently halving the ceiling score for every untrained category.
    programs = make_programs(categories={1: "Student Affairs"})
    xgb = FakeXGB({})  # no categories scored
    matcher = FakeMatcher({1: 0.8})

    recommender = Recommender(xgb, matcher)
    results = recommender.recommend(user_features={}, query_text="x", programs_by_id=programs)

    # Full (STRUCTURED_WEIGHT + TEXT_WEIGHT) weight applies to text: 1.0*0.8 = 0.8
    assert results[0]["score"] == 0.8


def test_trained_category_scored_zero_still_uses_normal_formula():
    # Contrast case: the category IS in the XGBoost output, and the
    # trained model genuinely scored it 0.0 - this is a real, confident
    # "not relevant" signal, so the (weighted, not full-weight) formula
    # still applies (distinguishes this from the "untrained category"
    # case above, which gets full weight on text instead).
    # top text score (0.8) clears the confident threshold here too.
    programs = make_programs(categories={1: "Technology"})
    xgb = FakeXGB({"Technology": 0.0})
    matcher = FakeMatcher({1: 0.8})

    recommender = Recommender(xgb, matcher)
    results = recommender.recommend(user_features={}, query_text="x", programs_by_id=programs)

    # 0.08*0.0 + 0.92*0.8 = 0.736, NOT the 0.8 an untrained category would
    # get (that path applies (structured_weight+text_weight), i.e. full
    # 1.0, to text - still distinct from this trained-but-zero case).
    assert results[0]["score"] == 0.736


def test_reason_text_when_text_signal_dominates():
    # text_score (0.3) beats structured_score (0.1) but stays below
    # TEXT_MATCH_STRONG_THRESHOLD (0.5) - the weaker, still-accurate
    # "dominates but isn't a strong absolute match" case. See the test
    # below for the strong-absolute-match case.
    programs = make_programs(categories={1: "Technology"})
    xgb = FakeXGB({"Technology": 0.1})
    matcher = FakeMatcher({1: 0.3})

    recommender = Recommender(xgb, matcher)
    results = recommender.recommend(user_features={}, query_text="x", programs_by_id=programs)

    assert results[0]["reason"] == "Matches the training you described"


def test_reason_text_strongly_matches_gets_upgraded_explanation():
    # 2026-09-03 - text_score clears TEXT_MATCH_STRONG_THRESHOLD (0.5),
    # so this should get the more specific/confident explanation instead
    # of the generic "dominates" phrasing above.
    programs = make_programs(categories={1: "Technology"})
    xgb = FakeXGB({"Technology": 0.1})
    matcher = FakeMatcher({1: 0.9})

    recommender = Recommender(xgb, matcher)
    results = recommender.recommend(user_features={}, query_text="x", programs_by_id=programs)

    assert results[0]["reason"] == "Closely matches what you described in your assessment"


def test_reason_text_when_structured_signal_dominates():
    # text_score (0.25) is moderate - structured just happens to be
    # higher - a legitimate, non-misleading "common for your role" case,
    # NOT the low-confidence case below (that needs text_score under
    # NO_GENUINE_MATCH_THRESHOLD, 0.20).
    programs = make_programs(categories={1: "Technology"})
    xgb = FakeXGB({"Technology": 0.9})
    matcher = FakeMatcher({1: 0.25})

    recommender = Recommender(xgb, matcher)
    results = recommender.recommend(user_features={}, query_text="x", programs_by_id=programs)

    assert results[0]["reason"] == "Common for your role/department"


def test_irrelevant_candidate_is_excluded_when_a_real_query_was_given():
    # 2026-09-03, superseding an earlier "label it honestly" version of
    # this test - per direct user feedback after seeing the labeled
    # version live on Dexter's real account: a program with zero genuine
    # relation to what someone specifically described shouldn't be
    # offered at all, caveat or not. "Common for your role/department"
    # was originally going to apply here (structured 0.9 > text 0.05),
    # but has_real_query now excludes it outright before _explain() is
    # ever reached. Modeled on Dexter's real pre-fix numbers (his actual
    # best match anywhere scored 0.0495; Inclusive Classroom Strategies
    # specifically scored 0.0924 against his real query).
    programs = make_programs(categories={1: "Technology", 2: "Communication"})
    xgb = FakeXGB({"Technology": 0.9, "Communication": 0.1})
    matcher = FakeMatcher({1: 0.05, 2: 0.6})  # program 1: irrelevant; program 2: the real match

    recommender = Recommender(xgb, matcher)
    results = recommender.recommend(user_features={}, query_text="x", programs_by_id=programs)

    result_ids = [r["program_id"] for r in results]
    assert 1 not in result_ids
    assert 2 in result_ids


def test_fewer_than_top_k_returned_when_catalog_is_thin_for_a_real_request():
    # Direct consequence of the exclusion above: if only 2 of 5 catalog
    # programs genuinely relate to what was described, the response
    # should honestly come back with 2, not be padded to 5. This is the
    # exact shape of Dexter's real pre-v7-catalog gap, generalized.
    programs = make_programs(categories={i: "Technology" for i in range(1, 6)})
    xgb = FakeXGB({"Technology": 0.9})
    # only programs 1 and 2 have any genuine textual relevance
    matcher = FakeMatcher({1: 0.5, 2: 0.4, 3: 0.05, 4: 0.02, 5: 0.0})

    recommender = Recommender(xgb, matcher)
    results = recommender.recommend(user_features={}, query_text="x", programs_by_id=programs, top_k=5)

    assert len(results) == 2
    assert {r["program_id"] for r in results} == {1, 2}


def test_tna_boost_alone_rescues_a_candidate_from_exclusion():
    # A program with weak personal text relevance still stays eligible
    # when it's a real, independent signal instead - the person's own
    # college officially (or self-reportedly) asked for it, which is a
    # genuinely different kind of evidence than "just what XGBoost's
    # generic role prior guessed."
    programs = make_programs(categories={1: "Technology"})
    xgb = FakeXGB({"Technology": 0.9})
    matcher = FakeMatcher({1: 0.05})  # would be excluded on text alone
    tna = FakeTnaMatcher({("CCJE", 1): 0.55})  # clears TNA_EXPLANATION_THRESHOLD (0.47)

    recommender = Recommender(xgb, matcher, tna)
    results = recommender.recommend(
        user_features={}, query_text="x", programs_by_id=programs, college_code="CCJE"
    )

    assert len(results) == 1
    assert results[0]["program_id"] == 1


def test_blank_submission_still_fills_top_k_with_role_based_fallback():
    # The one deliberate exception: nothing typed anywhere (has_real_query
    # is False) means there's no personal description to hold a program
    # accountable to, so the structured/role-based fallback keeps filling
    # every slot exactly as it always has - excluding here would be
    # wrong, not honest, since there was never a specific claim to fail
    # to match in the first place. Every result in this case is expected
    # to carry the low-confidence label, since none of them are
    # personalized to anything.
    programs = make_programs(categories={1: "Technology", 2: "Research", 3: "Pedagogy"})
    xgb = FakeXGB({"Technology": 0.9, "Research": 0.7, "Pedagogy": 0.5})
    matcher = FakeMatcher({})  # blank query -> matcher would never be given real text either

    recommender = Recommender(xgb, matcher)
    results = recommender.recommend(user_features={}, query_text="   ", programs_by_id=programs)

    assert len(results) == 3
    assert all(
        r["reason"] == "No close match yet — shown as a general suggestion based on your role"
        for r in results
    )


def test_empty_catalog_returns_empty_list():
    xgb = FakeXGB({})
    matcher = FakeMatcher({})

    recommender = Recommender(xgb, matcher)
    results = recommender.recommend(user_features={}, query_text="x", programs_by_id={})

    assert results == []


def test_tna_boost_adds_to_combined_score():
    programs = make_programs(categories={1: "Technology"})
    xgb = FakeXGB({"Technology": 0.5})
    matcher = FakeMatcher({1: 0.5})
    tna = FakeTnaMatcher({("CCJE", 1): 0.8})

    recommender = Recommender(xgb, matcher, tna)
    results = recommender.recommend(
        user_features={}, query_text="x", programs_by_id=programs, college_code="CCJE"
    )

    # top text score (0.5) clears the confident threshold, so this uses
    # STRUCTURED_WEIGHT_CONFIDENT/TEXT_WEIGHT_CONFIDENT (0.08/0.92 - still
    # sums to 1.0, so the structured==text==0.5 part is unaffected, same
    # as it was under the old 0.5/0.5 and 0.4/0.6 splits) plus
    # TNA_WEIGHT_CONFIDENT (0.04, not the normal-mode 0.2 - the TNA/self-
    # reported boost is scaled down in confident mode too, see
    # recommender.py):
    # 0.08*0.5 + 0.92*0.5 + 0.04*0.8 = 0.532
    assert results[0]["score"] == 0.532


def test_college_with_no_tna_submissions_gets_no_boost_not_penalty():
    # CCS submitted nothing for TNA 2025 - must score exactly as if the
    # feature didn't exist, never worse.
    programs = make_programs(categories={1: "Technology"})
    xgb = FakeXGB({"Technology": 0.5})
    matcher = FakeMatcher({1: 0.5})
    tna = FakeTnaMatcher({("CCJE", 1): 0.8})  # CCS has no entries at all

    recommender = Recommender(xgb, matcher, tna)
    results = recommender.recommend(
        user_features={}, query_text="x", programs_by_id=programs, college_code="CCS"
    )

    assert results[0]["score"] == 0.5  # same as no TNA feature at all


def test_reason_prioritizes_tna_match_above_threshold():
    # 2026-09-09 - rewritten. The old version deliberately gave
    # structured_score (0.9) a huge edge specifically to prove TNA "won
    # the reason anyway" once its raw similarity cleared
    # TNA_EXPLANATION_THRESHOLD - that was exactly the real bug found live
    # (a CAS instructor's top recommendation was credited to "what
    # colleagues have asked for" when that signal actually contributed a
    # fraction of what the generic structured prior contributed). The
    # reason is now based on which signal's WEIGHTED contribution is
    # largest, so this test instead uses a modest structured_score - TNA
    # should still win the explanation, but because it genuinely
    # contributed more, not merely because its raw number crossed a line.
    programs = make_programs(categories={1: "Technology"})
    xgb = FakeXGB({"Technology": 0.2})
    matcher = FakeMatcher({1: 0.1})
    tna = FakeTnaMatcher({("CCJE", 1): 0.9})  # well above TNA_EXPLANATION_THRESHOLD (0.47)

    recommender = Recommender(xgb, matcher, tna)
    results = recommender.recommend(
        user_features={}, query_text="x", programs_by_id=programs, college_code="CCJE"
    )

    assert results[0]["reason"] == "Related to a training your college has officially requested in a Training Needs Assessment"


def test_weak_tna_similarity_does_not_claim_official_request():
    # text_score kept below TEXT_MATCH_STRONG_THRESHOLD (0.5) so this
    # test still isolates the TNA-threshold behavior it's named for,
    # rather than incidentally exercising the strong-text-match branch.
    programs = make_programs(categories={1: "Technology"})
    xgb = FakeXGB({"Technology": 0.1})
    matcher = FakeMatcher({1: 0.3})
    tna = FakeTnaMatcher({("CCJE", 1): 0.3})  # below threshold - still boosts score, not the reason

    recommender = Recommender(xgb, matcher, tna)
    results = recommender.recommend(
        user_features={}, query_text="x", programs_by_id=programs, college_code="CCJE"
    )

    assert results[0]["reason"] == "Matches the training you described"


def test_no_tna_matcher_behaves_exactly_as_before():
    # Omitting tna_matcher still must not crash and must contribute 0 to
    # the score - that part is unaffected by the confident-mode change
    # below (tna_weight is simply irrelevant when there's no matcher at
    # all). Top text score (0.4) clears the confident threshold, so the
    # combined value itself uses the confident-mode structured/text split.
    programs = make_programs(categories={1: "Technology"})
    recommender = Recommender(FakeXGB({"Technology": 0.8}), FakeMatcher({1: 0.4}))
    results = recommender.recommend(
        user_features={}, query_text="x", programs_by_id=programs, college_code="CCJE"
    )
    # 0.08*0.8 + 0.92*0.4 = 0.432 (updated 2026-09-03 for the confident-mode fix)
    assert results[0]["score"] == 0.432


def test_self_reported_fallback_uses_smaller_weight_than_official():
    # CCS has no official 2025 TNA submission, so its boost comes from
    # what its own employees have said in their own assessments -
    # SELF_REPORTED_WEIGHT (0.12), not TNA_WEIGHT (0.2).
    programs = make_programs(categories={1: "Technology"})
    xgb = FakeXGB({"Technology": 0.5})
    matcher = FakeMatcher({1: 0.5})
    tna = FakeTnaMatcher({("CCS", 1): 0.8}, sources={"CCS": "self_reported"})

    recommender = Recommender(xgb, matcher, tna)
    results = recommender.recommend(
        user_features={}, query_text="x", programs_by_id=programs, college_code="CCS"
    )

    # top text score (0.5) clears the confident threshold ->
    # SELF_REPORTED_WEIGHT_CONFIDENT (0.02) applies instead of the
    # normal-mode 0.12, same reasoning as
    # test_tna_boost_adds_to_combined_score above:
    # 0.08*0.5 + 0.92*0.5 + 0.02*0.8 = 0.516
    assert results[0]["score"] == 0.516


def test_self_reported_reason_is_worded_differently_from_official():
    # See test_reason_prioritizes_tna_match_above_threshold's 2026-09-09
    # note - structured_score kept modest so TNA's weighted contribution
    # genuinely leads, matching what the reason logic now actually checks.
    programs = make_programs(categories={1: "Technology"})
    xgb = FakeXGB({"Technology": 0.2})
    matcher = FakeMatcher({1: 0.1})
    tna = FakeTnaMatcher({("CCS", 1): 0.9}, sources={"CCS": "self_reported"})

    recommender = Recommender(xgb, matcher, tna)
    results = recommender.recommend(
        user_features={}, query_text="x", programs_by_id=programs, college_code="CCS"
    )

    assert results[0]["reason"] == "Related to what colleagues in your college have asked for in their own assessments"


def test_tna_reason_does_not_fire_when_structured_actually_dominated():
    # 2026-09-09 - the real bug this guards against: a CAS Biology
    # instructor's top recommendation was worded "related to what
    # colleagues in your college have asked for," but that TNA signal was
    # only ~2% of his actual score (SELF_REPORTED_WEIGHT_CONFIDENT) - the
    # generic, role-based structured prior contributed roughly four times
    # as much and went unmentioned. Here structured_score (0.9) is picked
    # to genuinely dominate a TNA boost (0.55) that still clears
    # TNA_EXPLANATION_THRESHOLD (0.47) on its own - the reason must NOT
    # credit TNA just because its raw number crossed that line.
    programs = make_programs(categories={1: "Technology"})
    xgb = FakeXGB({"Technology": 0.9})
    matcher = FakeMatcher({1: 0.1})
    tna = FakeTnaMatcher({("CCJE", 1): 0.55})

    recommender = Recommender(xgb, matcher, tna)
    results = recommender.recommend(
        user_features={}, query_text="x", programs_by_id=programs, college_code="CCJE"
    )

    assert results[0]["reason"] != "Related to a training your college has officially requested in a Training Needs Assessment"
    assert results[0]["reason"] != "Related to what colleagues in your college have asked for in their own assessments"


def test_confident_mode_lets_a_strong_specific_match_win_over_a_generic_favorite():
    # Modeled directly on the real 2026-09-03 CCS case (see
    # recommender.py's TOP_TEXT_CONFIDENT_THRESHOLD comment): a program
    # with a much higher structured_score but a weak text match ("the
    # generic favorite") should NOT beat a program with a strong,
    # specific text match once that match clears the confident threshold,
    # even though the normal-mode weights would have let it win.
    # program 1's text_score (0.21) is deliberately kept just above
    # NO_GENUINE_MATCH_THRESHOLD (0.20) so it stays eligible and this
    # test still isolates the confident-mode WEIGHTING effect, not the
    # separate exclusion mechanism (see the dedicated exclusion tests).
    programs = make_programs(categories={1: "Pedagogy", 2: "Communication"})
    xgb = FakeXGB({"Pedagogy": 0.74, "Communication": 0.25})
    matcher = FakeMatcher({1: 0.21, 2: 0.33})  # program 2's 0.33 clears the 0.30 threshold

    recommender = Recommender(xgb, matcher)
    results = recommender.recommend(user_features={}, query_text="x", programs_by_id=programs)

    assert len(results) == 2  # both stay eligible - this is about ranking, not exclusion
    assert results[0]["program_id"] == 2
    # sanity: under the OLD normal-mode weights (0.4/0.6) program 1 would
    # have won instead (0.4*0.74 + 0.6*0.21 = 0.422 > 0.4*0.25 + 0.6*0.33 = 0.298)
    # - this test exists specifically to lock in that this no longer happens.


def test_normal_mode_weights_apply_when_no_strong_text_match():
    # The other half of the same fix: when NOTHING in the catalog is a
    # strong text match (top score stays below the confident threshold -
    # e.g. a vague query, or the pre-catalog-fix Fisheries case where
    # every text score was near-zero), the structured/role-based prior
    # keeps its normal, larger say instead of being suppressed too.
    # both scores kept just above NO_GENUINE_MATCH_THRESHOLD (0.20) so
    # both stay eligible - this isolates the confident/normal MODE
    # boundary (0.30) from the separate exclusion floor (0.20).
    programs = make_programs(categories={1: "Pedagogy", 2: "Communication"})
    xgb = FakeXGB({"Pedagogy": 0.74, "Communication": 0.25})
    matcher = FakeMatcher({1: 0.22, 2: 0.24})  # both above 0.20, both below the 0.30 threshold

    recommender = Recommender(xgb, matcher)
    results = recommender.recommend(user_features={}, query_text="x", programs_by_id=programs)

    # normal-mode weights (0.4/0.6): program 1 = 0.4*0.74+0.6*0.22 = 0.428,
    # program 2 = 0.4*0.25+0.6*0.24 = 0.244 - structured signal correctly
    # still decides it when text has nothing confident to offer.
    assert len(results) == 2
    assert results[0]["program_id"] == 1
    assert results[0]["score"] == 0.428


def test_college_with_no_data_at_all_still_gets_no_boost():
    # Neither official nor self-reported data exists for this college -
    # must behave exactly like the feature doesn't exist, same as before.
    programs = make_programs(categories={1: "Technology"})
    xgb = FakeXGB({"Technology": 0.5})
    matcher = FakeMatcher({1: 0.5})
    tna = FakeTnaMatcher({("CCJE", 1): 0.8}, sources={"CCJE": "official"})  # unrelated college

    recommender = Recommender(xgb, matcher, tna)
    results = recommender.recommend(
        user_features={}, query_text="x", programs_by_id=programs, college_code="CONAH"
    )

    assert results[0]["score"] == 0.5


def test_category_affinity_rescues_a_specialization_relevant_program():
    # 2026-09-09 - the real fix this guards: even after the earlier
    # weighted-text fix, a real CAS Biology instructor's own exact words
    # ("Specialized Chemical & Microscopic Analysis") still scored below a
    # completely unrelated program on raw SBERT similarity alone - that's
    # the pretrained model keying on the shared word "Analysis", not a
    # weighting problem. Program 1 here plays that unrelated-but-lexically-
    # similar favorite (decent text score, matching category never
    # trained). Program 2 plays the genuinely relevant "Natural Sciences"
    # program that text alone ranks below it, rescued by a real category
    # affinity ("Biology" -> "Natural Sciences", modeled on the 0.50
    # checked live this session).
    programs = make_programs(categories={1: "Engineering", 2: "Natural Sciences"})
    xgb = FakeXGB({})  # neither category trained - keeps this isolated to text vs. category
    matcher = FakeMatcher(
        {1: 0.38, 2: 0.32},
        category_scores={"Natural Sciences": 0.50, "Engineering": 0.10},
    )

    recommender = Recommender(xgb, matcher, tna_matcher=None)
    results = recommender.recommend(
        user_features={}, query_text="x", programs_by_id=programs,
        specialization_text="Biology",
    )

    ranked_ids = [r["program_id"] for r in results]
    assert ranked_ids[0] == 2, f"expected the Natural Sciences program on top, got order {ranked_ids}"


def test_category_affinity_does_not_override_a_stronger_specific_text_match():
    # The other real case this same session hit: a CCS/Computer Science
    # instructor who explicitly asked for Communication training must NOT
    # get pulled back toward his own specialization's category
    # (Technology) just because that affinity is real - his own specific,
    # on-topic text match has to still win. Program 1 = a Communication
    # program with a strong, specific text match. Program 2 = a Technology
    # program with a weak text match but Technology is his declared
    # specialization's top affinity.
    programs = make_programs(categories={1: "Communication", 2: "Technology"})
    xgb = FakeXGB({})
    matcher = FakeMatcher(
        {1: 0.40, 2: 0.12},
        category_scores={"Technology": 0.55, "Communication": 0.15},
    )

    recommender = Recommender(xgb, matcher, tna_matcher=None)
    results = recommender.recommend(
        user_features={}, query_text="I want to improve my Communication skills",
        programs_by_id=programs, specialization_text="Computer Science",
    )

    assert results[0]["program_id"] == 1


def test_no_category_scores_behaves_exactly_as_before():
    # A matcher with no category data on file (category_scores=None, the
    # default) must contribute nothing - same "missing signal isn't a
    # penalty" guarantee as every other optional signal in this file.
    programs = make_programs(categories={1: "Technology"})
    xgb = FakeXGB({"Technology": 0.5})
    matcher = FakeMatcher({1: 0.5})  # no category_scores passed

    recommender = Recommender(xgb, matcher, tna_matcher=None)
    results = recommender.recommend(
        user_features={}, query_text="x", programs_by_id=programs,
        specialization_text="Biology",
    )

    assert results[0]["score"] == 0.5
