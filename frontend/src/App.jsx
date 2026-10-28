import { useEffect, useState } from "react";
import AnalyzeTab from "./AnalyzeTab.jsx";
import "./styles.css";

export default function App() {
  const [status, setStatus] = useState("checking...");

  useEffect(() => {
    fetch("/api/health")
      .then((res) => res.json())
      .then((data) => setStatus(data.status))
      .catch(() => setStatus("could not reach the backend"));
  }, []);

  return (
    <div className="app">
      <h1>Experimentation &amp; Causal Inference Platform</h1>
      <p className="muted">
        Backend status: <strong>{status}</strong>
      </p>
      <AnalyzeTab />
    </div>
  );
}