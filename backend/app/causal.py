"""Observational causal methods (spec step 6).

Part A (this file): when people CHOOSE the treatment (no randomization),
the treated and untreated groups differ from the start. We use a simulator
with a KNOWN true effect to grade each method.

    naive difference ........ ignores the problem (biased)
    regression adjustment ... controls for covariates
    propensity matching ..... compares treated users to look-alike untreated users
    DoWhy ................... same idea via a standard causal-inference library
    EconML (DML) ............ machine-learning-based adjustment

Part B (next step): difference-in-differences and synthetic control.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors

COVARIATES = ["activity", "tenure"]


def simulate_confounded(n: int = 5_000, true_effect: float = 2.0,
                        confounding: float = 1.0, hidden_confounding: float = 0.0,
                        seed: int = 0) -> pd.DataFrame:
    """Users who were already more active (and longer-tenured) opt in more often.

    activity, tenure : things we can measure (the 'confounders')
    treated          : 1 if the user opted in to the feature
    outcome          : e.g. spend; depends on the confounders AND on treatment
    confounding      : 0 = opt-in is random; higher = opt-in depends more on activity/tenure
    hidden_confounding : strength of an UNMEASURED driver ('motivation') that raises
                       both opt-in and spend. It is in the data for transparency but
                       is NOT in COVARIATES, mimicking what you can't observe in real life.
    """
    rng = np.random.default_rng(seed)
    activity = rng.normal(0, 1, n)
    tenure = rng.normal(0, 1, n)
    motivation = np.random.default_rng(seed + 1).normal(0, 1, n)   # separate stream
    logit = confounding * (0.8 * activity + 0.5 * tenure) + hidden_confounding * motivation
    treated = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    outcome = (5 + 3 * activity + 2 * tenure + 2 * hidden_confounding * motivation
               + true_effect * treated + rng.normal(0, 2, n))
    return pd.DataFrame({"activity": activity, "tenure": tenure, "motivation": motivation,
                         "treated": treated, "outcome": outcome})


def naive_estimate(df: pd.DataFrame) -> dict:
    """Plain difference in means. Wrong when treatment was not randomized."""
    t, c = df.loc[df.treated == 1, "outcome"], df.loc[df.treated == 0, "outcome"]
    return {"method": "naive difference", "effect": float(t.mean() - c.mean())}


def regression_adjustment(df: pd.DataFrame, covariates=COVARIATES) -> dict:
    """OLS of outcome on treatment + covariates; the treatment coefficient is the effect."""
    X = sm.add_constant(df[["treated", *covariates]])
    fit = sm.OLS(df["outcome"], X).fit()
    lo, hi = fit.conf_int().loc["treated"]
    return {"method": "regression adjustment", "effect": float(fit.params["treated"]),
            "ci_95": [float(lo), float(hi)]}


def standardized_mean_diff(df: pd.DataFrame, covariates=COVARIATES,
                           weights=None) -> dict:
    """Balance check: how different are treated vs untreated on each covariate?
    Rule of thumb: |SMD| < 0.1 means well balanced."""
    w = np.ones(len(df)) if weights is None else np.asarray(weights, dtype=float)
    out = {}
    for c in covariates:
        t = df["treated"].values == 1
        m1 = np.average(df.loc[t, c], weights=w[t])
        m0 = np.average(df.loc[~t, c], weights=w[~t])
        pooled = np.sqrt((df.loc[t, c].var() + df.loc[~t, c].var()) / 2)
        out[c] = float((m1 - m0) / pooled)
    return out


def propensity_matching(df: pd.DataFrame, covariates=COVARIATES,
                        caliper_sd: float = 0.2, seed: int = 0) -> dict:
    """Match each treated user to the most similar untreated user.

    1. Propensity score = predicted chance of being treated, from covariates.
    2. For each treated user, find the untreated user with the closest score
       (matching WITH replacement), but only if it is within a caliper.
    3. Effect = average outcome gap across matched pairs (effect on the treated, ATT).
    """
    ps_model = LogisticRegression(max_iter=1000).fit(df[covariates], df["treated"])
    ps = np.clip(ps_model.predict_proba(df[covariates])[:, 1], 1e-6, 1 - 1e-6)
    logit_ps = np.log(ps / (1 - ps))
    caliper = caliper_sd * logit_ps.std()

    treated_idx = np.where(df["treated"].values == 1)[0]
    control_idx = np.where(df["treated"].values == 0)[0]
    nn = NearestNeighbors(n_neighbors=1).fit(logit_ps[control_idx].reshape(-1, 1))
    dist, pos = nn.kneighbors(logit_ps[treated_idx].reshape(-1, 1))
    keep = dist.ravel() <= caliper
    matched_t = treated_idx[keep]
    matched_c = control_idx[pos.ravel()[keep]]

    y = df["outcome"].values
    gaps = y[matched_t] - y[matched_c]
    se = gaps.std(ddof=1) / np.sqrt(len(gaps))   # simple approximation

    # Balance after matching: weight each control by how often it was matched.
    w = np.zeros(len(df))
    w[matched_t] += 1
    np.add.at(w, matched_c, 1)
    keep_rows = w > 0
    balance_after = standardized_mean_diff(df[keep_rows].reset_index(drop=True),
                                           covariates, w[keep_rows])
    return {"method": "propensity matching", "effect": float(gaps.mean()),
            "ci_95": [float(gaps.mean() - 1.96 * se), float(gaps.mean() + 1.96 * se)],
            "n_treated": int(len(treated_idx)), "n_matched": int(len(matched_t)),
            "balance_before": standardized_mean_diff(df, covariates),
            "balance_after": balance_after}


def dowhy_estimate(df: pd.DataFrame, covariates=COVARIATES, refute: bool = False) -> dict:
    """Same question through DoWhy's 4-step workflow: model, identify, estimate, refute."""
    from dowhy import CausalModel
    model = CausalModel(data=df, treatment="treated", outcome="outcome",
                        common_causes=list(covariates))
    estimand = model.identify_effect(proceed_when_unidentifiable=True)
    est = model.estimate_effect(estimand, method_name="backdoor.propensity_score_stratification",
                                target_units="att")
    out = {"method": "DoWhy (propensity stratification)", "effect": float(est.value)}
    if refute:
        ref = model.refute_estimate(estimand, est, method_name="placebo_treatment_refuter",
                                    placebo_type="permute", num_simulations=20)
        out["placebo_effect"] = float(ref.new_effect)   # should be close to 0
    return out


