const STAGE_COLORS = {
  "Stage 1 — Rules":   "stage-rules",
  "Stage 1.5 — Batch": "stage-batch",
  "Stage 2 — AI":      "stage-ai",
};

const STRATEGY_CHIP = {
  REF:        "chip-blue",
  "AMT+DATE": "chip-blue",
  BATCH:      "chip-blue",
  AI:         "chip-blue",
};

export default function AuditTrail({ entries }) {
  if (!entries || entries.length === 0) {
    return (
      <div className="empty-state">
        <p>No audit data available. Run a reconciliation first.</p>
      </div>
    );
  }

  const matched    = entries.filter((e) => e.decision === "MATCHED").length;
  const exceptions = entries.filter((e) => e.decision === "EXCEPTION").length;

  return (
    <div className="audit-wrap">
      <div className="audit-header">
        <div className="audit-summary">
          <span className="audit-badge audit-badge-matched">{matched} matched</span>
          <span className="audit-badge audit-badge-exception">{exceptions} exceptions</span>
        </div>
        <span className="audit-note">Every decision made by the pipeline — in order</span>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Settlement</th>
              <th>Bank Entry</th>
              <th>Stage</th>
              <th>Strategy</th>
              <th>Decision</th>
              <th>Confidence</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e, i) => (
              <tr key={i} className={e.decision === "EXCEPTION" ? "audit-exception-row" : ""}>
                <td className="mono audit-ts">{e.ts}</td>
                <td className="mono">{e.settlement_id}</td>
                <td className="mono">{e.bank_txn_id || <span className="muted-dash">—</span>}</td>
                <td>
                  <span className={"stage-pill " + (STAGE_COLORS[e.stage] || "")}>
                    {e.stage}
                  </span>
                </td>
                <td>
                  <span className={"chip " + (STRATEGY_CHIP[e.strategy] || "chip-grey")}>
                    {e.strategy}
                  </span>
                </td>
                <td>
                  {e.decision === "MATCHED" ? (
                    <span className="chip chip-green">MATCHED</span>
                  ) : (
                    <span className="chip chip-red">EXCEPTION</span>
                  )}
                </td>
                <td>
                  <ConfBar value={e.confidence} />
                </td>
                <td className="audit-reason">{e.reason || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ConfBar({ value }) {
  const pct = Math.round((value || 0) * 100);
  return (
    <div className="conf-bar-wrap">
      <div className="conf-bar-bg">
        <div className="conf-bar-fill" style={{ width: pct + "%" }} />
      </div>
      <span className="conf-pct">{pct}%</span>
    </div>
  );
}
