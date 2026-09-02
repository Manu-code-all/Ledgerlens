"""
Scale test — proves the deterministic stages (rules + batch detector) don't
fall over as record count grows well past the 64-record demo dataset.

Takes the existing settlements.csv / bank_statement.csv and replicates them
N times with unique IDs, then times Stage 1 + Stage 1.5 against the larger
set. The AI stage (Stage 2) is intentionally excluded here — it makes one
sequential API call per unmatched record, so its throughput is bounded by
network latency, not by this codebase. That tradeoff is called out in the
README's Limitations section.

Usage:
    python engine/scale_test.py            # default: 16x replication (~1024 rows)
    python engine/scale_test.py 50         # 50x replication (~3200 rows)
"""

import csv
import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
import rules
import batch_detector

ROOT   = os.path.join(os.path.dirname(__file__), "..")
SETL   = os.path.join(ROOT, "data", "settlements.csv")
BANK   = os.path.join(ROOT, "data", "bank_statement.csv")
OUT_SETL = os.path.join(ROOT, "data", "_scale_settlements.csv")
OUT_BANK = os.path.join(ROOT, "data", "_scale_bank.csv")


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def shift_date(date_str, days):
    d = datetime.strptime(date_str, "%Y-%m-%d").date() + timedelta(days=days)
    return d.isoformat()


def replicate(multiplier):
    """
    Replicate the base dataset `multiplier` times, shifting each replica's
    dates forward by one dataset-width (28 days) so it represents another
    month of the SAME business, not more transactions crammed into the same
    28 days. This is the realistic way settlement volume grows over time.
    """
    base_setl = load_csv(SETL)
    base_bank = load_csv(BANK)
    span_days = 28

    all_setl = []
    all_bank = []
    for r in range(multiplier):
        offset = r * span_days
        for row in base_setl:
            copy = dict(row)
            copy["settlement_id"]   = "%s-R%d" % (row["settlement_id"], r)
            copy["order_id"]        = "%s-R%d" % (row["order_id"], r)
            copy["settlement_date"] = shift_date(row["settlement_date"], offset)
            all_setl.append(copy)
        for row in base_bank:
            copy = dict(row)
            copy["bank_txn_id"] = "%s-R%d" % (row["bank_txn_id"], r)
            copy["value_date"]  = shift_date(row["value_date"], offset)
            all_bank.append(copy)

    with open(OUT_SETL, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(all_setl[0].keys()))
        w.writeheader()
        w.writerows(all_setl)
    with open(OUT_BANK, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(all_bank[0].keys()))
        w.writeheader()
        w.writerows(all_bank)

    return len(all_setl), len(all_bank)


def main():
    multiplier = int(sys.argv[1]) if len(sys.argv) > 1 else 16

    print("=" * 52)
    print("  LedgerLens — Scale Test (Rules + Batch Detector)")
    print("=" * 52)
    print()
    print("  Replicating base dataset x%d..." % multiplier)

    n_setl, n_bank = replicate(multiplier)
    print("  Settlements : %d" % n_setl)
    print("  Bank lines  : %d" % n_bank)
    print()

    started = time.time()

    rule_result = rules.run(OUT_SETL, OUT_BANK)

    all_bank = {r["bank_txn_id"]: r for r in load_csv(OUT_BANK)}
    claimed = {m["bank_txn_id"] for m in rule_result["matches"]}
    unclaimed_bank = {bid: row for bid, row in all_bank.items() if bid not in claimed}

    matched_ids = {m["settlement_id"] for m in rule_result["matches"]}
    all_setl = load_csv(OUT_SETL)
    unmatched = [s for s in all_setl if s["settlement_id"] not in matched_ids]

    batch_groups, batch_claimed = batch_detector.detect(unmatched, unclaimed_bank)

    elapsed = round(time.time() - started, 2)
    total_matched = len(rule_result["matches"]) + sum(len(g["settlement_ids"]) for g in batch_groups)

    print("  Rules matched        : %d" % len(rule_result["matches"]))
    print("  Batch groups found   : %d (%d settlements)" % (
        len(batch_groups), sum(len(g["settlement_ids"]) for g in batch_groups)))
    print("  Total matched        : %d / %d (%.1f%%)" % (
        total_matched, n_setl, total_matched / n_setl * 100))
    print()
    print("  Elapsed time         : %ss" % elapsed)
    print("  Throughput           : %s records/sec" % round(n_setl / elapsed, 1))
    print()

    # Clean up the temp files — this test dataset is not meant to be reused.
    os.remove(OUT_SETL)
    os.remove(OUT_BANK)


if __name__ == "__main__":
    main()
