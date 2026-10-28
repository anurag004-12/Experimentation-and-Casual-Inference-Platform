// Guess which columns are the group, the metric and the pre-experiment metric,
// so most people only need to press "Analyze".
const GROUP_HINT = /(group|variant|arm|treat|segment|version|bucket|test|cohort)/i;
const METRIC_HINT = /(conver|retention|spend|revenue|metric|outcome|click|purchase|visit|sales)/i;
const PRE_HINT = /(^|_)(pre|before|baseline|prior)(_|$)/i;

export function guessColumns(columns) {
  const names = columns.map((c) => c.name);

  // Group: a column that "sounds like" a group and has only a few distinct values.
  const groupCol =
    columns.find((c) => GROUP_HINT.test(c.name) && c.n_unique >= 2 && c.n_unique <= 6) ||
    columns.find((c) => c.n_unique >= 2 && c.n_unique <= 3);
  const group = groupCol ? groupCol.name : names[0];

  // Pre-experiment metric: a column named like "pre_spend" or "baseline_x".
  const preCol = columns.find((c) => c.name !== group && PRE_HINT.test(c.name));
  const pre = preCol ? preCol.name : "";

  // Metric: sounds like an outcome, and is not the group or the pre-experiment column.
  const metricCol = columns.find(
    (c) => c.name !== group && c.name !== pre && METRIC_HINT.test(c.name)
  );
  const rest = names.filter((n) => n !== group && n !== pre);
  const metric = metricCol ? metricCol.name : rest[rest.length - 1] || names[0];

  return { group, metric, pre };
}