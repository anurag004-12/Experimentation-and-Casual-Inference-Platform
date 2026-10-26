import pytest

from app.causal import (compare_methods, naive_estimate, propensity_matching,
                        regression_adjustment, simulate_confounded)

TRUE = 2.0


def test_naive_is_badly_biased_when_people_self_select():
    df = simulate_confounded(true_effect=TRUE, confounding=1.0)
    assert naive_estimate(df)["effect"] > 4.0          # true effect is only 2


def test_naive_is_fine_when_there_is_no_confounding():
    df = simulate_confounded(true_effect=TRUE, confounding=0.0)
    assert naive_estimate(df)["effect"] == pytest.approx(TRUE, abs=0.4)


def test_regression_adjustment_recovers_truth():
    df = simulate_confounded(true_effect=TRUE)
    assert regression_adjustment(df)["effect"] == pytest.approx(TRUE, abs=0.2)


def test_matching_recovers_truth_and_fixes_balance():
    df = simulate_confounded(true_effect=TRUE)
    r = propensity_matching(df)
    assert r["effect"] == pytest.approx(TRUE, abs=0.3)
    assert all(abs(v) > 0.3 for v in r["balance_before"].values())   # groups started different
    assert all(abs(v) < 0.05 for v in r["balance_after"].values())   # matching fixed it
    assert r["n_matched"] > 0.9 * r["n_treated"]


def test_hidden_confounder_breaks_every_method():
    """If an important driver is unmeasured, adjusting for what we CAN see is not enough."""
    df = simulate_confounded(true_effect=TRUE, hidden_confounding=1.0)
    assert regression_adjustment(df)["effect"] - TRUE > 1.0
    assert propensity_matching(df)["effect"] - TRUE > 1.0
    oracle = regression_adjustment(df, ["activity", "tenure", "motivation"])["effect"]
    assert oracle == pytest.approx(TRUE, abs=0.25)                    # only if we could measure it


def test_dowhy_matches_truth_and_passes_placebo():
    pytest.importorskip("dowhy")
    from app.causal import dowhy_estimate
    r = dowhy_estimate(simulate_confounded(true_effect=TRUE), refute=True)
    assert r["effect"] == pytest.approx(TRUE, abs=0.3)
    assert abs(r["placebo_effect"]) < 0.3                             # fake treatment -> ~0 effect


def test_econml_matches_truth():
    pytest.importorskip("econml")
    from app.causal import econml_dml_estimate
    r = econml_dml_estimate(simulate_confounded(true_effect=TRUE))
    assert r["effect"] == pytest.approx(TRUE, abs=0.3)
    assert r["ci_95"][0] < TRUE < r["ci_95"][1]


def test_compare_methods_reports_error_vs_truth():
    r = compare_methods(use_dowhy=False, use_econml=False)
    errors = {x["method"]: x["error_vs_truth"] for x in r["results"]}
    assert errors["naive difference"] > 2.0
    assert abs(errors["regression adjustment"]) < 0.3

# ---------------- Part B: difference-in-differences and synthetic control ----------------
import numpy as np

from app.causal import (_fit_weights, compare_panel_methods, did_estimate,
                        simulate_panel, synthetic_control)


def test_did_works_when_parallel_trends_holds():
    df = simulate_panel(true_effect=-3.0, loading_spread=0.0)
    r = did_estimate(df)
    assert r["effect"] == pytest.approx(-3.0, abs=0.5)
    assert r["parallel_trends_ok"] is True


def test_did_fails_and_warns_when_parallel_trends_is_violated():
    r = did_estimate(simulate_panel(true_effect=-3.0, loading_spread=1.0))
    assert abs(r["effect"] - (-3.0)) > 2.0          # badly wrong...
    assert r["parallel_trends_ok"] is False         # ...and the pre-trend check says so


def test_did_invents_an_effect_that_does_not_exist():
    r = did_estimate(simulate_panel(true_effect=0.0, loading_spread=1.0))
    assert abs(r["effect"]) > 2.0                   # no policy effect, yet DiD finds one


def test_synthetic_control_survives_the_violation():
    both = compare_panel_methods(true_effect=-3.0, loading_spread=1.0)
    assert abs(both["synthetic_control"]["error_vs_truth"]) < 1.0
    assert abs(both["synthetic_control"]["error_vs_truth"]) < abs(both["did"]["error_vs_truth"]) / 3


def test_synthetic_control_does_not_invent_effects():
    r = synthetic_control(simulate_panel(true_effect=0.0, loading_spread=1.0))
    assert abs(r["effect"]) < 1.0
    assert r["placebo_p_value"] > 0.2               # a gap this size is common by luck


def test_synthetic_control_placebo_test_flags_a_real_effect():
    r = synthetic_control(simulate_panel(true_effect=-3.0, loading_spread=0.0))
    assert r["placebo_p_value"] < 0.1
    assert r["pre_fit_rmspe"] < 1.5


def test_synthetic_weights_are_valid():
    df = simulate_panel()
    wide = df.pivot(index="time", columns="unit", values="outcome")
    pre = wide.index < 20
    w = _fit_weights(wide[0].values[pre], wide.drop(columns=0).values[pre])
    assert w.min() >= 0 and w.sum() == pytest.approx(1.0)