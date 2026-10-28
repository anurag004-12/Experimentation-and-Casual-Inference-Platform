// A tiny "forest plot": the estimated change with its 95% range, against zero (= no effect).
// Everything is drawn by hand as SVG, so no chart library is needed.
export default function LiftPlot({ value, lo, hi, binary }) {
  // Binary metrics are shown in percentage points, so multiply by 100.
  const k = binary ? 100 : 1;
  const unit = binary ? " pts" : "";
  const [v, l, h] = [value * k, lo * k, hi * k];

  // The visible range must include the whole interval AND zero, plus some padding.
  const min = Math.min(l, 0);
  const max = Math.max(h, 0);
  const pad = (max - min || 1) * 0.2;
  const [left, right] = [min - pad, max + pad];

  // Convert a data value into a horizontal pixel position (from 30 to 570).
  const x = (n) => 30 + ((n - left) / (right - left)) * 540;
  const fmt = (n) => `${n > 0 ? "+" : ""}${n.toFixed(binary ? 2 : 3)}${unit}`;

  return (
    <svg viewBox="0 0 600 90" role="img" aria-label="Estimated effect with 95% confidence range" className="liftplot">
      <line x1={x(0)} x2={x(0)} y1="10" y2="60" stroke="#888" strokeDasharray="4 4" />
      <text x={x(0)} y="76" textAnchor="middle" fontSize="12" fill="#666">no effect</text>
      <line x1={x(l)} x2={x(h)} y1="35" y2="35" stroke="#4f6df5" strokeWidth="4" />
      <line x1={x(l)} x2={x(l)} y1="27" y2="43" stroke="#4f6df5" strokeWidth="3" />
      <line x1={x(h)} x2={x(h)} y1="27" y2="43" stroke="#4f6df5" strokeWidth="3" />
      <circle cx={x(v)} cy="35" r="7" fill="#1b2a8a" />
      <text x={x(l)} y="20" textAnchor="middle" fontSize="12">{fmt(l)}</text>
      <text x={x(h)} y="20" textAnchor="middle" fontSize="12">{fmt(h)}</text>
    </svg>
  );
}