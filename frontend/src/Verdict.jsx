// How each verdict status from the backend should look.
const STATUS = {
  significant_win: { label: "Significant win", cls: "good" },
  significant_loss: { label: "Significant loss", cls: "bad" },
  inconclusive: { label: "Inconclusive", cls: "neutral" },
  do_not_trust: { label: "Do not trust this result", cls: "bad" },
  fragile: { label: "Unreliable result", cls: "warn" },
};

export default function Verdict({ data }) {
  const status = STATUS[data.verdict.status] || STATUS.inconclusive;
  return (
    <>
      <div className={`verdict ${status.cls}`}>
        <span className="badge">{status.label}</span>
        <p className="headline">{data.verdict.headline}</p>
        <ul>
          {data.verdict.details.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>
      </div>

      {data.warnings.length > 0 && (
        <section className="card">
          <h3>Warnings</h3>
          <ul className="warnings">
            {data.warnings.map((w, i) => (
              <li key={i} className={w.level}>
                <strong>{w.level.toUpperCase()}</strong> {w.message}
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}