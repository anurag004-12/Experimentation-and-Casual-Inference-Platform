import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { postJson } from "../api.js";
import Slider from "../components/Slider.jsx";

// Short labels so the chart axis stays readable. The table below the chart uses the full names.
const SHORT = {
  "naive difference": "Naive",
  "regression adjustment": "Regression",
  "propensity matching": "Matching",
};

// One bar per method. A bar turns red when it misses the true effect by more than 0.5.
export function toBars(d) {
  return d.results.map((r) => ({
    name: SHORT[r.method] || r.method.replace(/ \(.*\)/, ""), // "DoWhy (propensity stratification)" -> "DoWhy"
    value: Number(r.effect.toFixed(2)),
    off: Math.abs(r.error_vs_truth) > 0.5,
  }));
}

// One plain-English paragraph that fits whichever scenario was run.
export function describe(d) {
  const naive = d.results.find((r) => r.method === "naive difference");
  const careful = d.results.filter((r) => r.method !== "naive difference");
  const lo = Math.min(...careful.map((r) => r.effect));
  const hi = Math.max(...careful.map((r) => r.effect));
  const f = (x) => x.toFixed(2);

  if (d.hidden_confounding > 0) {
    return (
      `The true effect is ${d.true_effect}. The careful methods adjust for everything that was measured, but an important ` +
      `driver was NOT measured, so they still land at ${f(lo)} to ${f(hi)}. No method can correct for what the data does ` +
      `not contain. That is why randomizing matters.`
    );
  }
  if (d.confounding === 0) {
    return (
      `Nobody was choosing the treatment based on their own traits, so even the naive comparison is close to the truth ` +
      `(${f(naive.effect)} vs ${d.true_effect}). Random assignment is what makes the simple comparison valid.`
    );
  }
  return (
    `The true effect is ${d.true_effect}. The naive comparison says ${f(naive.effect)}, because the people who opted in were ` +
    `already different. The careful methods adjust for that and land at ${f(lo)} to ${f(hi)}.`
  );
}

export default function ObservationalCard() {
  const [confounding, setConfounding] = useState(1);
  const [hidden, setHidden] = useState(0);
  const [useDowhy, setUseDowhy] = useState(false);
  const [useEconml, setUseEconml] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    setError("");
    try {
      setResult(
        await postJson("/causal/compare", {
          n: 5000,
          true_effect: 2,
          confounding,
          hidden_confounding: hidden,
          use_dowhy: useDowhy,
          use_econml: useEconml,
        })
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <h2>What if people choose the treatment themselves?</h2>
      <p className="muted">
        Users who opt in to a feature were already different (more active, longer-tenured). The true effect of the
        feature is +2.0. Which methods get it right?
      </p>
      <div className="form">
        <Slider label="How strongly users self-select" value={confounding} min={0} max={3} step={0.5} onChange={setConfounding}
          note="0 = random assignment" />
        <Slider label="Strength of a hidden driver" value={hidden} min={0} max={2} step={0.5} onChange={setHidden}
          note="An unmeasured factor that affects both opting in and the outcome. Try 1." />
        <label className="check">
          <input type="checkbox" checked={useDowhy} onChange={(e) => setUseDowhy(e.target.checked)} />
          Include DoWhy (a few seconds)
        </label>
        <label className="check">
          <input type="checkbox" checked={useEconml} onChange={(e) => setUseEconml(e.target.checked)} />
          Include EconML (can take a minute)
        </label>
      </div>
      <button className="primary" onClick={run} disabled={busy}>{busy ? "Running\u2026" : "Run methods"}</button>

      {error && <div className="error" role="alert">{error}</div>}
      {result && (
        <>
          <h3>Each method's estimate. The green dashed line is the true effect ({result.true_effect}); red bars miss it.</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={toBars(result)} margin={{ top: 16, right: 16, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" interval={0} tick={{ fontSize: 12 }} />
              <YAxis domain={[0, "auto"]} />
              <Tooltip />
              <Bar dataKey="value">
                {toBars(result).map((b) => (
                  <Cell key={b.name} fill={b.off ? "#d73027" : "#4f6df5"} />
                ))}
              </Bar>
              <ReferenceLine y={result.true_effect} stroke="#1a9850" strokeWidth={2} strokeDasharray="6 3" />
            </BarChart>
          </ResponsiveContainer>
          <table>
            <thead>
              <tr><th>Method</th><th>Estimate</th><th>Error vs truth</th></tr>
            </thead>
            <tbody>
              {result.results.map((r) => (
                <tr key={r.method}>
                  <td>{r.method}</td>
                  <td>{r.effect.toFixed(2)}</td>
                  <td>{r.error_vs_truth > 0 ? "+" : ""}{r.error_vs_truth.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="takeaway">{describe(result)}</p>
        </>
      )}
    </section>
  );
}