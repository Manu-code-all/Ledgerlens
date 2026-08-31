export default function MetricTiles({ stats }) {
  const tiles = [
    {
      label: "Match Rate",
      value: stats.match_rate + "%",
      sub: `${stats.matched} of ${stats.total} settlements`,
      color: "blue",
    },
    {
      label: "Accuracy",
      value: stats.accuracy != null ? stats.accuracy + "%" : "—",
      sub: stats.accuracy != null
        ? `${stats.correct} correct · ${stats.incorrect} incorrect`
        : "no ground truth provided",
      color: stats.accuracy >= 90 ? "green" : stats.accuracy >= 75 ? "yellow" : "red",
    },
    {
      label: "Exceptions",
      value: stats.exceptions,
      sub: "flagged for human review",
      color: stats.exceptions === 0 ? "green" : "orange",
    },
    {
      label: "Throughput",
      value: stats.throughput + " rec/s",
      sub: `${stats.elapsed}s total · ${stats.total} records`,
      color: "purple",
    },
  ];

  const stageTiles = [
    { label: "Rules",  value: stats.rules_matched, icon: "⚡" },
    { label: "Batch",  value: stats.batch_matched, icon: "📦" },
    { label: "AI",     value: stats.ai_matched,    icon: "🤖" },
  ];

  return (
    <section className="metrics-section">
      <div className="metric-grid">
        {tiles.map((t) => (
          <div key={t.label} className={"metric-tile tile-" + t.color}>
            <p className="tile-label">{t.label}</p>
            <p className="tile-value">{t.value}</p>
            <p className="tile-sub">{t.sub}</p>
          </div>
        ))}
      </div>

      <div className="stage-row">
        <span className="stage-label">Pipeline breakdown:</span>
        {stageTiles.map((s) => (
          <span key={s.label} className="stage-chip">
            {s.icon} {s.label} <strong>{s.value}</strong>
          </span>
        ))}
      </div>
    </section>
  );
}
