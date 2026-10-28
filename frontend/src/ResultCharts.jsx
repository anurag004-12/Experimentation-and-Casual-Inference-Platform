import GroupChart from "./components/GroupChart.jsx";
import LiftPlot from "./components/LiftPlot.jsx";

export default function ResultCharts({ data }) {
  const binary = data.setup.metric_type === "binary";
  const lift = data.charts.lift;
  return (
    <div className="grid2">
      <section className="card">
        <h3>{binary ? "Conversion rate (%)" : `Average ${data.setup.metric}`} by group</h3>
        <GroupChart groups={data.charts.group_estimates} binary={binary} />
        <p className="muted">Black whiskers show the 95% range for each group.</p>
      </section>

      <section className="card">
        <h3>Estimated change (95% range)</h3>
        <LiftPlot value={lift.value} lo={lift.ci_low} hi={lift.ci_high} binary={binary} />
        <p className="muted">If the range crosses &ldquo;no effect&rdquo;, the data can&rsquo;t rule out zero.</p>
        {data.robustness && (
          <p className="muted">
            Check with extreme values capped ({data.robustness.description}):{" "}
            {data.robustness.significant ? "still significant" : "NOT significant"}.
          </p>
        )}
      </section>
    </div>
  );
}