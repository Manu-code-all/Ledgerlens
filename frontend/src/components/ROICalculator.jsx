import { useState } from "react";

const DEFAULTS = {
  monthlyVolume: 10000,   // settlements processed per month
  manualMinutes: 5,       // minutes a human takes per manual match
  hourlyCost:    400,     // ₹ per hour for a finance analyst
};

const VOLUME_STEP = 500;
const TIME_STEP    = 0.5;
const COST_STEP    = 50;

export default function ROICalculator({ stats }) {
  const [p, setP]           = useState(DEFAULTS);
  const [period, setPeriod] = useState("monthly");

  function set(key, val, min, max) {
    setP((s) => ({ ...s, [key]: Math.min(max, Math.max(min, val)) }));
  }

  const throughput = stats.throughput || 1.5;
  const mult        = period === "annual" ? 12 : 1;

  const manualHours    = ((p.monthlyVolume * p.manualMinutes) / 60) * mult;
  const automatedHours = ((p.monthlyVolume / throughput) / 3600) * mult;
  const hoursSaved      = Math.max(manualHours - automatedHours, 0);
  const costSaved        = hoursSaved * p.hourlyCost;

  const fmtINR = (n) => "₹" + Math.round(n).toLocaleString("en-IN");

  return (
    <div className="roi-widget">
      <div className="roi-widget-header">
        <div className="roi-widget-title">
          <span className="roi-icon-sm">₹</span>
          Business Impact
        </div>
      </div>

      <div className="roi-period-toggle roi-period-toggle-sm">
        <button
          className={"period-btn" + (period === "monthly" ? " active" : "")}
          onClick={() => setPeriod("monthly")}
        >
          Monthly
        </button>
        <button
          className={"period-btn" + (period === "annual" ? " active" : "")}
          onClick={() => setPeriod("annual")}
        >
          Annual
        </button>
      </div>

      <div className="roi-widget-steppers">
        <MiniStepper
          icon="📊" iconClass="stepper-icon-blue"
          label="Volume/mo"
          value={p.monthlyVolume}
          format={(v) => v.toLocaleString("en-IN")}
          onDec={() => set("monthlyVolume", p.monthlyVolume - VOLUME_STEP, 500, 200000)}
          onInc={() => set("monthlyVolume", p.monthlyVolume + VOLUME_STEP, 500, 200000)}
        />
        <MiniStepper
          icon="⏱" iconClass="stepper-icon-purple"
          label="Manual time"
          value={p.manualMinutes}
          format={(v) => `${v} min`}
          onDec={() => set("manualMinutes", p.manualMinutes - TIME_STEP, 1, 20)}
          onInc={() => set("manualMinutes", p.manualMinutes + TIME_STEP, 1, 20)}
        />
        <MiniStepper
          icon="💵" iconClass="stepper-icon-green"
          label="Analyst cost"
          value={p.hourlyCost}
          format={(v) => `₹${v}/hr`}
          onDec={() => set("hourlyCost", p.hourlyCost - COST_STEP, 100, 3000)}
          onInc={() => set("hourlyCost", p.hourlyCost + COST_STEP, 100, 3000)}
        />
      </div>

      <div className="roi-hero roi-hero-sm">
        <div className="roi-hero-label">{period === "annual" ? "Annual Savings" : "Monthly Savings"}</div>
        <div className="roi-hero-value roi-hero-value-sm">
          {fmtINR(costSaved)}
          <span className="roi-hero-period">/{period === "annual" ? "yr" : "mo"}</span>
        </div>
        <div className="roi-hero-sub">{hoursSaved.toFixed(0)} hrs saved</div>
      </div>

      <div className="roi-widget-fine">
        Based on this run's {throughput} rec/s throughput
      </div>
    </div>
  );
}

function MiniStepper({ icon, iconClass, label, value, format, onDec, onInc }) {
  return (
    <div className="mini-stepper">
      <span className={"stepper-icon stepper-icon-sm " + iconClass}>{icon}</span>
      <span className="mini-stepper-label">{label}</span>
      <div className="mini-stepper-controls">
        <button type="button" className="stepper-btn stepper-btn-sm" onClick={onDec}>−</button>
        <span className="mini-stepper-value">{format(value)}</span>
        <button type="button" className="stepper-btn stepper-btn-sm" onClick={onInc}>+</button>
      </div>
    </div>
  );
}
