"""Upload-and-analyze layer (spec step 7): CSV in, plain-English verdict out.

Step A (this file): randomized A/B tests.
  1. Load and validate the CSV.
  2. Run the 'Experiment Doctor' checks (is the test trustworthy?).
  3. Run the right statistical test (binary metric -> chi-square + Bayesian,
     continuous metric -> Welch t-test, optionally with CUPED).
  4. Write a verdict a non-statistician can act on, plus chart-ready numbers.
"""
import io

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.power import NormalIndPower, TTestIndPower
from statsmodels.stats.proportion import proportion_confint

from .bayesian import bayesian_ab_analytic
from .experiments import compare_means, compare_proportions, cuped_adjust, srm_check

MIN_PER_GROUP = 30


# ----------------------------------------------------------------- loading
def load_csv(content: bytes) -> pd.DataFrame:
    if not content or not content.strip():
        raise ValueError("The file is empty.")
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise ValueError(f"Could not read the file as a CSV: {e}")
    if df.shape[0] == 0 or df.shape[1] < 2:
        raise ValueError("The CSV needs a header row, at least 2 columns and at least 1 data row.")
    return df


def preview(df: pd.DataFrame, n_rows: int = 5) -> dict:
    """Column summary so a UI can offer sensible choices (which column is the group?)."""
    cols = []
    for c in df.columns:
        s = df[c]
        cols.append({"name": str(c), "dtype": str(s.dtype),
                     "n_unique": int(s.nunique(dropna=True)),
                     "missing_pct": round(float(s.isna().mean() * 100), 2),
                     "examples": [str(v) for v in s.dropna().unique()[:3]]})
    head = df.head(n_rows)
    return {"n_rows": int(len(df)), "columns": cols,
            "head": head.astype(object).where(head.notna(), None).to_dict("records")}


# ----------------------------------------------------------------- helpers
def _need(df, *cols):
    for c in cols:
        if c is not None and c not in df.columns:
            raise ValueError(f"Column '{c}' not found. Available columns: {list(df.columns)}")


def _pick_labels(g: pd.Series, control_label, treatment_label):
    values = sorted(g.unique())
    c = None if control_label is None else str(control_label)
    t = None if treatment_label is None else str(treatment_label)
    for lab in (c, t):
        if lab is not None and lab not in values:
            raise ValueError(f"Group label '{lab}' not found. The group column contains: {values}")
    assumed = False
    if c is None and t is None:
        if len(values) != 2:
            raise ValueError(f"The group column has {len(values)} values {values[:6]}. "
                             "Tell me which is control and which is treatment.")
        c, t = values
        assumed = True
    elif c is None or t is None:
        rest = [v for v in values if v not in (c, t)]
        if len(rest) != 1:
            raise ValueError(f"Please give both control_label and treatment_label. Values: {values}")
        c, t, assumed = (c, rest[0], True) if c is not None else (rest[0], t, True)
    if c == t:
        raise ValueError("control_label and treatment_label must be different.")
    return c, t, assumed


def _wilson(k, n, alpha=0.05):
    lo, hi = proportion_confint(k, n, alpha=alpha, method="wilson")
    return float(lo), float(hi)


def _mde_80(metric_type, n_c, n_t, base, sd, alpha):
    """Smallest true lift this test could detect 80% of the time."""
    ratio = n_t / n_c
    if metric_type == "binary":
        h = NormalIndPower().solve_power(nobs1=n_c, alpha=alpha, power=0.8, ratio=ratio)
        p_t = np.sin(np.arcsin(np.sqrt(base)) + h / 2) ** 2 if base < 1 else base
        return float(p_t - base)
    d = TTestIndPower().solve_power(nobs1=n_c, alpha=alpha, power=0.8, ratio=ratio)
    return float(d * sd)


def _fmt(x, binary):
    return f"{x * 100:.2f}%" if binary else f"{x:,.3f}"


