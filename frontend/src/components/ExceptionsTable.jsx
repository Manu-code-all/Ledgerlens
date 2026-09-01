import { useState } from "react";

export default function ExceptionsTable({ exceptions }) {
  const [expanded, setExpanded] = useState(null);

  if (exceptions.length === 0) {
    return (
      <div className="empty-state">
        <p>No exceptions — all settlements were matched.</p>
      </div>
    );
  }

  function toggle(id) {
    setExpanded(expanded === id ? null : id);
  }

  return (
    <div className="table-wrap">
      <div className="exceptions-header">
        <span className="exc-badge">{exceptions.length} records require human review</span>
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th>Settlement</th>
            <th>Confidence</th>
            <th>Reason</th>
            <th>Near Miss</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {exceptions.map((e) => {
            const nm     = e.near_miss || {};
            const isOpen = expanded === e.settlement_id;
            return (
              <>
                <tr key={e.settlement_id} className={"exception-row" + (isOpen ? " row-expanded" : "")}>
                  <td className="mono">{e.settlement_id}</td>
                  <td>
                    <span className="chip chip-red">
                      {Math.round((e.confidence || 0) * 100)}%
                    </span>
                  </td>
                  <td className="reason-cell">{e.reason || "No match found"}</td>
                  <td>
                    {nm.bank_txn_id ? (
                      <div className="near-miss-summary">
                        <span className="mono near-miss-id">{nm.bank_txn_id}</span>
                        <span className="near-miss-meta">
                          ₹{nm.amount_diff?.toFixed(2)} off · {nm.date_diff}d gap
                        </span>
                      </div>
                    ) : (
                      <span className="muted-dash">—</span>
                    )}
                  </td>
                  <td>
                    {nm.suggestion && (
                      <button className="expand-btn" onClick={() => toggle(e.settlement_id)}>
                        {isOpen ? "▲" : "▼"}
                      </button>
                    )}
                  </td>
                </tr>

                {isOpen && nm.suggestion && (
                  <tr key={e.settlement_id + "-nm"} className="reason-row">
                    <td colSpan={5}>
                      <div className="near-miss-box">
                        <div className="near-miss-box-header">
                          <span className="near-miss-label">Closest bank entry:</span>
                          <span className="mono">{nm.bank_txn_id}</span>
                          <span className="near-miss-chips">
                            <span className="chip chip-yellow">₹{nm.credit_amount?.toFixed(2)}</span>
                            <span className="chip chip-grey">{nm.value_date}</span>
                          </span>
                          {nm.description && (
                            <span className="near-miss-desc">"{nm.description}"</span>
                          )}
                        </div>
                        <div className="near-miss-suggestion">
                          <span className="suggestion-label">Suggested action:</span>{" "}
                          {nm.suggestion}
                        </div>
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
