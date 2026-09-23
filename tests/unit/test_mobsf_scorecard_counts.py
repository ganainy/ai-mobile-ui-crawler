from mobile_crawler.core.crawler_loop import mobsf_scorecard_summary


def test_counts_finding_lists_from_real_scorecard():
    # MobSF's scorecard API returns each severity as a list of findings, not a count.
    scorecard = {
        "security_score": 51,
        "high": [{"title": "h"}],
        "warning": [{"title": "w1"}, {"title": "w2"}],
        "info": [{"title": "i"}],
    }

    assert mobsf_scorecard_summary(scorecard) == (51.0, 1, 2, 1)


def test_accepts_plain_counts_and_missing_keys():
    assert mobsf_scorecard_summary({"score": 70, "high": 3, "medium": 4}) == (70.0, 3, 4, 0)
