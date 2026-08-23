"""
Synthetic data generator for LedgerLens.

Produces three files in ../data/:
  settlements.csv    - what the payment gateway says it paid out
  bank_statement.csv - what actually landed in the bank account
  ground_truth.csv   - the correct answer key (settlement -> bank line)

The two CSVs deliberately DO NOT line up cleanly. Real reconciliation is hard
because of gateway fees, settlement lag, mangled bank references, batched
payouts and genuinely missing money. We plant each of those on purpose so we
can later measure how well the matcher handles them.

Everything is seeded, so running this twice gives identical files. That matters:
our accuracy numbers have to be reproducible.
"""

import csv
import os
import random
from datetime import date, timedelta

SEED = 20260823
random.seed(SEED)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
START_DATE = date(2026, 7, 1)

# How many settlements of each kind to create.
# Total must be >= 50 to satisfy the track requirement.
MIX = {
    "CLEAN": 24,        # amount and date match exactly, reference is intact
    "FEE": 12,          # bank got less: gateway fee + GST deducted
    "LAG": 8,           # money arrived 1-3 days late (T+2 settlement)
    "GARBLED": 6,       # bank reference is truncated or mangled
    "BATCH": 6,         # 3 settlements paid out as ONE bank credit (x2 groups)
    "AMBIGUOUS": 4,     # same amount, same day, different orders (2 pairs)
    "MISSING": 4,       # settlement exists but money never arrived
}
ORPHAN_BANK_LINES = 3   # bank credits with no matching settlement at all

CUSTOMERS = [
    "Aarav Sharma", "Diya Nair", "Kabir Menon", "Ishita Rao", "Vivaan Patel",
    "Ananya Iyer", "Rohan Gupta", "Meera Joshi", "Arjun Reddy", "Sana Khan",
]


def money(value):
    """Round to 2 decimals the way an accountant would."""
    return round(value + 1e-9, 2)


def net_of_fees(gross):
    """Razorpay-style deduction: 2% platform fee, then 18% GST on that fee."""
    fee = money(gross * 0.02)
    gst = money(fee * 0.18)
    return money(gross - fee - gst)


def garble(ref):
    """Mangle a reference the way a bank narration field would."""
    style = random.choice(["truncate", "nospace", "suffix", "case"])
    if style == "truncate":
        return ref[:6]  # "ORD-7049" -> "ORD-70": digits genuinely lost
    if style == "nospace":
        return ref.replace("-", "")
    if style == "suffix":
        return ref + "-PART"
    return ref.lower()


def write_csv(filename, rows, fieldnames):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print("wrote " + os.path.normpath(path))