# ----------------------------------------------------------------- main
def analyze_ab(df: pd.DataFrame, group_col: str, metric_col: str,
               control_label=None, treatment_label=None, metric_type: str = "auto",
               pre_metric_col: str | None = None, expected_treat_share: float = 0.5,
               alpha: float = 0.05) -> dict:
    _need(df, group_col, metric_col, pre_metric_col)
    if group_col == metric_col:
        raise ValueError("The group column and the metric column must be different.")
    if metric_type not in ("auto", "binary", "continuous"):
        raise ValueError("metric_type must be 'auto', 'binary' or 'continuous'.")
    if not 0 < alpha < 1 or not 0 < expected_treat_share < 1:
        raise ValueError("alpha and expected_treat_share must be between 0 and 1.")

    warnings = []
    rows_total = len(df)
    df = df[df[group_col].notna()].copy()
    g = df[group_col].astype(str)
    ctrl, trt, assumed = _pick_labels(g, control_label, treatment_label)
    if assumed:
        warnings.append({"level": "info", "message":
                         f"I assumed '{ctrl}' is the control and '{trt}' is the treatment. "
                         "Set control_label / treatment_label if that's backwards."})
    df = df[g.isin([ctrl, trt])].copy()
    df["_is_treat"] = (df[group_col].astype(str) == trt).astype(int)

    n_c, n_t = int((df._is_treat == 0).sum()), int((df._is_treat == 1).sum())
    if min(n_c, n_t) < MIN_PER_GROUP:
        raise ValueError(f"Need at least {MIN_PER_GROUP} rows per group (got {n_c} and {n_t}).")

    # ---- Doctor check 1: sample ratio mismatch (uses ALL assigned rows)
    srm = srm_check(n_c, n_t, expected_treat_share)

    # ---- metric cleaning
    raw_metric = df[metric_col]
    metric = pd.to_numeric(raw_metric, errors="coerce")
    if metric.notna().sum() < 0.5 * raw_metric.notna().sum():
        raise ValueError(f"Column '{metric_col}' is not numeric. Use 0/1 for conversions or numbers for amounts.")
    df["_y"] = metric
    miss_c = float(df.loc[df._is_treat == 0, "_y"].isna().mean())
    miss_t = float(df.loc[df._is_treat == 1, "_y"].isna().mean())
    missing = {"control_pct": round(miss_c * 100, 2), "treatment_pct": round(miss_t * 100, 2)}
    if max(miss_c, miss_t) > 0.05 or abs(miss_c - miss_t) > 0.02:
        warnings.append({"level": "warning", "message":
                         f"Missing metric values: {missing['control_pct']}% in control vs "
                         f"{missing['treatment_pct']}% in treatment. If users drop out differently "
                         "in each group, the comparison can be biased."})
    df = df[df._y.notna()].copy()

    values = set(df._y.unique())
    is_binary = values <= {0, 1, 0.0, 1.0}
    if metric_type == "binary" and not is_binary:
        raise ValueError("metric_type='binary' needs a column of only 0/1 values.")
    mtype = metric_type if metric_type != "auto" else ("binary" if is_binary else "continuous")
    binary = mtype == "binary"

    y_c, y_t = df.loc[df._is_treat == 0, "_y"], df.loc[df._is_treat == 1, "_y"]
    if min(len(y_c), len(y_t)) < MIN_PER_GROUP:
        raise ValueError("Too many missing metric values: fewer than 30 usable rows in a group.")

    # ---- Doctor checks 2-4: pre-experiment balance, heavy tails, CUPED
    pre_balance, tails, cuped_info, robustness = None, None, None, None
    use_cuped = False
    if pre_metric_col is not None:
        if binary:
            warnings.append({"level": "info", "message": "CUPED is only used for continuous metrics; ignoring the pre-experiment column."})
        else:
            df["_x"] = pd.to_numeric(df[pre_metric_col], errors="coerce")
            before = len(df)
            df = df[df._x.notna()].copy()
            if len(df) < before:
                warnings.append({"level": "info", "message": f"Dropped {before - len(df)} rows with no pre-experiment value (needed for CUPED)."})
            xc, xt = df.loc[df._is_treat == 0, "_x"], df.loc[df._is_treat == 1, "_x"]
            if min(len(xc), len(xt)) < MIN_PER_GROUP:
                raise ValueError("Too few rows with a pre-experiment value.")
            p_pre = float(stats.ttest_ind(xt, xc, equal_var=False).pvalue)
            pre_balance = {"control_mean": float(xc.mean()), "treatment_mean": float(xt.mean()),
                           "p_value": p_pre, "balanced": bool(p_pre > 0.01)}
            if p_pre <= 0.01:
                warnings.append({"level": "warning", "message":
                                 "The groups already differed BEFORE the experiment on the pre-experiment metric "
                                 f"(p = {p_pre:.4f}). Randomization may be broken."})
            use_cuped = True
            y_c, y_t = df.loc[df._is_treat == 0, "_y"], df.loc[df._is_treat == 1, "_y"]

    if not binary:
        pooled = df["_y"].values
        p99, p999, mx = np.percentile(pooled, 99), np.percentile(pooled, 99.9), pooled.max()
        if p99 > 0 and mx > 20 * p99:
            tails = {"max": float(mx), "p99": float(p99), "capped_at": float(p999)}
            warnings.append({"level": "warning", "message":
                             f"Extreme values: the largest value ({mx:,.0f}) is over 20x the 99th percentile "
                             f"({p99:,.0f}). A few users can dominate an average, so I also ran a check with "
                             f"values capped at the 99.9th percentile ({p999:,.0f})."})

    # ---- primary analysis
    if binary:
        k_c, k_t = int(y_c.sum()), int(y_t.sum())
        test = compare_proportions(k_c, len(y_c), k_t, len(y_t), alpha)
        bayes = bayesian_ab_analytic(k_c, len(y_c), k_t, len(y_t))
        effect, ci, p_val = test["abs_lift"], test["ci"], test["p_value"]
        base = test["rate_control"]
        rel = test["rel_lift"]
        lo_c, hi_c = _wilson(k_c, len(y_c), alpha)
        lo_t, hi_t = _wilson(k_t, len(y_t), alpha)
        groups = [{"group": ctrl, "value": test["rate_control"], "ci_low": lo_c, "ci_high": hi_c, "n": len(y_c)},
                  {"group": trt, "value": test["rate_treatment"], "ci_low": lo_t, "ci_high": hi_t, "n": len(y_t)}]
        prob_b, expected_loss = bayes["prob_b_beats_a"], bayes["expected_loss_choose_b"]
        sd = None
        method = "chi-square test on conversion rates"
    else:
        tmp = df.assign(group=df._is_treat)
        raw = compare_means(tmp, "_y", "group")
        base = float(y_c.mean())
        sd = float(df["_y"].std())
        if use_cuped:
            tmp["_adj"] = cuped_adjust(tmp, "_y", "_x")
            adj = compare_means(tmp, "_adj", "group")
            red = 1 - (adj["se"] / raw["se"]) ** 2
            cuped_info = {"variance_reduction_pct": round(float(red * 100), 1),
                          "raw_effect": raw["effect"], "raw_p_value": raw["p_value"],
                          "adjusted_effect": adj["effect"], "adjusted_p_value": adj["p_value"]}
            res, method = adj, "Welch t-test on CUPED-adjusted values"
        else:
            res, method = raw, "Welch t-test on means"
        effect, ci, p_val = res["effect"], res["ci_95"], res["p_value"]
        rel = effect / base if base != 0 else None
        groups = []
        for lab, ys in ((ctrl, y_c), (trt, y_t)):
            se = ys.std(ddof=1) / np.sqrt(len(ys))
            groups.append({"group": lab, "value": float(ys.mean()), "ci_low": float(ys.mean() - 1.96 * se),
                           "ci_high": float(ys.mean() + 1.96 * se), "n": int(len(ys))})
        prob_b = expected_loss = None
        if tails:
            cap = tails["capped_at"]
            capped = tmp.assign(_c=tmp["_y"].clip(upper=cap))
            rc = compare_means(capped, "_c", "group")
            robustness = {"description": f"values capped at {cap:,.0f}", "effect": rc["effect"],
                          "p_value": rc["p_value"], "significant": bool(rc["p_value"] < alpha)}
            if (rc["p_value"] < alpha) != (p_val < alpha):
                warnings.append({"level": "warning", "message":
                                 "The conclusion CHANGES when extreme values are capped. "
                                 "The result depends on a handful of unusual users."})

    significant = bool(p_val < alpha)
    mde = _mde_80(mtype, len(y_c), len(y_t), base, sd, alpha)

    # ---- verdict
    b = binary
    unit = "percentage points" if b else ""
    eff_txt = f"{effect * 100:+.2f} {unit}" if b else f"{effect:+,.3f}"
    ci_txt = (f"{ci[0] * 100:+.2f} to {ci[1] * 100:+.2f} points" if b else f"{ci[0]:+,.3f} to {ci[1]:+,.3f}")
    rel_txt = f" ({rel * 100:+.1f}%)" if rel is not None else ""
    what = "conversion rate" if b else f"'{metric_col}'"
    details = [f"Control ({ctrl}): {_fmt(groups[0]['value'], b)} across {groups[0]['n']:,} users. "
               f"Treatment ({trt}): {_fmt(groups[1]['value'], b)} across {groups[1]['n']:,} users.",
               f"Estimated change in {what}: {eff_txt}{rel_txt}. 95% confidence range: {ci_txt}.",
               f"Method: {method}; p-value = {p_val:.4f}."]
    if prob_b is not None:
        details.append(f"Bayesian view: {prob_b * 100:.1f}% probability that {trt} is better than {ctrl}.")
    if cuped_info:
        details.append(f"CUPED removed about {cuped_info['variance_reduction_pct']}% of the noise, "
                       "so the same data gives a sharper answer.")

    if srm["srm_detected"]:
        status = "do_not_trust"
        headline = ("Do not trust this result: the group sizes don't match the plan "
                    f"(expected {expected_treat_share * 100:.0f}% in treatment, observed "
                    f"{srm['observed_treat_share'] * 100:.1f}%). Fix the assignment or logging problem first.")
        warnings.insert(0, {"level": "error", "message": srm["message"]})
    elif robustness is not None and robustness["significant"] != significant:
        status = "fragile"
        headline = (f"Unreliable result: the raw comparison says {eff_txt}{rel_txt} "
                    f"({'significant' if significant else 'not significant'}), but with extreme values "
                    f"capped ({robustness['description']}) it is "
                    f"{'significant' if robustness['significant'] else 'not significant'}. "
                    "A handful of unusual users are driving the answer.")
    elif significant:
        status = "significant_win" if effect > 0 else "significant_loss"
        headline = (f"{trt} {'increased' if effect > 0 else 'decreased'} {what} by {eff_txt}{rel_txt}. "
                    "This is statistically significant.")
    else:
        status = "inconclusive"
        headline = (f"No clear difference between {ctrl} and {trt} yet (observed {eff_txt}{rel_txt}, "
                    "not statistically significant).")
        details.append(f"With this many users the test could only reliably detect a change of about "
                       f"{_fmt(mde, b) if not b else f'{mde * 100:.2f} points'} or more (80% power). "
                       "A smaller real effect could still exist; 'not significant' is not 'no effect'.")

    return {
        "setup": {"control": ctrl, "treatment": trt, "metric_type": mtype, "metric": metric_col,
                  "rows_in_file": rows_total, "rows_used": int(len(df)),
                  "n_control": int(len(y_c)), "n_treatment": int(len(y_t))},
        "doctor": {"srm": srm, "missing_metric": missing, "pre_experiment_balance": pre_balance,
                   "extreme_values": tails, "min_detectable_change_80pct_power": mde},
        "result": {"effect": float(effect), "relative_effect": None if rel is None else float(rel),
                   "ci_95": [float(ci[0]), float(ci[1])], "p_value": float(p_val),
                   "significant": significant, "method": method,
                   "prob_treatment_better": prob_b, "expected_loss_choose_treatment": expected_loss},
        "cuped": cuped_info, "robustness": robustness,
        "charts": {"group_estimates": groups,
                   "lift": {"value": float(effect), "ci_low": float(ci[0]), "ci_high": float(ci[1])}},
        "warnings": warnings,
        "verdict": {"status": status, "headline": headline, "details": details},
    }