import { useEffect, useRef } from "react";

const W   = 600;
const H   = 200;
const PX  = 56;   // horizontal padding
const PY  = 28;   // vertical padding
const CW  = W - PX * 2;
const CH  = H - PY * 2;

const COLORS = ["#8892a4", "#3b82f6", "#a855f7", "#22c55e"];
const STAGE_LABELS = [
  { top: "Start",     bot: "0 matched" },
  { top: "Stage 1",   bot: "Rules" },
  { top: "Stage 1.5", bot: "Batch" },
  { top: "Stage 2",   bot: "AI Agent" },
];

function toY(pct) {
  return PY + CH * (1 - pct / 100);
}

function toX(i, total) {
  return PX + (CW / (total - 1)) * i;
}

export default function AccuracyTracker({ stats }) {
  const { rules_matched = 0, batch_matched = 0, matched = 0, total = 1 } = stats;

  const values = [
    0,
    parseFloat((rules_matched / total * 100).toFixed(1)),
    parseFloat(((rules_matched + batch_matched) / total * 100).toFixed(1)),
    parseFloat((matched / total * 100).toFixed(1)),
  ];

  const pts = values.map((v, i) => ({ x: toX(i, values.length), y: toY(v), v }));

  const polyline = pts.map((p) => `${p.x},${p.y}`).join(" ");
  const fillPoly  = [
    `${pts[0].x},${PY + CH}`,
    ...pts.map((p) => `${p.x},${p.y}`),
    `${pts[pts.length - 1].x},${PY + CH}`,
  ].join(" ");

  const lineRef = useRef(null);

  useEffect(() => {
    const el = lineRef.current;
    if (!el) return;
    const len = el.getTotalLength();
    el.style.strokeDasharray  = len;
    el.style.strokeDashoffset = len;
    el.getBoundingClientRect();
    el.style.transition = "stroke-dashoffset 1.4s cubic-bezier(0.4,0,0.2,1)";
    el.style.strokeDashoffset = 0;
  }, []);

  return (
    <div className="tracker-card">
      <div className="tracker-header">
        <div>
          <div className="tracker-title">Pipeline Accuracy Progression</div>
          <div className="tracker-sub">Match rate after each stage — watch the AI add value</div>
        </div>
        <div className="tracker-delta">
          <span className="delta-label">AI contribution</span>
          <span className="delta-value">
            +{(values[3] - values[1]).toFixed(1)}%
          </span>
        </div>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} width="100%" className="tracker-svg">
        <defs>
          <linearGradient id="fillGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#6366f1" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0.01" />
          </linearGradient>
        </defs>

        {/* Grid lines */}
        {[0, 25, 50, 75, 100].map((pct) => (
          <g key={pct}>
            <line
              x1={PX} y1={toY(pct)} x2={PX + CW} y2={toY(pct)}
              stroke="rgba(255,255,255,0.05)" strokeWidth="1"
            />
            <text x={PX - 8} y={toY(pct) + 4} textAnchor="end"
              fontSize="10" fill="rgba(136,146,164,0.7)">
              {pct}%
            </text>
          </g>
        ))}

        {/* Fill area */}
        <polygon points={fillPoly} fill="url(#fillGrad)" />

        {/* Animated line */}
        <polyline
          ref={lineRef}
          points={polyline}
          fill="none"
          stroke="#6366f1"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Dots + labels */}
        {pts.map((p, i) => (
          <g key={i} style={{ animation: `dotPop 0.3s ease ${0.3 + i * 0.3}s both` }}>
            <circle cx={p.x} cy={p.y} r="6" fill={COLORS[i]} stroke="var(--bg-color,#0f1117)" strokeWidth="2" />
            {/* value label above dot */}
            <text x={p.x} y={p.y - 12} textAnchor="middle" fontSize="12"
              fontWeight="700" fill={COLORS[i]}>
              {p.v}%
            </text>
            {/* stage label below chart */}
            <text x={p.x} y={PY + CH + 18} textAnchor="middle" fontSize="11"
              fontWeight="600" fill="rgba(226,232,240,0.9)">
              {STAGE_LABELS[i].top}
            </text>
            <text x={p.x} y={PY + CH + 31} textAnchor="middle" fontSize="10"
              fill="rgba(136,146,164,0.8)">
              {STAGE_LABELS[i].bot}
            </text>
          </g>
        ))}

        {/* Vertical stage separators */}
        {pts.slice(1).map((p, i) => (
          <line key={i} x1={p.x} y1={PY} x2={p.x} y2={PY + CH}
            stroke="rgba(255,255,255,0.04)" strokeWidth="1" strokeDasharray="3,3" />
        ))}
      </svg>
    </div>
  );
}
