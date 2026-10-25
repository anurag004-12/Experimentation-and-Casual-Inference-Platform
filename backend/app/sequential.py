"""Sequential testing: let teams peek at results safely (spec step 4).

The problem: if you check a normal (fixed-horizon) test every day and stop the
first time p < 0.05, your real false-alarm rate is far above 5%.

The fix used here: the mixture Sequential Probability Ratio Test (mSPRT).
It gives an "evidence ratio" that stays valid no matter how often you look.
Rule: stop and call it significant when evidence_ratio >= 1 / alpha.

Simplifications (state these in your README):
- Metric is roughly normal; per-user standard deviation is known/estimated.
- Groups are equal size and grow together, so we treat each pair
  (one control user, one treatment user) as one observation of the
  difference. That difference has variance 2 * sd**2.
"""
import numpy as np
from scipy import stats


def msprt_log_evidence(sum_diff, n_pairs, sd: float, tau: float):
    """Log of the mSPRT evidence ratio (works on numbers or numpy arrays).

    sum_diff : sum over pairs of (treatment - control)
    n_pairs  : number of pairs so far (users per group)
    sd       : standard deviation of the metric for ONE user
    tau      : how big you expect the effect to be (prior spread of the
               effect, same units as the metric). Pick roughly your MDE.
    """
    s2 = 2.0 * sd**2          # variance of one pair-difference
    t2 = tau**2
    n = np.asarray(n_pairs, dtype=float)
    return (0.5 * np.log(s2 / (s2 + n * t2))
            + t2 * np.asarray(sum_diff, dtype=float) ** 2
            / (2.0 * s2 * (s2 + n * t2)))


def sequential_check(mean_diff: float, n_per_group: int, sd: float,
                     tau: float | None = None, alpha: float = 0.05) -> dict:
    """Live check for one experiment: can we stop now?"""
    if n_per_group <= 0 or sd <= 0 or not 0 < alpha < 1:
        raise ValueError("n_per_group and sd must be > 0, and 0 < alpha < 1.")
    tau = tau if tau is not None else 0.1 * sd
    if tau <= 0:
        raise ValueError("tau must be > 0.")
    log_ev = float(msprt_log_evidence(mean_diff * n_per_group, n_per_group, sd, tau))
    threshold = float(np.log(1 / alpha))
    evidence = float(np.exp(min(log_ev, 700)))   # avoid overflow
    stop = log_ev >= threshold
    return {"evidence_ratio": evidence,
            "stop_threshold": 1 / alpha,
            "always_valid_p": float(min(1.0, np.exp(-log_ev))),
            "decision": "stop: significant" if stop else "keep collecting data",
            "message": ("Evidence is strong enough to stop now, and this stays valid "
                        "even though you peeked." if stop else
                        "Not enough evidence yet. Peeking is safe; keep going.")}


def _simulate_paths(n_sims: int, users_per_look: int, n_looks: int,
                    true_effect: float, sd: float, rng) -> tuple:
    """Cumulative sum of (treatment - control) pair differences at each look.
    Each block of `users_per_look` pairs adds a Normal sum, so no need to
    simulate every user (fast and exact)."""
    block_mean = users_per_look * true_effect
    block_sd = np.sqrt(2.0 * users_per_look) * sd
    blocks = rng.normal(block_mean, block_sd, size=(n_sims, n_looks))
    sums = np.cumsum(blocks, axis=1)
    n_pairs = users_per_look * np.arange(1, n_looks + 1)
    return sums, n_pairs


def compare_strategies(true_effect: float = 0.0, n_sims: int = 20_000,
                       n_looks: int = 10, users_per_look: int = 500,
                       sd: float = 1.0, tau: float | None = None,
                       alpha: float = 0.05, seed: int = 0) -> dict:
    """Compare three ways of running the same experiment.

    - fixed_horizon : look ONCE at the end (the textbook way).
    - naive_peeking : look at every look, stop at the first p < alpha. (WRONG)
    - sequential    : look at every look using mSPRT. (SAFE)

    With true_effect = 0 the rates are FALSE-POSITIVE rates (should be <= alpha).
    With true_effect > 0 the rates are POWER (higher is better).
    """
    tau = tau if tau is not None else 0.1 * sd
    rng = np.random.default_rng(seed)
    sums, n = _simulate_paths(n_sims, users_per_look, n_looks, true_effect, sd, rng)

    z = sums / (np.sqrt(2.0) * sd * np.sqrt(n))           # z-stat at every look
    z_crit = stats.norm.ppf(1 - alpha / 2)
    fixed = np.abs(z[:, -1]) > z_crit
    naive = (np.abs(z) > z_crit).any(axis=1)

    log_ev = msprt_log_evidence(sums, n, sd, tau)
    crossed = log_ev >= np.log(1 / alpha)
    seq = crossed.any(axis=1)
    first_cross = np.where(seq, crossed.argmax(axis=1), n_looks - 1)
    avg_users = float((n[first_cross]).mean())

    return {"true_effect": true_effect, "n_looks": n_looks,
            "fixed_horizon": float(fixed.mean()),
            "naive_peeking": float(naive.mean()),
            "sequential": float(seq.mean()),
            "sequential_avg_users_per_group": avg_users,
            "max_users_per_group": int(n[-1])}