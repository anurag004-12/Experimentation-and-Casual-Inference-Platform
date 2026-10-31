// A labelled slider. Calls onChange with a NUMBER (not text).
export default function Slider({ label, value, onChange, min, max, step, note }) {
  return (
    <label className="slider">
      <span>
        {label}: <strong>{value}</strong>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      {note && <small className="muted">{note}</small>}
    </label>
  );
}