def main():
    settlements = []   # rows for settlements.csv
    bank_rows = []     # rows for bank_statement.csv
    truth = []         # (settlement_id, bank_txn_id, category)

    counters = {"settlement": 0, "bank": 0}

    def next_settlement(gross=None, day_offset=None):
        """Create one settlement row. Returns (row, gross, day_offset)."""
        counters["settlement"] += 1
        n = counters["settlement"]
        sid = "SETL-%04d" % n
        order_id = "ORD-%d" % (7000 + n)
        if gross is None:
            gross = money(random.uniform(499, 48000))
        if day_offset is None:
            day_offset = random.randint(0, 27)
        row = {
            "settlement_id": sid,
            "order_id": order_id,
            "customer": random.choice(CUSTOMERS),
            "gross_amount": "%.2f" % gross,
            "settlement_date": (START_DATE + timedelta(days=day_offset)).isoformat(),
        }
        settlements.append(row)
        return row, gross, day_offset

    def next_bank(amount, day_offset, description):
        """Create one bank credit line. Returns its id."""
        counters["bank"] += 1
        bid = "BANK-%04d" % counters["bank"]
        bank_rows.append({
            "bank_txn_id": bid,
            "value_date": (START_DATE + timedelta(days=day_offset)).isoformat(),
            "credit_amount": "%.2f" % amount,
            "description": description,
        })
        return bid

    # ---- CLEAN: the easy ones. Rules alone should get all of these. ----
    for _ in range(MIX["CLEAN"]):
        row, gross, day = next_settlement()
        bid = next_bank(gross, day, "RZPY*" + row["order_id"] + " NEFT CR")
        truth.append((row["settlement_id"], bid, "CLEAN"))

    # ---- FEE: amount is short by fee + GST. Exact-amount matching fails. ----
    for _ in range(MIX["FEE"]):
        row, gross, day = next_settlement()
        bid = next_bank(net_of_fees(gross), day, "RZPY*" + row["order_id"] + " SETTL")
        truth.append((row["settlement_id"], bid, "FEE"))

    # ---- LAG: fee deducted AND money arrives 1-3 days later. ----
    for _ in range(MIX["LAG"]):
        row, gross, day = next_settlement(day_offset=random.randint(0, 24))
        lag = random.randint(1, 3)
        bid = next_bank(net_of_fees(gross), day + lag,
                        "RZPY*" + row["order_id"] + " SETTL T+" + str(lag))
        truth.append((row["settlement_id"], bid, "LAG"))

    # ---- GARBLED: reference unreadable, so only amount + date can guide us. ----
    for _ in range(MIX["GARBLED"]):
        row, gross, day = next_settlement()
        bid = next_bank(net_of_fees(gross), day, "RZPY" + garble(row["order_id"]) + "/CR")
        truth.append((row["settlement_id"], bid, "GARBLED"))

    # ---- BATCH: 3 settlements collapse into 1 bank credit. One-to-many. ----
    for group in range(MIX["BATCH"] // 3):
        day = random.randint(0, 25)
        members = []
        total = 0.0
        for _ in range(3):
            row, gross, _ = next_settlement(day_offset=day)
            members.append(row["settlement_id"])
            total += net_of_fees(gross)
        bid = next_bank(money(total), day,
                        "RZPY PAYOUT BATCH-%d %d TXNS" % (group + 1, len(members)))
        for sid in members:
            truth.append((sid, bid, "BATCH"))

    # ---- AMBIGUOUS: identical amount, identical day. Rules cannot choose. ----
    for _ in range(MIX["AMBIGUOUS"] // 2):
        day = random.randint(0, 25)
        gross = money(random.uniform(1500, 9000))
        for _ in range(2):
            row, g, _ = next_settlement(gross=gross, day_offset=day)
            bid = next_bank(net_of_fees(g), day, "RZPY SETTLEMENT CREDIT")
            truth.append((row["settlement_id"], bid, "AMBIGUOUS"))

    # ---- MISSING: money genuinely never arrived. Correct answer is "no match". ----
    for _ in range(MIX["MISSING"]):
        row, _, _ = next_settlement()
        truth.append((row["settlement_id"], "", "MISSING"))

    # ---- ORPHANS: bank credits that are not settlements at all. ----
    orphan_descriptions = [
        "IMPS CR FROM VENDOR REFUND",
        "INT.CREDIT SAVINGS A/C",
        "NEFT CR ACME SUPPLIES PVT LTD",
    ]
    for i in range(ORPHAN_BANK_LINES):
        next_bank(money(random.uniform(2000, 30000)),
                  random.randint(0, 27),
                  orphan_descriptions[i % len(orphan_descriptions)])

    # Shuffle so the answer is not simply "row 1 matches row 1".
    random.shuffle(settlements)
    random.shuffle(bank_rows)

    # Renumber bank ids in their new shuffled order. Without this, the id
    # itself leaks the answer key: BANK-0046 would always pair with ORD-7046,
    # and a matcher could "win" by comparing trailing digits instead of
    # actually reconciling anything.
    remap = {}
    for i, row in enumerate(bank_rows, start=1):
        new_id = "BANK-%04d" % i
        remap[row["bank_txn_id"]] = new_id
        row["bank_txn_id"] = new_id
    truth = [(s, remap.get(b, ""), c) for s, b, c in truth]

    os.makedirs(DATA_DIR, exist_ok=True)
    write_csv("settlements.csv", settlements,
              ["settlement_id", "order_id", "customer", "gross_amount", "settlement_date"])
    write_csv("bank_statement.csv", bank_rows,
              ["bank_txn_id", "value_date", "credit_amount", "description"])
    write_csv("ground_truth.csv",
              [{"settlement_id": s, "bank_txn_id": b, "category": c} for s, b, c in truth],
              ["settlement_id", "bank_txn_id", "category"])

    print("")
    print("settlements   : %d" % len(settlements))
    print("bank lines    : %d" % len(bank_rows))
    print("truth entries : %d" % len(truth))
    print("")
    for name, count in MIX.items():
        print("  %-10s %d" % (name, count))
    print("  %-10s %d (bank-side only)" % ("ORPHAN", ORPHAN_BANK_LINES))


if __name__ == "__main__":
    main()
