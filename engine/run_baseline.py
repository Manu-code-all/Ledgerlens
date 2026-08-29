"""
Run the rule-based baseline and print every number we care about.

Usage:
    python engine/run_baseline.py
"""

import os
import sys

# Allow "python engine/run_baseline.py" from the project root.
sys.path.insert(0, os.path.dirname(__file__))

import rules

ROOT        = os.path.join(os.path.dirname(__file__), "..")
SETTLEMENTS = os.path.join(ROOT, "data", "settlements.csv")
BANK        = os.path.join(ROOT, "data", "bank_statement.csv")
TRUTH       = os.path.join(ROOT, "data", "ground_truth.csv")
AUDIT_LOG   = os.path.join(ROOT, "data", "audit_log_baseline.jsonl")

result  = rules.run(SETTLEMENTS, BANK, audit_log_path=AUDIT_LOG)
scoring = rules.score(result["matches"], TRUTH)
stats   = result["stats"]

print("=" * 48)
print("  LedgerLens — Rule-Based Baseline")
print("=" * 48)
print()
print("  Total settlements  : %d" % stats["total_settlements"])
print("  Matched            : %d" % stats["matched"])
print("  Exceptions         : %d" % stats["exceptions"])
print("  Unclaimed bank     : %d" % stats["unmatched_bank"])
print("  Time               : %.3fs" % stats["elapsed_seconds"])
print("  Throughput         : %s rec/s" % stats["throughput"])
print()
print("  --- Accuracy (vs ground truth) ---")
print("  Correct            : %d / %d" % (scoring["correct"], scoring["total"]))
print("  Incorrect          : %d" % scoring["incorrect"])
print("  Missed (exception) : %d" % scoring["missing"])
print("  Accuracy           : %s%%" % scoring["accuracy"])
print()
print("  Audit log          : data/audit_log_baseline.jsonl")
print()

# Per-match breakdown (first 10 lines, so the terminal doesn't scroll off)
print("  --- Sample matches (first 10) ---")
for m in result["matches"][:10]:
    print("  %-12s -> %-10s via %s" % (
        m["settlement_id"], m["bank_txn_id"], m["strategy"]))

if result["exceptions"]:
    print()
    print("  --- Exceptions (first 10) ---")
    for e in result["exceptions"][:10]:
        print("  %-12s  no match found" % e["settlement_id"])

print()
