import pytest

from app.bayesian import bayesian_ab_analytic
from app.experiments import compare_proportions


def test_clear_winner_gets_high_probability():
    r = bayesian_ab_analytic(100, 1000, 130, 1000)
    assert 0.97 < r["prob_b_beats_a"] < 0.99
    assert r["decision"] == "B is very likely better"
    assert r["abs_lift_ci95"][0] > 0          # whole 95% range is above zero


def test_identical_data_is_a_coin_flip():
    r = bayesian_ab_analytic(100, 1000, 100, 1000)
    assert r["prob_b_beats_a"] == pytest.approx(0.5, abs=0.01)
    assert r["decision"] == "Not enough evidence yet"


def test_b_worse_than_a_is_detected():
    r = bayesian_ab_analytic(130, 1000, 100, 1000)
    assert r["prob_b_beats_a"] < 0.05
    assert r["decision"] == "A is very likely better"


def test_strong_prior_pulls_small_samples_toward_a_coin_flip():
    flat = bayesian_ab_analytic(3, 10, 5, 10)["prob_b_beats_a"]
    strong = bayesian_ab_analytic(3, 10, 5, 10, prior_alpha=100, prior_beta=100)["prob_b_beats_a"]
    assert abs(strong - 0.5) < abs(flat - 0.5)


def test_expected_loss_is_tiny_when_b_clearly_wins():
    r = bayesian_ab_analytic(100, 1000, 130, 1000)
    assert r["expected_loss_choose_b"] < 0.001
    assert r["expected_loss_choose_a"] > 0.02


def test_agrees_with_frequentist_test_on_large_samples():
    """With a flat prior, P(B beats A) is about 1 - (two-sided p-value / 2)."""
    b = bayesian_ab_analytic(100, 1000, 130, 1000)["prob_b_beats_a"]
    p = compare_proportions(100, 1000, 130, 1000)["p_value"]
    assert b == pytest.approx(1 - p / 2, abs=0.005)


def test_rejects_bad_input():
    with pytest.raises(ValueError):
        bayesian_ab_analytic(1500, 1000, 100, 1000)
    with pytest.raises(ValueError):
        bayesian_ab_analytic(10, 100, 10, 100, prior_alpha=0)


def test_pymc_matches_exact_math():
    pytest.importorskip("pymc")
    from app.bayesian import bayesian_ab_pymc
    exact = bayesian_ab_analytic(100, 1000, 130, 1000)
    sampled = bayesian_ab_pymc(100, 1000, 130, 1000)
    assert sampled["prob_b_beats_a"] == pytest.approx(exact["prob_b_beats_a"], abs=0.02)
    assert sampled["abs_lift_mean"] == pytest.approx(exact["abs_lift_mean"], abs=0.003)