import { useState } from "react";
import UploadPanel from "./components/UploadPanel";
import MetricTiles from "./components/MetricTiles";
import MatchesTable from "./components/MatchesTable";
import ExceptionsTable from "./components/ExceptionsTable";

const TABS = ["Matches", "Exceptions"];

export default function App() {
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [tab, setTab]         = useState("Matches");

  async function handleUpload(settlements, bank) {
    setLoading(true);
    setError(null);
    setResult(null);

    const form = new FormData();
    form.append("settlements", settlements);
    form.append("bank_statement", bank);

    try {
      const res = await fetch("http://localhost:8000/reconcile", {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Server error " + res.status);
      }
      setResult(await res.json());
      setTab("Matches");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header>
        <div className="header-inner">
          <span className="logo">LedgerLens</span>
          <span className="subtitle">AI Reconciliation Controller · Track 4</span>
        </div>
      </header>

      <main>
        <UploadPanel onSubmit={handleUpload} loading={loading} />

        {error && (
          <div className="error-banner">
            <strong>Error:</strong> {error}
          </div>
        )}

        {loading && (
          <div className="loading-card">
            <div className="spinner" />
            <div>
              <p className="loading-title">Running reconciliation pipeline…</p>
              <p className="loading-sub">Rules → Batch detector → AI agent</p>
            </div>
          </div>
        )}

        {result && !loading && (
          <>
            <MetricTiles stats={result.stats} />

            <div className="tab-bar">
              {TABS.map((t) => (
                <button
                  key={t}
                  className={"tab-btn" + (tab === t ? " active" : "")}
                  onClick={() => setTab(t)}
                >
                  {t}
                  <span className="tab-count">
                    {t === "Matches"
                      ? result.matches.length
                      : result.exceptions.length}
                  </span>
                </button>
              ))}
            </div>

            {tab === "Matches" && (
              <MatchesTable matches={result.matches} />
            )}
            {tab === "Exceptions" && (
              <ExceptionsTable exceptions={result.exceptions} />
            )}
          </>
        )}
      </main>
    </div>
  );
}
