import { useState } from "react";

const DEFAULTS = {
  monthlyVolume: 10000,   // settlements processed per month
  manualMinutes: 5,       // minutes a human takes per manual match
  hourlyCost:    400,     // ₹ per hour for a finance analyst
};

const FTE_HOURS_PER_MONTH = 160; // one full-time employee, standard month

export default function ROICalculator({ stats }) {
  const [p, setP] = useState(DEFAULTS);

  function set(key, val) {
    setP((s) => ({ ...s, [key]: val }));
  }

  // Real measured throughput from this run (records/sec)
  const throughput = stats.throughput || 1.5;

  const manualHours    = (p.monthlyVolume * p.manualMinutes) / 60;
  const automatedHours = (p.monthlyVolume / throughput) / 3600;
  const hoursSaved      = Math.max(manualHours - automatedHours, 0);
  const costSaved        = hoursSaved * p.hourlyCost;
  const fteEquivalent    = hoursSaved / FTE_HOURS_PER_MONTH;

  const fmtINR = (n) =>
    "₹" + Math.round(n).toLocaleString("en-IN");

  return (
    <div className="roi-card">
      <div className="roi-header">
        <div>
          <div className="roi-title">Business Impact Calculator</div>
          <div className="roi-sub">
            What this pipeline actually saves a finance team — using this run's real throughput ({throughput} rec/s)
          </div>
        </div>
      </div>

      <div className="roi-inputs">
        <RoiSlider
          label="Monthly settlement volume"
          value={p.monthlyVolume}
          min={500} max={100000} step={500}
          format={(v) => v.toLocaleString("en-IN")}
          onChange={(v) => set("monthlyVolume", v)}
        />
        <RoiSlider
          label="Manual time per record"
          value={p.manualMinutes}
          min={1} max={15} step={0.5}
          format={(v) => `${v} min`}
          onChange={(v) => set("manualMinutes", v)}
        />
        <RoiSlider
          label="Finance analyst cost"
          value={p.hourlyCost}
          min={100} max={1500} step={50}
          format={(v) => `₹${v}/hr`}
          onChange={(v) => set("hourlyCost", v)}
        />
      </div>

      <div className="roi-compare">
        <div className="roi-col roi-col-manual">
          <div className="roi-col-label">Manual reconciliation</div>
          <div className="roi-col-value">{manualHours.toFixed(0)} hrs/month</div>
        </div>
        <div className="roi-arrow">→</div>
        <div className="roi-col roi-col-auto">
          <div className="roi-col-label">LedgerLens</div>
          <div className="roi-col-value">{automatedHours.toFixed(1)} hrs/month</div>
        </div>
      </div>

      <div className="roi-results">
        <div className="roi-result-tile">
          <div className="roi-result-label">Hours saved / month</div>
          <div className="roi-result-value">{hoursSaved.toFixed(0)}</div>
        </div>
        <div className="roi-result-tile">
          <div className="roi-result-label">Cost saved / month</div>
          <div className="roi-result-value">{fmtINR(costSaved)}</div>
        </div>
        <div className="roi-result-tile">
          <div className="roi-result-label">Equivalent headcount freed</div>
          <div className="roi-result-value">{fteEquivalent.toFixed(1)} FTE</div>
        </div>
      </div>

      <div className="roi-footnote">
        Based on this run's measured throughput of {throughput} records/sec, extrapolated to your monthly volume.
        Manual time and analyst cost are editable estimates — adjust the sliders for your own numbers.
      </div>
    </div>
  );
}

function RoiSlider({ label, value, min, max, step, format, onChange }) {
  return (
    <div className="slider-row">
      <div className="slider-header">
        <span className="slider-label">{label}</span>
        <span className="slider-value">{format(value)}</span>
      </div>
      <input
        type="range"
        min={min} max={max} step={step}
        value={value}
        className="slider-input"
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
    </div>
  );
}
