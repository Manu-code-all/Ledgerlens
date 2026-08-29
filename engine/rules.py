"""
Rule-based reconciliation matcher — the baseline.

Two strategies only, applied in order:

  Strategy 1 (REFERENCE): look for the settlement's order_id inside any
  bank description string. "ORD-7011" found in "RZPY*ORD-7011 NEFT CR"
  is a match. Fast, exact, zero ambiguity.

  Strategy 2 (AMOUNT+DATE): if no reference match was found, look for a
  bank line where the credit amount AND the value date both match exactly.

No fuzzy logic. No fee tolerance. No date windows. Anything that doesn't
hit Strategy 1 or 2 goes to the exceptions list.

This is intentionally simple. The point is to establish a measurable
baseline before the AI agent is added. The categories that fail here —
FEE, LAG, GARBLED, BATCH — are exactly the ones the agent will handle.
"""

import csv
import json
import time
from datetime import datetime


def load_csv(path):
    """Read a CSV file and return a list of dicts, one per row."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run(settlements_path, bank_path, audit_log_path=None):
    """
    Match settlements against bank lines using deterministic rules.

    Returns a dict with:
      matches    - list of {settlement_id, bank_txn_id, strategy, confidence}
      exceptions - list of {settlement_id, reason}
      stats      - timing and count information
    """
    started_at = time.time()

    settlements = load_csv(settlements_path)
    bank_rows   = load_csv(bank_path)

    # We will "consume" each bank line at most once.
    # unmatched_bank is a dict: bank_txn_id -> row, shrinking as we match.
    unmatched_bank = {row["bank_txn_id"]: row for row in bank_rows}

    matches    = []
    exceptions = []
    audit      = []  # every decision goes here

    for settlement in settlements:
        sid        = settlement["settlement_id"]
        order_id   = settlement["order_id"]      # e.g. "ORD-7011"
        gross      = settlement["gross_amount"]  # string like "8643.12"
        setl_date  = settlement["settlement_date"]

        matched_bid      = None
        matched_strategy = None

        # ------------------------------------------------------------------
        # Strategy 1: reference match
        # Scan every remaining bank line for the order_id in its description.
        # ------------------------------------------------------------------
        for bid, bank_row in unmatched_bank.items():
            if order_id in bank_row["description"]:
                matched_bid      = bid
                matched_strategy = "REF"
                break

        # ------------------------------------------------------------------
        # Strategy 2: exact amount + exact date
        # Only tried if Strategy 1 found nothing.
        # ------------------------------------------------------------------
        if matched_bid is None:
            for bid, bank_row in unmatched_bank.items():
                if (bank_row["credit_amount"] == gross and
                        bank_row["value_date"] == setl_date):
                    matched_bid      = bid
                    matched_strategy = "AMT+DATE"
                    break

        # ------------------------------------------------------------------
        # Record the outcome
        # ------------------------------------------------------------------
        if matched_bid is not None:
            matches.append({
                "settlement_id": sid,
                "bank_txn_id":   matched_bid,
                "strategy":      matched_strategy,
                "confidence":    1.0,   # rules are binary: matched or not
            })
            audit.append({
                "settlement_id": sid,
                "bank_txn_id":   matched_bid,
                "strategy":      matched_strategy,
                "decision":      "MATCHED",
                "note":          "rule: " + matched_strategy,
            })
            # Remove from pool so no other settlement can claim this bank line.
            del unmatched_bank[matched_bid]
        else:
            exceptions.append({
                "settlement_id": sid,
                "reason":        "no_rule_match",
            })
            audit.append({
                "settlement_id": sid,
                "bank_txn_id":   "",
                "strategy":      "NONE",
                "decision":      "EXCEPTION",
                "note":          "neither reference nor amount+date found a match",
            })

    elapsed = round(time.time() - started_at, 3)

    stats = {
        "total_settlements": len(settlements),
        "matched":           len(matches),
        "exceptions":        len(exceptions),
        "unmatched_bank":    len(unmatched_bank),   # bank lines nobody claimed
        "elapsed_seconds":   elapsed,
        "throughput":        round(len(settlements) / elapsed, 1) if elapsed > 0 else 0,
    }

    # Write audit log if a path was given.
    if audit_log_path:
        with open(audit_log_path, "w", encoding="utf-8") as f:
            for entry in audit:
                entry["ts"] = datetime.utcnow().isoformat()
                f.write(json.dumps(entry) + "\n")

    return {"matches": matches, "exceptions": exceptions, "stats": stats}


def score(matches, ground_truth_path):
    """
    Compare matches against the answer key and report accuracy.

    Returns a dict with correct, incorrect, missing counts and accuracy %.
    """
    truth = {}
    for row in load_csv(ground_truth_path):
        truth[row["settlement_id"]] = row["bank_txn_id"]  # "" means no match

    correct   = 0
    incorrect = 0
    missing   = 0   # settlement in truth but not in our matches

    matched_ids = {m["settlement_id"]: m["bank_txn_id"] for m in matches}

    for sid, correct_bid in truth.items():
        our_bid = matched_ids.get(sid)  # None if we put it in exceptions
        if our_bid is None:
            # We said exception; correct only if the truth also has no match.
            if correct_bid == "":
                correct += 1
            else:
                missing += 1
        else:
            if our_bid == correct_bid:
                correct += 1
            else:
                incorrect += 1

    total   = len(truth)
    accuracy = round(correct / total * 100, 1) if total else 0

    return {
        "total":     total,
        "correct":   correct,
        "incorrect": incorrect,
        "missing":   missing,
        "accuracy":  accuracy,
    }
