import { useState } from "react";

export default function UploadPanel({ onSubmit, loading }) {
  const [settlements, setSettlements] = useState(null);
  const [bank, setBank]               = useState(null);

  function handleSubmit(e) {
    e.preventDefault();
    if (!settlements || !bank) return;
    onSubmit(settlements, bank);
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
