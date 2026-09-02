import { useState } from "react";
import UploadPanel from "./components/UploadPanel";
import MetricTiles from "./components/MetricTiles";
import MatchesTable from "./components/MatchesTable";
import ExceptionsTable from "./components/ExceptionsTable";
import AuditTrail from "./components/AuditTrail";
import ConfidenceChart from "./components/ConfidenceChart";
import ExportButton from "./components/ExportButton";
import AccuracyTracker from "./components/AccuracyTracker";
import ROICalculator from "./components/ROICalculator";

const TABS = ["Matches", "Exceptions", "Audit Trail"];

export default function App() {
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [tab, setTab]         = useState("Matches");

  async function handleUpload(settlements, bank, params = {}) {
    setLoading(true);
    setError(null);
    setResult(null);

    const form = new FormData();
    form.append("settlements", settlements);
    form.append("bank_statement", bank);
    if (params.fee_rate             !== undefined) form.append("fee_rate",             params.fee_rate);
    if (params.date_window          !== undefined) form.append("date_window",          params.date_window);
    if (params.confidence_threshold !== undefined) form.append("confidence_threshold", params.confidence_threshold);

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
      if (e instanceof TypeError) {
        setError("Cannot reach the LedgerLens API server. Make sure it is running at http://localhost:8000.");
      } else {
        setError(e.message);
      }
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

            <AccuracyTracker stats={result.stats} />

            <ROICalculator stats={result.stats} />

            <ConfidenceChart
              matches={result.matches}
              exceptions={result.exceptions}
            />

            <div className="tab-bar-row">
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
                      : t === "Exceptions"
                      ? result.exceptions.length
                      : (result.audit_trail || []).length}
                  </span>
                </button>
              ))}
              </div>
              <ExportButton result={result} />
            </div>

            {tab === "Matches" && (
              <MatchesTable matches={result.matches} />
            )}
            {tab === "Exceptions" && (
              <ExceptionsTable exceptions={result.exceptions} />
            )}
            {tab === "Audit Trail" && (
              <AuditTrail entries={result.audit_trail || []} />
            )}
          </>
        )}
      </main>
    </div>
  );
}
