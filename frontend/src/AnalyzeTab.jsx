import { useState } from "react";
import { postForm } from "./api.js";

export default function AnalyzeTab() {
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onFile(event) {
    const file = event.target.files[0];
    setPreview(null);
    setError("");
    if (!file) return;

    setLoading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      setPreview(await postForm("/analyze/preview", form));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card">
      <h2>1. Upload your experiment data</h2>
      <p className="muted">A CSV with one row per user: the group they were in, and the outcome you measured.</p>
      <input type="file" accept=".csv,text/csv" onChange={onFile} aria-label="CSV file" />

      {loading && <p>Reading file&hellip;</p>}
      {error && <div className="error" role="alert">{error}</div>}

      {preview && (
        <>
          <p>
            <strong>{preview.n_rows.toLocaleString()}</strong> rows,{" "}
            <strong>{preview.columns.length}</strong> columns
          </p>
          <table>
            <thead>
              <tr>
                <th>Column</th>
                <th>Type</th>
                <th>Unique values</th>
                <th>Missing %</th>
                <th>Examples</th>
              </tr>
            </thead>
            <tbody>
              {preview.columns.map((c) => (
                <tr key={c.name}>
                  <td>{c.name}</td>
                  <td>{c.dtype}</td>
                  <td>{c.n_unique.toLocaleString()}</td>
                  <td>{c.missing_pct}</td>
                  <td>{c.examples.join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}