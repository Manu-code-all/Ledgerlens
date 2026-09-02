"""
Tests for the arithmetic batch detector (engine/batch_detector.py) — Stage 1.5.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import batch_detector as bd


def bank_row(bid, amount, date):
    return {"bank_txn_id": bid, "credit_amount": str(amount), "value_date": date}


def settlement(sid, gross, date):
    return {"settlement_id": sid, "gross_amount": str(gross), "settlement_date": date}


def test_net_of_fees_applies_mdr_and_gst():
    # 1000 gross, 2% fee = 20, 18% GST on fee = 3.60 -> net 976.40
    assert bd.net_of_fees("1000.00") == 976.40


def test_two_settlement_batch_is_detected():
    settlements = [
        settlement("S1", 500.00, "2026-08-10"),
        settlement("S2", 300.00, "2026-08-10"),
    ]
    net_total = bd.net_of_fees("500.00") + bd.net_of_fees("300.00")
    unclaimed = {"B1": bank_row("B1", round(net_total, 2), "2026-08-10")}

    groups, claimed = bd.detect(settlements, unclaimed)

    assert len(groups) == 1
    assert set(groups[0]["settlement_ids"]) == {"S1", "S2"}
    assert "B1" in claimed


def test_three_settlement_batch_is_detected():
    settlements = [
        settlement("S1", 500.00, "2026-08-10"),
        settlement("S2", 300.00, "2026-08-10"),
        settlement("S3", 200.00, "2026-08-10"),
    ]
    net_total = sum(bd.net_of_fees(str(g)) for g in (500.00, 300.00, 200.00))
    unclaimed = {"B1": bank_row("B1", round(net_total, 2), "2026-08-10")}

    groups, claimed = bd.detect(settlements, unclaimed)

    assert len(groups) == 1
    assert len(groups[0]["settlement_ids"]) == 3


def test_no_batch_when_amounts_dont_add_up():
    settlements = [
        settlement("S1", 500.00, "2026-08-10"),
        settlement("S2", 300.00, "2026-08-10"),
    ]
    unclaimed = {"B1": bank_row("B1", 999999.00, "2026-08-10")}

    groups, claimed = bd.detect(settlements, unclaimed)

    assert groups == []
    assert claimed == set()


def test_settlements_on_different_dates_are_not_batched():
    settlements = [
        settlement("S1", 500.00, "2026-08-10"),
        settlement("S2", 300.00, "2026-08-11"),   # different date
    ]
    net_total = bd.net_of_fees("500.00") + bd.net_of_fees("300.00")
    unclaimed = {"B1": bank_row("B1", round(net_total, 2), "2026-08-10")}

    groups, claimed = bd.detect(settlements, unclaimed)

    assert groups == []


def test_higher_fee_rate_changes_which_bank_line_matches():
    # At 2% fee the batch nets to 776.20; a bank line showing that exact
    # amount should only match when fee_rate=0.02, not at a higher rate.
    settlements = [
        settlement("S1", 500.00, "2026-08-10"),
        settlement("S2", 300.00, "2026-08-10"),
    ]
    net_at_2pct = bd.net_of_fees("500.00") + bd.net_of_fees("300.00")
    unclaimed = {"B1": bank_row("B1", round(net_at_2pct, 2), "2026-08-10")}

    groups_default, _ = bd.detect(settlements, dict(unclaimed), fee_rate=0.02)
    groups_high_fee, _ = bd.detect(settlements, dict(unclaimed), fee_rate=0.05)

    assert len(groups_default) == 1
    assert len(groups_high_fee) == 0


def test_date_window_controls_how_late_a_batch_credit_can_land():
    settlements = [
        settlement("S1", 500.00, "2026-08-10"),
        settlement("S2", 300.00, "2026-08-10"),
    ]
    net_total = bd.net_of_fees("500.00") + bd.net_of_fees("300.00")
    # Bank credit lands 5 days later
    unclaimed = {"B1": bank_row("B1", round(net_total, 2), "2026-08-15")}

    groups_narrow, _ = bd.detect(settlements, dict(unclaimed), date_window=3)
    groups_wide, _   = bd.detect(settlements, dict(unclaimed), date_window=5)

    assert groups_narrow == []
    assert len(groups_wide) == 1
