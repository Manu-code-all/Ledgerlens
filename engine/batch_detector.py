"""
Batch payout detector — Stage 1.5 between rules and the AI agent.

Problem: Razorpay sometimes pays out multiple settlements in a single bank
credit. One bank line shows, say, 68,000 and three settlements individually
sum to that amount after fees. Rules see a mismatch; the AI (called one
settlement at a time) can't group them either.

Solution: pure arithmetic. For every subset of 2-3 unmatched settlements,
compute their combined net-of-fee amount and check if it matches an
unclaimed bank line within a small tolerance. No AI needed.

Returns the matched groups so run_full.py can claim those bank lines before
the AI stage.
"""

from itertools import combinations


FEE_RATE    = 0.02        # 2% platform fee
GST_RATE    = 0.18        # 18% GST on the fee
TOLERANCE   = 0.05        # Rs 0.05 rounding tolerance
MAX_LAG     = 3           # bank date may be up to 3 days after settlement date
MAX_GROUP   = 3           # look for groups of 2 or 3


def net_of_fees(gross_str):
    gross = float(gross_str)
    fee   = round(gross * FEE_RATE + 1e-9, 2)
    gst   = round(fee   * GST_RATE + 1e-9, 2)
    return round(gross - fee - gst + 1e-9, 2)


def date_to_int(date_str):
    """Convert 'YYYY-MM-DD' to integer days since epoch for arithmetic."""
    from datetime import date
    y, m, d = date_str.split("-")
    return (date(int(y), int(m), int(d)) - date(2026, 1, 1)).days


def detect(unmatched_settlements, unclaimed_bank):
    """
    Find batch groups among unmatched settlements.

    unmatched_settlements : list of settlement dicts
    unclaimed_bank        : dict {bank_txn_id: bank_row}

    Returns:
      groups   - list of {bank_txn_id, settlement_ids, combined_net, reason}
      claimed  - set of bank_txn_ids claimed by batch matches
    """
    groups  = []
    claimed = set()                      # bank lines claimed so far
    used    = set()                      # settlement ids used so far

    # Index bank lines for quick lookup
    bank_list = [row for bid, row in unclaimed_bank.items() if bid not in claimed]

    for size in range(2, MAX_GROUP + 1):
        for combo in combinations(unmatched_settlements, size):
            # Skip if any settlement in this combo already claimed
            if any(s["settlement_id"] in used for s in combo):
                continue

            # All settlements in a batch share the same settlement date
            dates = {s["settlement_date"] for s in combo}
            if len(dates) > 1:
                continue                 # different dates — not a batch

            setl_date_int = date_to_int(combo[0]["settlement_date"])
            combined_net  = sum(net_of_fees(s["gross_amount"]) for s in combo)
            combined_net  = round(combined_net + 1e-9, 2)

            # Look for a matching bank line
            for bank_row in bank_list:
                if bank_row["bank_txn_id"] in claimed:
                    continue

                bank_amount   = float(bank_row["credit_amount"])
                bank_date_int = date_to_int(bank_row["value_date"])

                amount_ok = abs(bank_amount - combined_net) <= TOLERANCE
                date_ok   = 0 <= (bank_date_int - setl_date_int) <= MAX_LAG

                if amount_ok and date_ok:
                    bid = bank_row["bank_txn_id"]
                    sids = [s["settlement_id"] for s in combo]
                    groups.append({
                        "bank_txn_id":     bid,
                        "settlement_ids":  sids,
                        "combined_net":    combined_net,
                        "reason": (
                            "Batch: %d settlements sum to %.2f "
                            "(bank shows %.2f, diff %.4f)" % (
                                size, combined_net, bank_amount,
                                abs(bank_amount - combined_net)
                            )
                        ),
                    })
                    claimed.add(bid)
                    for sid in sids:
                        used.add(sid)
                    break             # found a bank line for this combo

    return groups, claimed
