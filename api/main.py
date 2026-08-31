"""
LedgerLens FastAPI backend.

Two endpoints:
  POST /reconcile   Upload settlements.csv + bank_statement.csv, run the pipeline
  GET  /results     Return the last run's full results as JSON

The React dashboard calls these two endpoints only.
"""

import csv
import io
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# Allow "python api/main.py" or "uvicorn api.main:app" from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import rules
import batch_detector
import agent

app = FastAPI(title="LedgerLens", version="1.0")

# Allow the React dev server (port 5173) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for the last run's results (simple, no database needed)
_last_result: Optional[dict] = None

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
TRUTH_PATH = os.path.join(DATA_DIR, "ground_truth.csv")


def parse_csv_bytes(content: bytes) -> list:
    text = content.decode("utf-8-sig")   # strip BOM if present
    return list(csv.DictReader(io.StringIO(text)))


def save_temp_csv(rows: list, fieldnames: list, filename: str) -> str:
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


@app.get("/")
def root():
    return {"status": "ok", "service": "LedgerLens"}


@app.post("/reconcile")
async def reconcile(
    settlements: UploadFile = File(...),
    bank_statement: UploadFile = File(...),
):
    """
    Accept two CSV uploads, run the three-stage pipeline, return results.
    """
    global _last_result

    # ---- validate file types ----
    for f in [settlements, bank_statement]:
        if not f.filename.endswith(".csv"):
            raise HTTPException(400, detail=f"{f.filename} must be a .csv file")

    # ---- parse uploaded CSVs ----
    try:
        setl_rows = parse_csv_bytes(await settlements.read())
        bank_rows = parse_csv_bytes(await bank_statement.read())
    except Exception as e:
        raise HTTPException(400, detail="CSV parse error: " + str(e))

    # ---- validate required columns ----
    required_setl = {"settlement_id", "order_id", "gross_amount", "settlement_date"}
    required_bank = {"bank_txn_id", "value_date", "credit_amount", "description"}

    if setl_rows and not required_setl.issubset(setl_rows[0].keys()):
        missing = required_setl - setl_rows[0].keys()
        raise HTTPException(400, detail="settlements.csv missing columns: " + str(missing))

    if bank_rows and not required_bank.issubset(bank_rows[0].keys()):
        missing = required_bank - bank_rows[0].keys()
        raise HTTPException(400, detail="bank_statement.csv missing columns: " + str(missing))

    if len(setl_rows) == 0:
        raise HTTPException(400, detail="settlements.csv is empty")
    if len(bank_rows) == 0:
        raise HTTPException(400, detail="bank_statement.csv is empty")

    # ---- save to disk so the engine modules can read them ----
    setl_fieldnames = list(setl_rows[0].keys())
    bank_fieldnames = list(bank_rows[0].keys())
    setl_path = save_temp_csv(setl_rows, setl_fieldnames, "uploaded_settlements.csv")
    bank_path = save_temp_csv(bank_rows, bank_fieldnames, "uploaded_bank.csv")

    started = time.time()

    # ---- Stage 1: rules ----
    rule_result = rules.run(setl_path, bank_path)
    claimed_by_rules = {m["bank_txn_id"] for m in rule_result["matches"]}
    all_bank_map = {r["bank_txn_id"]: r for r in bank_rows}
    unclaimed_bank = {bid: row for bid, row in all_bank_map.items()
                      if bid not in claimed_by_rules}
    matched_ids = {m["settlement_id"] for m in rule_result["matches"]}
    unmatched_settlements = [s for s in setl_rows if s["settlement_id"] not in matched_ids]

    # ---- Stage 1.5: batch detector ----
    batch_groups, _ = batch_detector.detect(unmatched_settlements, unclaimed_bank)
    batch_matches = []
    batch_used = set()
    for grp in batch_groups:
        for sid in grp["settlement_ids"]:
            batch_matches.append({
                "settlement_id": sid,
                "bank_txn_id":   grp["bank_txn_id"],
                "strategy":      "BATCH",
                "confidence":    0.99,
                "reason":        grp["reason"],
            })
            batch_used.add(sid)
        unclaimed_bank.pop(grp["bank_txn_id"], None)
    unmatched_settlements = [s for s in unmatched_settlements
                             if s["settlement_id"] not in batch_used]

    # ---- Stage 2: AI agent ----
    agent_results = agent.run_batch(unmatched_settlements, unclaimed_bank)

    # ---- combine ----
    CONFIDENCE_THRESHOLD = 0.5
    final_matches = list(rule_result["matches"]) + batch_matches
    final_exceptions = []

    for res in agent_results:
        sid  = res["settlement_id"]
        bid  = res.get("bank_txn_id")
        conf = res.get("confidence", 0.0)
        if bid and conf >= CONFIDENCE_THRESHOLD and res["decision"] == "AI_MATCHED":
            final_matches.append({
                "settlement_id": sid,
                "bank_txn_id":   bid,
                "strategy":      "AI",
                "confidence":    conf,
                "reason":        res.get("reason", ""),
            })
        else:
            final_exceptions.append({
                "settlement_id": sid,
                "reason":        res.get("reason", res.get("decision", "")),
                "confidence":    conf,
            })

    elapsed = round(time.time() - started, 1)

    # ---- score if ground truth available ----
    scoring = None
    if os.path.exists(TRUTH_PATH):
        try:
            scoring = rules.score(final_matches, TRUTH_PATH)
        except Exception:
            pass

    # ---- build response ----
    stats = {
        "total":          len(setl_rows),
        "matched":        len(final_matches),
        "exceptions":     len(final_exceptions),
        "match_rate":     round(len(final_matches) / len(setl_rows) * 100, 1),
        "rules_matched":  rule_result["stats"]["matched"],
        "batch_matched":  len(batch_matches),
        "ai_matched":     sum(1 for m in final_matches if m.get("strategy") == "AI"),
        "elapsed":        elapsed,
        "throughput":     round(len(setl_rows) / elapsed, 1) if elapsed > 0 else 0,
        "run_at":         datetime.now(timezone.utc).isoformat(),
    }
    if scoring:
        stats["accuracy"]  = scoring["accuracy"]
        stats["correct"]   = scoring["correct"]
        stats["incorrect"] = scoring["incorrect"]
        stats["missed"]    = scoring["missing"]

    _last_result = {
        "stats":      stats,
        "matches":    final_matches,
        "exceptions": final_exceptions,
    }

    return _last_result


@app.get("/results")
def get_results():
    if _last_result is None:
        raise HTTPException(404, detail="No reconciliation run yet. POST to /reconcile first.")
    return _last_result
