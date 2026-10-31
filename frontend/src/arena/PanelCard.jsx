import { useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { postJson } from "../api.js";
import Slider from "../components/Slider.jsx";

// One row per time period, with the real unit and its synthetic twin side by side.
export function toSeries(d) {
  const sc = d.synthetic_control;
  return sc.time.map((t, i) => ({
    time: t,
    "Real unit": Number(sc.treated_series[i].toFixed(2)),
    "Synthetic twin": Number(sc.synthetic_series[i].toFixed(2)),
  }));
}

// What the parallel-trends check said, in words.
export function trendsText(did) {
  if (did.parallel_trends_ok === null || did.parallel_trends_ok === undefined) return "cannot be tested";
  return did.parallel_trends_ok ? "passed" : "FAILED";
}

// One plain-English paragraph that fits whichever scenario was run.
export function describe(d) {
  const f = (x) => x.toFixed(2);
  const did = d.did;
  const sc = d.synthetic_control;
  const flagged = did.parallel_trends_ok === false;

  if (d.true_effect === 0) {
    return (
      `There is no real policy effect (the true value is 0). Difference-in-differences reports ${f(did.effect)}` +
      `${Math.abs(did.effect) > 1 ? ", an effect that does not exist" : ""}${flagged ? ", and its own parallel-trends check flags the problem" : ""}. ` +
      `Synthetic control reports ${f(sc.effect)} (placebo p-value ${sc.placebo_p_value.toFixed(2)}).`
    );
  }
  if (d.loading_spread === 0) {
    return (
      `All units react to the shared trend in the same way, so "parallel trends" holds and both methods land near the true ` +
      `effect of ${d.true_effect} (difference-in-differences ${f(did.effect)}, synthetic control ${f(sc.effect)}).`
    );
  }
  return (
    `Units react differently to the shared trend, so "parallel trends" is violated. Difference-in-differences reports ` +
    `${f(did.effect)} (true effect ${d.true_effect}); its pre-trend check ${trendsText(did) === "FAILED" ? "flags the problem" : trendsText(did)}. ` +
    `Synthetic control builds its comparison from a weighted mix of similar units and reports ${f(sc.effect)}.`
  );
}

export default function PanelCard() {
  const [spread, setSpread] = useState(1);
  const [trueEffect, setTrueEffect] = useState(-3);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    setError("");
    try {
      setResult(await postJson("/causal/panel-compare", { true_effect: trueEffect, loading_spread: spread }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const did = result && result.did;
  const sc = result && result.synthetic_control;
  return (
    <section className="card">
      <h2>What if a policy hit just one place?</h2>
      <p className="muted">
        One unit (say, one state) gets a policy and about 30 others do not. We know the true effect, so we can check
        which method finds it.
      </p>
      <div className="form">
        <Slider label="How differently units react to trends" value={spread} min={0} max={2} step={0.5} onChange={setSpread}
          note={'0 = "parallel trends" holds. 1 or more = it is violated.'} />
        <Slider label="True policy effect" value={trueEffect} min={-6} max={6} step={1} onChange={setTrueEffect}
          note="Set to 0 to see which method invents an effect." />
      </div>
      <button className="primary" onClick={run} disabled={busy}>{busy ? "Running\u2026" : "Compare methods"}</button>

      {error && <div className="error" role="alert">{error}</div>}
      {result && (
        <>
          <h3>The real unit and its synthetic twin. The grey dashed line is when the policy started.</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={toSeries(result)} margin={{ top: 16, right: 16, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" interval={4} />
              <YAxis domain={["auto", "auto"]} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="Real unit" stroke="#d73027" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="Synthetic twin" stroke="#4f6df5" strokeWidth={2} strokeDasharray="5 3" dot={false} />
              <ReferenceLine x={result.treatment_time} stroke="#888" strokeDasharray="5 5" />
            </LineChart>
          </ResponsiveContainer>
          <p className="muted">
            Before the dashed line the twin tracks the real unit closely (that is how it is built). The gap after it is the
            estimated effect.
          </p>
          <div className="grid2">
            <div className={`mini ${Math.abs(did.error_vs_truth) > 1 ? "bad" : "good"}`}>
              <h4>Difference-in-differences</h4>
              <p>Estimate: <strong>{did.effect.toFixed(2)}</strong> (true {result.true_effect}; error {did.error_vs_truth > 0 ? "+" : ""}{did.error_vs_truth.toFixed(2)})</p>
              <p>Parallel-trends check: <strong>{trendsText(did)}</strong></p>
            </div>
            <div className={`mini ${Math.abs(sc.error_vs_truth) > 1 ? "bad" : "good"}`}>
              <h4>Synthetic control</h4>
              <p>Estimate: <strong>{sc.effect.toFixed(2)}</strong> (true {result.true_effect}; error {sc.error_vs_truth > 0 ? "+" : ""}{sc.error_vs_truth.toFixed(2)})</p>
              <p>Placebo p-value: <strong>{sc.placebo_p_value.toFixed(3)}</strong></p>
            </div>
          </div>
          <p className="takeaway">{describe(result)}</p>
        </>
      )}
    </section>
  );
}