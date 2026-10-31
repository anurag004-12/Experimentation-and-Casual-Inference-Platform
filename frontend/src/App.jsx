import { useEffect, useState } from "react";
import AnalyzeTab from "./AnalyzeTab.jsx";
import ArenaTab from "./ArenaTab.jsx";
import "./styles.css";

export default function App() {
  const [status, setStatus] = useState("checking...");
  const [tab, setTab] = useState("analyze");

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

      <nav>
        <button className={tab === "analyze" ? "active" : ""} onClick={() => setTab("analyze")}>
          Analyze my A/B test
        </button>
        <button className={tab === "arena" ? "active" : ""} onClick={() => setTab("arena")}>
          Method arena
        </button>
      </nav>

      {/* Both tabs stay loaded, so switching doesn't lose an uploaded file. */}
      <div hidden={tab !== "analyze"}>
        <AnalyzeTab />
      </div>
      <div hidden={tab !== "arena"}>
        <ArenaTab />
      </div>
    </div>
  );
}