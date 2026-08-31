import { useState } from "react";

const STRATEGY_COLORS = {
  REF:      "chip-blue",
  "AMT+DATE": "chip-teal",
  BATCH:    "chip-purple",
  AI:       "chip-green",
};

export default function MatchesTable({ matches }) {
  const [expanded, setExpanded] = useState(null);

  function toggle(id) {
    setExpanded(expanded === id ? null : id);
  }

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Settlement</th>
            <th>Bank Line</th>
            <th>Strategy</th>
            <th>Confidence</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {matches.map((m) => {
            const isOpen = expanded === m.settlement_id;
            return (
              <>
                <tr key={m.settlement_id} className={isOpen ? "row-expanded" : ""}>
                  <td className="mono">{m.settlement_id}</td>
                  <td className="mono">{m.bank_txn_id}</td>
                  <td>
                    <span className={"chip " + (STRATEGY_COLORS[m.strategy] || "chip-grey")}>
                      {m.strategy}
                    </span>
                  </td>
                  <td>
                    <ConfidenceBar value={m.confidence} />
                  </td>
                  <td>
                    {m.reason && (
                      <button className="expand-btn" onClick={() => toggle(m.settlement_id)}>
                        {isOpen ? "▲" : "▼"}
                      </button>
                    )}
                  </td>
                </tr>
                {isOpen && m.reason && (
                  <tr key={m.settlement_id + "-reason"} className="reason-row">
                    <td colSpan={5}>
                      <div className="reason-box">
                        <span className="reason-label">AI reasoning:</span> {m.reason}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ConfidenceBar({ value }) {
  const pct = Math.round((value || 0) * 100);
  const color = pct >= 90 ? "#22c55e" : pct >= 60 ? "#f59e0b" : "#ef4444";
  return (
    <div className="conf-bar-wrap" title={pct + "%"}>
      <div className="conf-bar-bg">
        <div className="conf-bar-fill" style={{ width: pct + "%", background: color }} />
      </div>
      <span className="conf-pct">{pct}%</span>
    </div>
  );
}
