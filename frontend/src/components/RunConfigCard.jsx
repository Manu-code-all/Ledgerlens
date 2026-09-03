export default function RunConfigCard({ stats }) {
  const p = stats.params || {};

  const runTime = stats.run_at
    ? new Date(stats.run_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    : "—";

  return (
    <div className="run-config-card">
      <div className="run-config-header">
        <span className="run-config-icon">⚙</span>
        Run Configuration
      </div>

      <div className="run-config-grid">
        <ConfigItem label="Fee Rate"    value={p.fee_rate != null ? `${(p.fee_rate * 100).toFixed(1)}%` : "—"} />
        <ConfigItem label="Date Window" value={p.date_window != null ? `±${p.date_window}d` : "—"} />
        <ConfigItem label="Confidence"  value={p.confidence_threshold != null ? `≥${(p.confidence_threshold * 100).toFixed(0)}%` : "—"} />
        <ConfigItem label="Records"     value={stats.total} />
        <ConfigItem label="Elapsed"     value={`${stats.elapsed}s`} />
        <ConfigItem label="Run At"      value={runTime} />
      </div>

      <div className="run-config-fine">
        Rules → Batch Detector → AI Agent · re-run with different sliders to compare
      </div>
    </div>
  );
}

function ConfigItem({ label, value }) {
  return (
    <div className="run-config-item">
      <div className="run-config-item-label">{label}</div>
      <div className="run-config-item-value">{value}</div>
    </div>
  );
}
