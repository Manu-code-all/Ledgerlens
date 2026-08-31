export default function ExceptionsTable({ exceptions }) {
  if (exceptions.length === 0) {
    return (
      <div className="empty-state">
        <p>No exceptions — all settlements were matched.</p>
      </div>
    );
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
          </tr>
        </thead>
        <tbody>
          {exceptions.map((e) => (
            <tr key={e.settlement_id} className="exception-row">
              <td className="mono">{e.settlement_id}</td>
              <td>
                <span className="chip chip-red">
                  {Math.round((e.confidence || 0) * 100)}%
                </span>
              </td>
              <td className="reason-cell">{e.reason || "No match found"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
