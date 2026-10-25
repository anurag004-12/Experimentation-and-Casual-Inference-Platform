"""Experiment simulation, trust checks ('Experiment Doctor') and classic tests.

Contents
- simulate_experiment : ground-truth data generator (we choose the true effect)
- srm_check           : sample ratio mismatch alarm
- cuped_adjust        : variance reduction using pre-experiment data
- compare_means       : Welch t-test with confidence interval

TODO (Phase 2): chi-square test for conversions, Bonferroni and
Benjamini-Hochberg multiple-testing corrections, novelty-effect check.
"""
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests


def simulate_experiment(
    n_users: int = 20_000,
    baseline_mean: float = 10.0,
    true_effect: float = 0.5,
    noise_sd: float = 5.0,
    pre_corr: float = 0.7,
    treat_share: float = 0.5,
    srm_bug: float = 0.0,
    novelty_decay: float = 0.0,
    n_days: int = 14,
    seed: int = 42,
) -> pd.DataFrame:
    """Simulate a continuous-metric A/B test with a KNOWN true effect.

    true_effect   : the real lift for treated users (the answer key).
    pre_corr      : correlation between pre-experiment and in-experiment metric.
    treat_share   : intended share of users assigned to treatment.
    srm_bug       : fraction of treated users silently dropped (fake logging bug).
    novelty_decay : 0 = constant effect; 0.3 = effect fades over the days.
    """
    rng = np.random.default_rng(seed)
    group = (rng.random(n_users) < treat_share).astype(int)

    latent = rng.normal(0, 1, n_users)  # user quality shared by 'before' and 'during'
    w_shared, w_idio = np.sqrt(pre_corr), np.sqrt(1 - pre_corr)  # => corr == pre_corr
    pre = baseline_mean + noise_sd * (w_shared * latent + w_idio * rng.normal(0, 1, n_users))

    day = rng.integers(1, n_days + 1, n_users)
    effect_by_day = true_effect * np.exp(-novelty_decay * (day - 1))
    y = baseline_mean + noise_sd * (w_shared * latent + w_idio * rng.normal(0, 1, n_users))
    y = y + group * effect_by_day

    df = pd.DataFrame({"user_id": np.arange(n_users), "group": group,
                       "pre_metric": pre, "metric": y, "day": day})
    if srm_bug > 0:
        drop = (df["group"] == 1) & (rng.random(len(df)) < srm_bug)
        df = df[~drop].reset_index(drop=True)
    return df


def srm_check(n_control: int, n_treatment: int, expected_treat_share: float = 0.5,
              alpha: float = 0.001) -> dict:
    """Sample Ratio Mismatch: did the split match the plan?
    Strict alpha (0.001) is the industry convention; SRM makes the whole test suspect."""
    total = n_control + n_treatment
    expected = [total * (1 - expected_treat_share), total * expected_treat_share]
    chi2, p = stats.chisquare([n_control, n_treatment], f_exp=expected)
    return {"observed_treat_share": n_treatment / total,
            "expected_treat_share": expected_treat_share,
            "chi2": float(chi2), "p_value": float(p), "srm_detected": bool(p < alpha),
            "message": ("WARNING: group sizes don't match the plan. Do not trust this result."
                        if p < alpha else "Group sizes match the plan.")}


def cuped_adjust(df: pd.DataFrame, metric: str = "metric",
                 pre: str = "pre_metric") -> pd.Series:
    """CUPED: remove the part of the metric predicted by pre-experiment behaviour.
    theta = Cov(Y, X) / Var(X);  adjusted Y = Y - theta * (X - mean(X))."""
    theta = np.cov(df[metric], df[pre])[0, 1] / np.var(df[pre], ddof=1)
    return df[metric] - theta * (df[pre] - df[pre].mean())


def compare_means(df: pd.DataFrame, metric: str = "metric", group: str = "group") -> dict:
    """Welch t-test on a metric (raw or CUPED-adjusted)."""
    a, b = df.loc[df[group] == 0, metric], df.loc[df[group] == 1, metric]
    t, p = stats.ttest_ind(b, a, equal_var=False)
    diff = b.mean() - a.mean()
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return {"effect": float(diff), "se": float(se),
            "ci_95": [float(diff - 1.96 * se), float(diff + 1.96 * se)],
            "p_value": float(p)}


def compare_proportions(conv_control: int, n_control: int,
                        conv_treatment: int, n_treatment: int,
                        alpha: float = 0.05) -> dict:
    """Compare two conversion rates (chi-square test on a 2x2 table)."""
    if not (0 <= conv_control <= n_control and 0 <= conv_treatment <= n_treatment):
        raise ValueError("Conversions must be between 0 and the group size.")
    if n_control == 0 or n_treatment == 0:
        raise ValueError("Both groups need at least one user.")

    table = [[conv_control, n_control - conv_control],
             [conv_treatment, n_treatment - conv_treatment]]
    chi2, p, _, _ = stats.chi2_contingency(table, correction=False)

    p_c, p_t = conv_control / n_control, conv_treatment / n_treatment
    diff = p_t - p_c
    se = np.sqrt(p_c * (1 - p_c) / n_control + p_t * (1 - p_t) / n_treatment)
    z = stats.norm.ppf(1 - alpha / 2)
    return {"rate_control": p_c, "rate_treatment": p_t,
            "abs_lift": float(diff),
            "rel_lift": float(diff / p_c) if p_c > 0 else None,
            "ci": [float(diff - z * se), float(diff + z * se)],
            "chi2": float(chi2), "p_value": float(p),
            "significant": bool(p < alpha)}


def adjust_pvalues(p_values: list, method: str = "benjamini-hochberg",
                   alpha: float = 0.05) -> list:
    """Correct p-values when you test many metrics/variants at once.

    bonferroni         : strict. Controls the chance of ANY false positive.
    benjamini-hochberg : looser. Controls the SHARE of false positives
                         among the results you call significant (FDR).
    """
    methods = {"bonferroni": "bonferroni", "benjamini-hochberg": "fdr_bh"}
    if method not in methods:
        raise ValueError(f"method must be one of {list(methods)}")
    if len(p_values) == 0:
        raise ValueError("Provide at least one p-value.")
    reject, adj, _, _ = multipletests(p_values, alpha=alpha, method=methods[method])
    return [{"p_value": float(p), "adjusted_p": float(a), "significant": bool(r)}
            for p, a, r in zip(p_values, adj, reject)]
