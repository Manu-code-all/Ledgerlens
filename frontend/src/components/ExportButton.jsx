import { useState } from "react";

function download(filename, content, mime = "text/plain") {
  const blob = new Blob([content], { type: mime });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function buildTextReport(result) {
  const { stats, matches, exceptions } = result;
  const p = stats.params || {};
  const now = new Date().toLocaleString("en-IN", { timeZone: "Asia/Kolkata" });

  const line = (c = "-", n = 48) => c.repeat(n);

  const lines = [
    "LEDGERLENS RECONCILIATION REPORT",
    `Generated: ${now}`,
    line("="),
    "",
    "SUMMARY",
    line(),
    `Total settlements   : ${stats.total}`,
    `Matched             : ${stats.matched}  (${stats.match_rate}%)`,
    `Exceptions          : ${stats.exceptions}  (${(100 - stats.match_rate).toFixed(1)}%)`,
    stats.accuracy != null
      ? `Accuracy            : ${stats.accuracy}%  (${stats.correct} correct, ${stats.incorrect} incorrect)`
      : "",
    `Throughput          : ${stats.throughput} rec/s`,
    `Run duration        : ${stats.elapsed}s`,
    "",
    "PIPELINE BREAKDOWN",
    line(),
    `Stage 1  — Rules    : ${stats.rules_matched} matched`,
    `Stage 1.5 — Batch   : ${stats.batch_matched} matched`,
    `Stage 2  — AI Agent : ${stats.ai_matched} matched`,
    "",
    "PARAMETERS USED",
    line(),
    `Fee Rate            : ${p.fee_rate != null ? (p.fee_rate * 100).toFixed(1) + "%" : "2.0%"}`,
    `Date Window         : ±${p.date_window ?? 3} days`,
    `Confidence Threshold: ${p.confidence_threshold != null ? (p.confidence_threshold * 100).toFixed(0) + "%" : "50%"}`,
    "",
    `EXCEPTIONS  (${exceptions.length} records require human review)`,
    line(),
  ];

  exceptions.forEach((e) => {
    const conf = Math.round((e.confidence || 0) * 100);
    lines.push(`${e.settlement_id.padEnd(14)} conf=${conf}%  ${e.reason || "No match found"}`);
    if (e.near_miss?.bank_txn_id) {
      lines.push(
        `  → Closest: ${e.near_miss.bank_txn_id}  ` +
        `(₹${e.near_miss.amount_diff?.toFixed(2)} off, ${e.near_miss.date_diff}d gap)`
      );
    }
  });

  lines.push("", `MATCHES  (${matches.length} records)`, line());
  matches.forEach((m) => {
    const conf = Math.round((m.confidence || 0) * 100);
    lines.push(
      `${m.settlement_id.padEnd(14)} → ${m.bank_txn_id.padEnd(12)}  ${m.strategy.padEnd(8)}  ${conf}%`
    );
  });

  lines.push("", line("="), "End of report — LedgerLens AI Reconciliation Controller");
  return lines.filter((l) => l !== null).join("\n");
}

function buildMatchesCSV(matches) {
  const header = "settlement_id,bank_txn_id,strategy,confidence,reason";
  const rows = matches.map((m) =>
    [m.settlement_id, m.bank_txn_id, m.strategy,
     (m.confidence || 0).toFixed(2),
     `"${(m.reason || "").replace(/"/g, '""')}"`].join(",")
  );
  return [header, ...rows].join("\n");
}

function buildExceptionsCSV(exceptions) {
  const header = "settlement_id,confidence,reason,nearest_bank_entry,amount_diff,date_diff_days,suggestion";
  const rows = exceptions.map((e) => {
    const nm = e.near_miss || {};
    return [
      e.settlement_id,
      (e.confidence || 0).toFixed(2),
      `"${(e.reason || "").replace(/"/g, '""')}"`,
      nm.bank_txn_id || "",
      nm.amount_diff != null ? nm.amount_diff.toFixed(2) : "",
      nm.date_diff ?? "",
      `"${(nm.suggestion || "").replace(/"/g, '""')}"`,
    ].join(",");
  });
  return [header, ...rows].join("\n");
}

export default function ExportButton({ result }) {
  const [open, setOpen] = useState(false);

  function handle(type) {
    setOpen(false);
    const ts = new Date().toISOString().slice(0, 10);
    if (type === "report") {
      download(`ledgerlens-report-${ts}.txt`, buildTextReport(result));
    } else if (type === "matches") {
      download(`ledgerlens-matches-${ts}.csv`, buildMatchesCSV(result.matches), "text/csv");
    } else if (type === "exceptions") {
      download(`ledgerlens-exceptions-${ts}.csv`, buildExceptionsCSV(result.exceptions), "text/csv");
    }
  }

  return (
    <div className="export-wrap">
      <button className="export-btn" onClick={() => setOpen((v) => !v)}>
        ↓ Export
      </button>
      {open && (
        <>
          <div className="export-backdrop" onClick={() => setOpen(false)} />
          <div className="export-menu">
            <button className="export-item" onClick={() => handle("report")}>
              <span className="export-icon">📄</span>
              <div>
                <div className="export-item-title">Full Report (.txt)</div>
                <div className="export-item-sub">Summary + all matches + all exceptions</div>
              </div>
            </button>
            <button className="export-item" onClick={() => handle("matches")}>
              <span className="export-icon">✅</span>
              <div>
                <div className="export-item-title">Matches (.csv)</div>
                <div className="export-item-sub">{result.matches.length} matched records</div>
              </div>
            </button>
            <button className="export-item" onClick={() => handle("exceptions")}>
              <span className="export-icon">⚠️</span>
              <div>
                <div className="export-item-title">Exceptions (.csv)</div>
                <div className="export-item-sub">{result.exceptions.length} records with near-miss data</div>
              </div>
            </button>
          </div>
        </>
      )}
    </div>
  );
}