def econml_dml_estimate(df: pd.DataFrame, covariates=COVARIATES, seed: int = 0) -> dict:
    """Double Machine Learning: flexible ML models remove the covariates' influence
    from both treatment and outcome, then the leftover relationship is the effect."""
    from econml.dml import LinearDML
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
    est = LinearDML(model_y=RandomForestRegressor(n_estimators=100, min_samples_leaf=20,
                                                  random_state=seed, n_jobs=-1),
                    model_t=RandomForestClassifier(n_estimators=100, min_samples_leaf=20,
                                                   random_state=seed, n_jobs=-1),
                    discrete_treatment=True, random_state=seed)
    est.fit(df["outcome"], df["treated"], X=None, W=df[list(covariates)])
    lo, hi = est.ate_interval(X=None, alpha=0.05)
    return {"method": "EconML (LinearDML)", "effect": float(est.ate(X=None)),
            "ci_95": [float(np.ravel(lo)[0]), float(np.ravel(hi)[0])]}


def compare_methods(n: int = 5_000, true_effect: float = 2.0, confounding: float = 1.0,
                    hidden_confounding: float = 0.0, seed: int = 0,
                    use_dowhy: bool = True, use_econml: bool = True) -> dict:
    """The 'Method Arena': run every method on the same confounded data and
    report how far each lands from the TRUE effect."""
    df = simulate_confounded(n, true_effect, confounding, hidden_confounding, seed)
    results = [naive_estimate(df), regression_adjustment(df), propensity_matching(df, seed=seed)]
    if use_dowhy:
        results.append(dowhy_estimate(df))
    if use_econml:
        results.append(econml_dml_estimate(df, seed=seed))
    for r in results:
        r["error_vs_truth"] = r["effect"] - true_effect
    return {"true_effect": true_effect, "confounding": confounding,
            "hidden_confounding": hidden_confounding, "n": n, "results": results}