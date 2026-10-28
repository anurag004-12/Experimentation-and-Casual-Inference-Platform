"""Generate small CSV files to try the upload endpoint with.
Run from the backend folder:  python scripts/make_sample_data.py
Files are written to backend/sample_data/ (git-ignored)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.experiments import simulate_experiment  # noqa: E402

out = Path(__file__).resolve().parents[1] / "sample_data"
out.mkdir(exist_ok=True)
rng = np.random.default_rng(0)

# 1) Conversion test: A converts at 10%, B at 12% (a real +2 point lift)
n = 20_000
b = rng.random(n) < 0.5
pd.DataFrame({"user_id": range(n), "variant": np.where(b, "B", "A"),
              "converted": (rng.random(n) < np.where(b, 0.12, 0.10)).astype(int)}
             ).to_csv(out / "ab_binary.csv", index=False)

# 2) Spend test with a pre-experiment column (CUPED helps here). True effect = +0.5
d = simulate_experiment(n_users=20_000, true_effect=0.5, seed=1)
d["arm"] = np.where(d.group == 1, "treatment", "control")
d[["user_id", "arm", "pre_metric", "metric"]].rename(
    columns={"pre_metric": "pre_spend", "metric": "spend"}).to_csv(out / "ab_continuous.csv", index=False)

# 3) Broken test: 15% of treatment users silently lost (sample ratio mismatch)
s = simulate_experiment(n_users=20_000, true_effect=0.5, seed=1, srm_bug=0.15)
s["arm"] = np.where(s.group == 1, "treatment", "control")
s[["user_id", "arm", "metric"]].rename(columns={"metric": "spend"}).to_csv(out / "ab_srm_bug.csv", index=False)

# 4) Trap: NO real effect, but five whales in treatment make it look like a huge win
h = simulate_experiment(n_users=20_000, true_effect=0.0, seed=2)
h["arm"] = np.where(h.group == 1, "treatment", "control")
h.loc[h.index[h.group == 1][:5], "metric"] = 60_000
h[["user_id", "arm", "metric"]].rename(columns={"metric": "spend"}).to_csv(out / "ab_heavy_tail.csv", index=False)

print("Wrote:", *sorted(p.name for p in out.glob("*.csv")), sep="\n  ")