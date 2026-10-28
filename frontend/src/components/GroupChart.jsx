import { Bar, BarChart, CartesianGrid, ErrorBar, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

// Turn the backend's numbers into what the chart needs.
// Each bar needs a height (value) and how far the whiskers reach below and above it (err).
export function toBars(groups, binary) {
  const k = binary ? 100 : 1; // show conversion rates as percentages
  return groups.map((g) => ({
    name: g.group,
    value: g.value * k,
    err: [(g.value - g.ci_low) * k, (g.ci_high - g.value) * k],
  }));
}

export default function GroupChart({ groups, binary }) {
  const bars = toBars(groups, binary);
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={bars} margin={{ top: 16, right: 16, bottom: 4, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis domain={[0, "auto"]} />
        <Tooltip formatter={(v) => (typeof v === "number" ? v.toFixed(3) : v)} />
        <Bar dataKey="value" fill="#4f6df5">
          <ErrorBar dataKey="err" width={8} strokeWidth={2} stroke="#222" />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}