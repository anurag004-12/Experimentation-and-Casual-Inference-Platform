import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { postJson } from "../api.js";
import Slider from "../components/Slider.jsx";

const pct = (x) => `${(x * 100).toFixed(1)}%`;

// Turn the simulation numbers into one plain-English paragraph.
export function describe(r) {
  if (r.true_effect === 0) {
    return (
      `With no real difference, looking once gives a false win ${pct(r.fixed_horizon)} of the time (the planned 5%). ` +
      `Checking ${r.n_looks} times and stopping the first time p < 0.05 gives a false win ${pct(r.naive_peeking)} of the time. ` +
      `The safe method gives ${pct(r.sequential)}.`
    );
  }
  return (
    `There is a real effect. Looking once finds it ${pct(r.fixed_horizon)} of the time; the safe method finds it ` +
    `${pct(r.sequential)} of the time, stopping after an average of ${Math.round(r.sequential_avg_users_per_group).toLocaleString()} ` +
    `of ${r.max_users_per_group.toLocaleString()} users per group. Peeking "finds" it ${pct(r.naive_peeking)} of the time, ` +
    `but remember it also produces false wins when there is no effect.`
  );
}

export function toBars(r) {
  return [
    { name: "Look once, at the end", value: r.fixed_horizon * 100 },
    { name: "Stop the first time p < 0.05", value: r.naive_peeking * 100 },
    { name: "Safe method", value: r.sequential * 100 },
  ];
}

export default function PeekingCard() {
  const [nLooks, setNLooks] = useState(10);
  const [trueEffect, setTrueEffect] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    setError("");
    try {
      setResult(await postJson("/sequential/peeking-demo", { true_effect: trueEffect, n_looks: nLooks }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const noEffect = result && result.true_effect === 0;
  return (
    <section className="card">
      <h2>Can I peek at results early?</h2>
      <p className="muted">
        Thousands of simulated experiments, checked several times along the way. Set the true effect to 0 to see how
        often checking early creates a fake win.
      </p>
      <div className="form">
        <Slider label="How many times do you check?" value={nLooks} min={2} max={30} step={1} onChange={setNLooks} />
        <Slider label="True effect" value={trueEffect} min={0} max={0.1} step={0.01} onChange={setTrueEffect}
          note="0 means nothing is really different" />
      </div>
      <button className="primary" onClick={run} disabled={busy}>{busy ? "Running\u2026" : "Run simulation"}</button>

      {error && <div className="error" role="alert">{error}</div>}
      {result && (
        <>
          <h3>{noEffect ? "How often each strategy declares a fake win (%). The green dashed line is the 5% you planned for." : "How often each strategy finds the real effect (%)"}</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={toBars(result)} margin={{ top: 16, right: 16, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" interval={0} tick={{ fontSize: 12 }} />
              <YAxis domain={noEffect ? [0, 40] : [0, 100]} />
              <Tooltip formatter={(v) => `${v.toFixed(1)}%`} />
              {noEffect && <ReferenceLine y={5} stroke="#1a9850" strokeDasharray="6 3" />}
              <Bar dataKey="value">
                {toBars(result).map((b, i) => (
                  <Cell key={b.name} fill={noEffect && i === 1 ? "#d73027" : "#4f6df5"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="takeaway">{describe(result)}</p>
        </>
      )}
    </section>
  );
}