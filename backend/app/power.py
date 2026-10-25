"""Power and sample-size calculations (spec step 2)."""
from statsmodels.stats.power import NormalIndPower, TTestIndPower
from statsmodels.stats.proportion import proportion_effectsize


def sample_size_proportions(p_baseline: float, mde_abs: float,
                            alpha: float = 0.05, power: float = 0.8,
                            ratio: float = 1.0) -> dict:
    """Users needed PER GROUP to detect an absolute lift in a conversion rate."""
    if not 0 < p_baseline < 1 or not 0 < p_baseline + mde_abs < 1:
        raise ValueError("Baseline and baseline+MDE must both be between 0 and 1.")
    if mde_abs == 0:
        raise ValueError("mde_abs must be non-zero.")
    es = proportion_effectsize(p_baseline + mde_abs, p_baseline)
    n = NormalIndPower().solve_power(effect_size=abs(es), alpha=alpha,
                                     power=power, ratio=ratio,
                                     alternative="two-sided")
    return {"n_control": int(round(n)) + 1, "n_treatment": int(round(n * ratio)) + 1,
            "effect_size_cohens_h": float(abs(es))}


def sample_size_means(sd: float, mde_abs: float, alpha: float = 0.05,
                      power: float = 0.8, ratio: float = 1.0) -> dict:
    """Users needed PER GROUP to detect an absolute change in a mean metric."""
    if sd <= 0 or mde_abs == 0:
        raise ValueError("sd must be > 0 and mde_abs must be non-zero.")
    d = abs(mde_abs) / sd
    n = TTestIndPower().solve_power(effect_size=d, alpha=alpha, power=power,
                                    ratio=ratio, alternative="two-sided")
    return {"n_control": int(round(n)) + 1, "n_treatment": int(round(n * ratio)) + 1,
            "effect_size_cohens_d": float(d)}
