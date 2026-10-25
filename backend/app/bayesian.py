"""Bayesian A/B analysis (spec step 5): "what is the probability B beats A?"

Model (Beta-Binomial):
    p_a ~ Beta(prior_alpha, prior_beta)      our belief about A's rate BEFORE data
    p_b ~ Beta(prior_alpha, prior_beta)
    conversions_a ~ Binomial(n_a, p_a)       how likely the data is, given p_a
    conversions_b ~ Binomial(n_b, p_b)

Two engines give the same answer:
- "analytic": uses the exact conjugate solution (instant).
- "pymc"    : samples the posterior with PyMC (general-purpose; the approach
              you would use if the model were too complex for a formula).
Having both lets you VERIFY the PyMC model against known math.
"""
import numpy as np


def _validate(conv_a, n_a, conv_b, n_b, prior_alpha, prior_beta):
    if not (0 <= conv_a <= n_a and 0 <= conv_b <= n_b) or n_a <= 0 or n_b <= 0:
        raise ValueError("Conversions must be between 0 and the group size, "
                         "and both groups need at least one user.")
    if prior_alpha <= 0 or prior_beta <= 0:
        raise ValueError("prior_alpha and prior_beta must be > 0.")


def _summarize(p_a: np.ndarray, p_b: np.ndarray, engine: str) -> dict:
    """Turn posterior samples of the two rates into business-friendly numbers."""
    lift = p_b - p_a
    prob_b = float((p_b > p_a).mean())
    return {
        "engine": engine,
        "prob_b_beats_a": prob_b,
        "rate_a_mean": float(p_a.mean()),
        "rate_b_mean": float(p_b.mean()),
        "abs_lift_mean": float(lift.mean()),
        "abs_lift_ci95": [float(np.percentile(lift, 2.5)), float(np.percentile(lift, 97.5))],
        "rel_lift_mean": float((lift / p_a).mean()),
        # Expected loss = average conversion rate we give up if we pick that
        # variant and it turns out to be the worse one.
        "expected_loss_choose_b": float(np.maximum(p_a - p_b, 0).mean()),
        "expected_loss_choose_a": float(np.maximum(p_b - p_a, 0).mean()),
        "decision": ("B is very likely better" if prob_b >= 0.95 else
                     "A is very likely better" if prob_b <= 0.05 else
                     "Not enough evidence yet"),
    }


def bayesian_ab_analytic(conv_a: int, n_a: int, conv_b: int, n_b: int,
                         prior_alpha: float = 1.0, prior_beta: float = 1.0,
                         n_samples: int = 200_000, seed: int = 0) -> dict:
    """Exact posterior: Beta(prior_alpha + conversions, prior_beta + non-conversions)."""
    _validate(conv_a, n_a, conv_b, n_b, prior_alpha, prior_beta)
    rng = np.random.default_rng(seed)
    p_a = rng.beta(prior_alpha + conv_a, prior_beta + n_a - conv_a, n_samples)
    p_b = rng.beta(prior_alpha + conv_b, prior_beta + n_b - conv_b, n_samples)
    return _summarize(p_a, p_b, "analytic")


def bayesian_ab_pymc(conv_a: int, n_a: int, conv_b: int, n_b: int,
                     prior_alpha: float = 1.0, prior_beta: float = 1.0,
                     draws: int = 2_000, tune: int = 1_000, chains: int = 2,
                     seed: int = 0) -> dict:
    """Same model, sampled with PyMC (MCMC)."""
    _validate(conv_a, n_a, conv_b, n_b, prior_alpha, prior_beta)
    import pymc as pm  # imported here: PyMC is heavy, so the API starts fast without it

    with pm.Model():
        p_a = pm.Beta("p_a", alpha=prior_alpha, beta=prior_beta)
        p_b = pm.Beta("p_b", alpha=prior_alpha, beta=prior_beta)
        pm.Binomial("obs_a", n=n_a, p=p_a, observed=conv_a)
        pm.Binomial("obs_b", n=n_b, p=p_b, observed=conv_b)
        idata = pm.sample(draws=draws, tune=tune, chains=chains, random_seed=seed,
                          progressbar=False, cores=1)

    post = idata.posterior
    return _summarize(np.asarray(post["p_a"]).ravel(), np.asarray(post["p_b"]).ravel(), "pymc")