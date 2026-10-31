# Case study: Cookie Cats gate placement

**Question:** Does moving the first gate from level 30 to level 40 change player retention or engagement?

**Data:** 90,189 players of the mobile game Cookie Cats, randomly assigned to `gate_30`
(44,700 players) or `gate_40` (45,489 players). Source: Kaggle.

**Method:** Randomized A/B analysis using this platform's Experiment Doctor checks. Three
metrics were tested on the same players, so p-values were corrected with Benjamini-Hochberg
and Bonferroni (they agree).

## Results

| Metric | gate_30 | gate_40 | Change (95% range) | p-value | Adjusted p (BH / Bonferroni) | Verdict |
|---|---|---|---|---|---|---|
| retention_1 (returned after 1 day) | 44.82% | 44.23% | -0.59 pts (-1.24 to +0.06) | 0.0744 | 0.1116 / 0.2232 | Inconclusive |
| retention_7 (returned after 7 days) | 19.02% | 18.20% | -0.82 pts (-1.33 to -0.31) | 0.0016 | 0.0048 / 0.0048 | Significant loss |
| sum_gamerounds (rounds played) | 52.456 | 51.299 | -1.157 (-3.720 to +1.405) | 0.3759 | 0.3759 / 1.0 | Inconclusive |

## Doctor checks
- **Group sizes:** 49.6% / 50.4%. A sample-ratio test gives p = 0.0086, below the platform's
  strict alarm threshold (0.001), so no alarm, but slightly uneven.
- **Extreme values (sum_gamerounds):** the largest player played 49,854 rounds (in gate_30),
  against a 99th percentile of 493; the largest in gate_40 played 2,640. That one player
  adds about 1.1 rounds to gate_30's average. Without them, the group averages are 51.34
  and 51.30 (a gap of -0.04, against -1.16 with them), and the medians are 17 and 16 rounds.
  The check with values capped at 1,074 rounds also found no significant difference. The
  apparent -2.2% gap in average rounds is therefore almost entirely one player.

## Conclusion
After correcting for three metrics, moving the gate to level 40 **lowered 7-day retention**
by 0.82 percentage points (about 8 fewer returning players per 1,000; plausible range 3 to 13
per 1,000). Day-1 retention and total rounds played show no statistically significant
difference. On this evidence, **keep the gate at level 30**, if retention is the priority.

## What this does and does not show
- Because players were randomly assigned, the retention difference can be attributed to the
  gate placement. This analysis cannot say **why**.
- "Not significant" for day-1 retention and rounds is not "no effect": the day-1 test could
  only reliably detect changes of about 0.93 points or more.
- Revenue and player satisfaction were not measured, so a benefit of the later gate
  there would not show up here.
- The averages of `sum_gamerounds` are dominated by a few extreme players.
- This is one experiment on one game.
- For heavy-tailed metrics like rounds played, compare medians or use a bootstrap instead of
  relying on averages. A planned improvement for the platform.