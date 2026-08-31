"""
Full two-stage reconciliation pipeline:
  Stage 1 — deterministic rules (fast, zero cost)
  Stage 2 — AI agent for unmatched residue (Groq / qwen3.8-27b)

Usage:
    python engine/run_full.py

Writes a combined audit log to data/audit_log_full.jsonl
"""

import csv
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
import rules
import agent
import batch_detector

ROOT        = os.path.join(os.path.dirname(__file__), "..")
SETTLEMENTS = os.path.join(ROOT, "data", "settlements.csv")
BANK        = os.path.join(ROOT, "data", "bank_statement.csv")
TRUTH       = os.path.join(ROOT, "data", "ground_truth.csv")
AUDIT_LOG   = os.path.join(ROOT, "data", "audit_log_full.jsonl")

CONFIDENCE_THRESHOLD = 0.5   # agent matches below this go to exceptions


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    print("=" * 52)
    print("  LedgerLens — Full Pipeline (Rules + AI Agent)")
    print("=" * 52)
    print()

    started = time.time()

    # ------------------------------------------------------------------ #
    # Stage 1: rules
    # ------------------------------------------------------------------ #
    print("  [1/2] Running rule-based matcher...")
    rule_result = rules.run(SETTLEMENTS, BANK)
    rule_stats  = rule_result["stats"]

    print("        Matched by rules : %d" % rule_stats["matched"])
    print("        Unmatched        : %d" % rule_stats["exceptions"])
    print()

    # Build the pool of still-unclaimed bank lines
    all_bank      = {r["bank_txn_id"]: r for r in load_csv(BANK)}
    claimed_by_rules = {m["bank_txn_id"] for m in rule_result["matches"]}
    unclaimed_bank   = {bid: row for bid, row in all_bank.items()
                        if bid not in claimed_by_rules}

    # Build the list of unmatched settlements (in original order)
    matched_ids   = {m["settlement_id"] for m in rule_result["matches"]}
    all_settlements = load_csv(SETTLEMENTS)
    unmatched_settlements = [s for s in all_settlements
                             if s["settlement_id"] not in matched_ids]

    # ------------------------------------------------------------------ #
    # Stage 1.5: batch detector (pure arithmetic, no AI)
    # ------------------------------------------------------------------ #
    print("  [1.5] Running batch detector...")
    batch_groups, batch_claimed = batch_detector.detect(unmatched_settlements, unclaimed_bank)

    batch_matches   = []
    batch_used_sids = set()
    for grp in batch_groups:
        for sid in grp["settlement_ids"]:
            batch_matches.append({
                "settlement_id": sid,
                "bank_txn_id":   grp["bank_txn_id"],
                "strategy":      "BATCH",
                "confidence":    0.99,
                "reason":        grp["reason"],
            })
            batch_used_sids.add(sid)
        # Remove claimed bank line from pool
        unclaimed_bank.pop(grp["bank_txn_id"], None)

    print("        Batch groups found : %d (%d settlements)" % (
        len(batch_groups), len(batch_used_sids)))

    # Remove batch-matched settlements from the AI queue
    unmatched_settlements = [s for s in unmatched_settlements
                             if s["settlement_id"] not in batch_used_sids]

    # ------------------------------------------------------------------ #
    # Stage 2: AI agent
    # ------------------------------------------------------------------ #
    print("  [2/2] Running AI agent on %d unmatched records..." % len(unmatched_settlements))
    print("        (this makes %d API calls — may take 20-40s)" % len(unmatched_settlements))
    print()

    agent_results = agent.run_batch(unmatched_settlements, unclaimed_bank)

    # ------------------------------------------------------------------ #
    # Combine results
    # ------------------------------------------------------------------ #
    final_matches    = list(rule_result["matches"]) + batch_matches
    final_exceptions = []
    ai_matched       = 0
    ai_exceptions    = 0

    for res in agent_results:
        sid = res["settlement_id"]
        bid = res.get("bank_txn_id")
        conf = res.get("confidence", 0.0)

        if bid and conf >= CONFIDENCE_THRESHOLD and res["decision"] == "AI_MATCHED":
            final_matches.append({
                "settlement_id": sid,
                "bank_txn_id":   bid,
                "strategy":      "AI",
                "confidence":    conf,
                "reason":        res.get("reason", ""),
            })
            ai_matched += 1
        else:
            final_exceptions.append({
                "settlement_id": sid,
                "reason":        res.get("reason", res.get("decision", "ai_no_match")),
                "confidence":    conf,
            })
            ai_exceptions += 1

    elapsed = round(time.time() - started, 1)

    # ------------------------------------------------------------------ #
    # Score against ground truth
    # ------------------------------------------------------------------ #
    scoring = rules.score(final_matches, TRUTH)

    # ------------------------------------------------------------------ #
    # Write combined audit log
    # ------------------------------------------------------------------ #
    with open(AUDIT_LOG, "w", encoding="utf-8") as f:
        ts = datetime.now(timezone.utc).isoformat()

        for m in rule_result["matches"]:
            f.write(json.dumps({
                "ts": ts, "settlement_id": m["settlement_id"],
                "bank_txn_id": m["bank_txn_id"], "strategy": m["strategy"],
                "decision": "MATCHED", "confidence": 1.0,
                "reason": "rule: " + m["strategy"],
            }) + "\n")

        for m in batch_matches:
            f.write(json.dumps({
                "ts": ts, "settlement_id": m["settlement_id"],
                "bank_txn_id": m["bank_txn_id"], "strategy": "BATCH",
                "decision": "MATCHED", "confidence": m["confidence"],
                "reason": m["reason"],
            }) + "\n")

        for res in agent_results:
            f.write(json.dumps({
                "ts": ts,
                "settlement_id": res["settlement_id"],
                "bank_txn_id":   res.get("bank_txn_id") or "",
                "strategy":      "AI",
                "decision":      res.get("decision", ""),
                "confidence":    res.get("confidence", 0.0),
                "reason":        res.get("reason", ""),
            }) + "\n")

    # ------------------------------------------------------------------ #
    # Print results
    # ------------------------------------------------------------------ #
    print("=" * 52)
    print("  RESULTS")
    print("=" * 52)
    print()
    print("  Total settlements    : %d" % len(all_settlements))
    print()
    print("  Stage 1 — Rules")
    print("    Matched            : %d" % rule_stats["matched"])
    print()
    print("  Stage 2 — AI Agent")
    print("    Matched            : %d" % ai_matched)
    print("    Exceptions         : %d" % ai_exceptions)
    print()
    print("  Combined")
    print("    Total matched      : %d" % len(final_matches))
    print("    Total exceptions   : %d" % len(final_exceptions))
    print("    Match rate         : %.1f%%" % (len(final_matches) / len(all_settlements) * 100))
    print()
    print("  Accuracy (vs ground truth)")
    print("    Correct            : %d / %d" % (scoring["correct"], scoring["total"]))
    print("    Incorrect          : %d" % scoring["incorrect"])
    print("    Missed             : %d" % scoring["missing"])
    print("    Accuracy           : %s%%" % scoring["accuracy"])
    print()
    print("  Baseline (rules only): 75.0%%")
    print("  Full pipeline        : %s%%" % scoring["accuracy"])
    delta = round(scoring["accuracy"] - 75.0, 1)
    sign  = "+" if delta >= 0 else ""
    print("  AI contribution      : %s%s%%" % (sign, delta))
    print()
    print("  Time                 : %ss" % elapsed)
    print("  Throughput           : %s rec/s" % round(len(all_settlements) / elapsed, 1))
    print()
    print("  Audit log            : data/audit_log_full.jsonl")
    print()

    if final_exceptions:
        print("  --- Exceptions (requires human review) ---")
        for e in final_exceptions:
            conf_str = "conf=%.2f" % e.get("confidence", 0)
            print("  %-12s  %s  %s" % (e["settlement_id"], conf_str, e["reason"][:60]))
        print()

    # Sample of AI matches with their reasoning
    ai_match_list = [m for m in final_matches if m.get("strategy") == "AI"]
    if ai_match_list:
        print("  --- AI matches (sample) ---")
        for m in ai_match_list[:6]:
            print("  %-12s -> %-10s  conf=%.2f" % (
                m["settlement_id"], m["bank_txn_id"], m["confidence"]))
            if m.get("reason"):
                print("               %s" % m["reason"][:70])
        print()


if __name__ == "__main__":
    main()
