import { useState } from "react";
import { postForm } from "./api.js";
import { guessColumns } from "./guess.js";
import Verdict from "./Verdict.jsx";
import ResultCharts from "./ResultCharts.jsx";

// A dropdown listing the file's columns.
function ColumnSelect({ label, value, onChange, columns, optional }) {
  return (
    <label>
      {label}
      <select value={value} onChange={onChange}>
        {optional && <option value="">(none)</option>}
        {columns.map((c) => (
          <option key={c.name} value={c.name}>
            {c.name} ({c.n_unique} unique)
          </option>
        ))}
      </select>
    </label>
  );
}

export default function AnalyzeTab() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [form, setForm] = useState({
    group_col: "",
    metric_col: "",
    pre_metric_col: "",
    control_label: "",
    treatment_label: "",
    expected_treat_share: "0.5",
  });
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Returns a function that updates one field of the form.
  const setField = (name) => (event) =>
    setForm((old) => ({ ...old, [name]: event.target.value }));

  async function onFile(event) {
    const chosen = event.target.files[0];
    setFile(chosen || null);
    setPreview(null);
    setResult(null);
    setError("");
    if (!chosen) return;

    setLoading(true);
    try {
      const data = new FormData();
      data.append("file", chosen);
      const p = await postForm("/analyze/preview", data);
      const guess = guessColumns(p.columns);
      setPreview(p);
      setForm((old) => ({
        ...old,
        group_col: guess.group,
        metric_col: guess.metric,
        pre_metric_col: guess.pre,
      }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function onAnalyze() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = new FormData();
      data.append("file", file);
      // Only send fields that have a value; empty ones mean "let the backend decide".
      Object.entries(form).forEach(([name, value]) => {
        if (value !== "") data.append(name, value);
      });
      setResult(await postForm("/analyze/ab", data));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const columns = preview ? preview.columns : [];

  return (
    <div>
      <section className="card">
        <h2>1. Upload your experiment data</h2>
        <p className="muted">A CSV with one row per user: the group they were in, and the outcome you measured.</p>
        <input type="file" accept=".csv,text/csv" onChange={onFile} aria-label="CSV file" />
        {preview && (
          <p className="muted">
            {preview.n_rows.toLocaleString()} rows, {columns.length} columns
          </p>
        )}
      </section>

      {preview && (
        <section className="card">
          <h2>2. Tell me what the columns mean</h2>
          <div className="form">
            <ColumnSelect label="Group column (who saw what)" value={form.group_col} onChange={setField("group_col")} columns={columns} />
            <ColumnSelect label="Metric column (the outcome)" value={form.metric_col} onChange={setField("metric_col")} columns={columns} />
            <ColumnSelect label="Pre-experiment metric (optional, enables CUPED)" value={form.pre_metric_col} onChange={setField("pre_metric_col")} columns={columns} optional />
            <label>
              Control label (optional)
              <input value={form.control_label} onChange={setField("control_label")} placeholder="auto" />
            </label>
            <label>
              Treatment label (optional)
              <input value={form.treatment_label} onChange={setField("treatment_label")} placeholder="auto" />
            </label>
            <label>
              Planned share in treatment
              <input type="number" min="0.01" max="0.99" step="0.01" value={form.expected_treat_share} onChange={setField("expected_treat_share")} />
            </label>
          </div>
          <button className="primary" onClick={onAnalyze} disabled={loading}>
            {loading ? "Working\u2026" : "Analyze"}
          </button>
        </section>
      )}

      {error && <div className="error" role="alert">{error}</div>}
      {result && <Verdict data={result} />}
      {result && <ResultCharts data={result} />}
    </div>
  );
}