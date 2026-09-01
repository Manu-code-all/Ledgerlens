const BUCKETS = [
  { label: "90–100%", min: 0.90, max: 1.01, color: "#22c55e", desc: "High confidence" },
  { label: "70–90%",  min: 0.70, max: 0.90, color: "#f59e0b", desc: "Medium confidence" },
  { label: "50–70%",  min: 0.50, max: 0.70, color: "#f97316", desc: "Low confidence" },
  { label: "<50%",    min: 0.00, max: 0.50, color: "#ef4444", desc: "Exceptions" },
];

export default function ConfidenceChart({ matches, exceptions }) {
  const all = [
    ...matches.map((m) => ({ confidence: m.confidence, type: "match" })),
    ...exceptions.map((e) => ({ confidence: e.confidence || 0, type: "exception" })),
  ];

  const buckets = BUCKETS.map((b) => ({
    ...b,
    count: all.filter((r) => r.confidence >= b.min && r.confidence < b.max).length,
  }));

  const maxCount = Math.max(...buckets.map((b) => b.count), 1);

  return (
    <div className="conf-chart-card">
      <div className="conf-chart-header">
        <div>
          <div className="conf-chart-title">Confidence Distribution</div>
          <div className="conf-chart-sub">
            How certain the pipeline was across all {all.length} decisions
          </div>
        </div>
        <div className="conf-chart-legend">
          <span className="legend-dot" style={{ background: "#22c55e" }} /> High (≥90%)
          <span className="legend-dot" style={{ background: "#f59e0b" }} /> Medium
          <span className="legend-dot" style={{ background: "#f97316" }} /> Low
          <span className="legend-dot" style={{ background: "#ef4444" }} /> Exception
        </div>
      </div>

      <div className="conf-bars">
        {buckets.map((b) => {
          const pct = Math.round((b.count / maxCount) * 100);
          return (
            <div key={b.label} className="conf-bar-col">
              <div className="conf-bar-count">{b.count}</div>
              <div className="conf-bar-track">
                <div
                  className="conf-bar-fill-vert"
                  style={{ height: pct + "%", background: b.color }}
                  title={`${b.count} records`}
                />
              </div>
              <div className="conf-bar-bucket-label">{b.label}</div>
              <div className="conf-bar-desc">{b.desc}</div>
            </div>
          );
        })}
      </div>

      <div className="conf-insight">
        <InsightRow buckets={buckets} total={all.length} />
      </div>
    </div>
  );
}

function InsightRow({ buckets, total }) {
  const high = buckets.find((b) => b.label === "90–100%").count;
  const exceptions = buckets.find((b) => b.label === "<50%").count;
  const highPct = Math.round((high / total) * 100);

  return (
    <div className="insight-text">
      <span className="insight-highlight" style={{ color: "#22c55e" }}>{highPct}%</span>
      {" "}of all decisions were made with ≥90% confidence.{" "}
      <span className="insight-highlight" style={{ color: "#ef4444" }}>{exceptions}</span>
      {" "}records fell below the confidence threshold and were flagged for human review.
    </div>
  );
}
