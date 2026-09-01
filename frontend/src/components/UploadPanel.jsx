import { useState } from "react";

const DEFAULTS = { feeRate: 2, dateWindow: 3, confidenceThreshold: 50 };

export default function UploadPanel({ onSubmit, loading }) {
  const [settlements, setSettlements] = useState(null);
  const [bank, setBank]               = useState(null);
  const [showAdv, setShowAdv]         = useState(false);
  const [params, setParams]           = useState(DEFAULTS);

  function setParam(key, val) {
    setParams((p) => ({ ...p, [key]: val }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (!settlements || !bank) return;
    onSubmit(settlements, bank, {
      fee_rate:             params.feeRate / 100,
      date_window:          params.dateWindow,
      confidence_threshold: params.confidenceThreshold / 100,
    });
  }

  return (
    <form className="upload-panel" onSubmit={handleSubmit}>
      <div className="upload-row">
        <FileInput
          label="settlements.csv"
          hint="Payment gateway export"
          onChange={setSettlements}
          file={settlements}
        />
        <FileInput
          label="bank_statement.csv"
          hint="Bank credit lines"
          onChange={setBank}
          file={bank}
        />
      </div>

      <div className="adv-toggle-row">
        <button
          type="button"
          className="adv-toggle"
          onClick={() => setShowAdv((v) => !v)}
        >
          {showAdv ? "▲" : "▼"} Advanced Settings
        </button>
        {!showAdv && (
          <span className="adv-defaults">
            Fee {params.feeRate}% · Date ±{params.dateWindow}d · Confidence ≥{params.confidenceThreshold}%
          </span>
        )}
      </div>

      {showAdv && (
        <div className="adv-panel">
          <Slider
            label="Fee Rate"
            value={params.feeRate}
            min={0.5} max={5} step={0.1}
            format={(v) => `${v.toFixed(1)}%`}
            hint="Razorpay platform fee deducted before settlement"
            onChange={(v) => setParam("feeRate", v)}
          />
          <Slider
            label="Date Window"
            value={params.dateWindow}
            min={1} max={14} step={1}
            format={(v) => `±${v} days`}
            hint="How many days of lag to allow between settlement and bank dates"
            onChange={(v) => setParam("dateWindow", v)}
          />
          <Slider
            label="Confidence Threshold"
            value={params.confidenceThreshold}
            min={10} max={90} step={5}
            format={(v) => `${v}%`}
            hint="AI matches below this confidence are sent to exceptions"
            onChange={(v) => setParam("confidenceThreshold", v)}
          />
          <button
            type="button"
            className="reset-btn"
            onClick={() => setParams(DEFAULTS)}
          >
            Reset to defaults
          </button>
        </div>
      )}

      <button
        type="submit"
        className="run-btn"
        disabled={!settlements || !bank || loading}
      >
        {loading ? "Running…" : "Run Reconciliation"}
      </button>
    </form>
  );
}

function FileInput({ label, hint, onChange, file }) {
  return (
    <label className={"file-input" + (file ? " has-file" : "")}>
      <span className="file-label">{label}</span>
      <span className="file-hint">{file ? file.name : hint}</span>
      <input
        type="file"
        accept=".csv"
        style={{ display: "none" }}
        onChange={(e) => onChange(e.target.files[0] || null)}
      />
    </label>
  );
}

function Slider({ label, value, min, max, step, format, hint, onChange }) {
  return (
    <div className="slider-row">
      <div className="slider-header">
        <span className="slider-label">{label}</span>
        <span className="slider-value">{format(value)}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        className="slider-input"
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
      <span className="slider-hint">{hint}</span>
    </div>
  );
}
