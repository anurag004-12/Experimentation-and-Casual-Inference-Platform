import pytest

from app.sequential import compare_strategies, sequential_check


def test_fixed_horizon_keeps_5_percent_false_alarms():
    r = compare_strategies(true_effect=0.0, seed=0)
    assert 0.04 < r["fixed_horizon"] < 0.06


def test_naive_peeking_inflates_false_alarms():
    r = compare_strategies(true_effect=0.0, n_looks=10, seed=0)
    assert r["naive_peeking"] > 0.15          # theory: about 19%


def test_more_peeks_means_more_false_alarms():
    few = compare_strategies(true_effect=0.0, n_looks=3, seed=1)["naive_peeking"]
    many = compare_strategies(true_effect=0.0, n_looks=14, seed=1)["naive_peeking"]
    assert many > few


def test_sequential_method_stays_under_alpha_even_with_peeking():
    r = compare_strategies(true_effect=0.0, n_looks=14, seed=2)
    assert r["sequential"] < 0.05


def test_sequential_detects_real_effect_and_can_stop_early():
    r = compare_strategies(true_effect=0.08, seed=3)
    assert r["sequential"] > 0.75
    assert r["sequential_avg_users_per_group"] < r["max_users_per_group"]


def test_sequential_check_decisions():
    assert sequential_check(0.10, 3000, 1.0)["decision"] == "stop: significant"
    assert sequential_check(0.01, 3000, 1.0)["decision"] == "keep collecting data"


def test_sequential_check_rejects_bad_input():
    with pytest.raises(ValueError):
        sequential_check(0.1, 0, 1.0)