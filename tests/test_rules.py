"""
Tests for the deterministic rule-based matcher (engine/rules.py).
"""

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import rules


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


SETL_FIELDS = ["settlement_id", "order_id", "gross_amount", "settlement_date"]
BANK_FIELDS = ["bank_txn_id", "value_date", "credit_amount", "description"]


def make_files(tmp_path, settlements, bank_rows):
    setl_path = tmp_path / "settlements.csv"
    bank_path = tmp_path / "bank.csv"
    write_csv(setl_path, settlements, SETL_FIELDS)
    write_csv(bank_path, bank_rows, BANK_FIELDS)
    return str(setl_path), str(bank_path)


def test_strategy1_reference_match(tmp_path):
    settlements = [{"settlement_id": "S1", "order_id": "ORD-7049",
                     "gross_amount": "1000.00", "settlement_date": "2026-08-01"}]
    bank_rows = [{"bank_txn_id": "B1", "value_date": "2026-08-01",
                  "credit_amount": "976.40", "description": "RZPY*ORD-7049 NEFT CR"}]
    setl_path, bank_path = make_files(tmp_path, settlements, bank_rows)

    result = rules.run(setl_path, bank_path)

    assert len(result["matches"]) == 1
    assert result["matches"][0]["strategy"] == "REF"
    assert result["matches"][0]["bank_txn_id"] == "B1"


def test_strategy2_amount_and_date_match(tmp_path):
    settlements = [{"settlement_id": "S1", "order_id": "ORD-9999",
                     "gross_amount": "500.00", "settlement_date": "2026-08-05"}]
    bank_rows = [{"bank_txn_id": "B1", "value_date": "2026-08-05",
                  "credit_amount": "500.00", "description": "unrelated narration"}]
    setl_path, bank_path = make_files(tmp_path, settlements, bank_rows)

    result = rules.run(setl_path, bank_path, date_window=0)

    assert len(result["matches"]) == 1
    assert result["matches"][0]["strategy"] == "AMT+DATE"


def test_date_window_zero_rejects_lagged_credit(tmp_path):
    settlements = [{"settlement_id": "S1", "order_id": "ORD-1",
                     "gross_amount": "500.00", "settlement_date": "2026-08-05"}]
    bank_rows = [{"bank_txn_id": "B1", "value_date": "2026-08-07",  # 2 days later
                  "credit_amount": "500.00", "description": "unrelated"}]
    setl_path, bank_path = make_files(tmp_path, settlements, bank_rows)

    result = rules.run(setl_path, bank_path, date_window=0)

    assert len(result["matches"]) == 0
    assert len(result["exceptions"]) == 1


def test_date_window_extends_match_within_range(tmp_path):
    settlements = [{"settlement_id": "S1", "order_id": "ORD-1",
                     "gross_amount": "500.00", "settlement_date": "2026-08-05"}]
    bank_rows = [{"bank_txn_id": "B1", "value_date": "2026-08-07",  # 2 days later
                  "credit_amount": "500.00", "description": "unrelated"}]
    setl_path, bank_path = make_files(tmp_path, settlements, bank_rows)

    result = rules.run(setl_path, bank_path, date_window=3)

    assert len(result["matches"]) == 1
    assert result["matches"][0]["strategy"] == "AMT+DATE"


def test_no_matching_bank_line_goes_to_exceptions(tmp_path):
    settlements = [{"settlement_id": "S1", "order_id": "ORD-1",
                     "gross_amount": "500.00", "settlement_date": "2026-08-05"}]
    bank_rows = [{"bank_txn_id": "B1", "value_date": "2026-08-05",
                  "credit_amount": "999.00", "description": "no relation"}]
    setl_path, bank_path = make_files(tmp_path, settlements, bank_rows)

    result = rules.run(setl_path, bank_path)

    assert len(result["matches"]) == 0
    assert result["exceptions"][0]["settlement_id"] == "S1"


def test_bank_line_can_only_be_claimed_once(tmp_path):
    # Two settlements both point at the same bank line by reference match.
    settlements = [
        {"settlement_id": "S1", "order_id": "ORD-SAME",
         "gross_amount": "500.00", "settlement_date": "2026-08-05"},
        {"settlement_id": "S2", "order_id": "ORD-SAME",
         "gross_amount": "500.00", "settlement_date": "2026-08-05"},
    ]
    bank_rows = [{"bank_txn_id": "B1", "value_date": "2026-08-05",
                  "credit_amount": "500.00", "description": "RZPY*ORD-SAME"}]
    setl_path, bank_path = make_files(tmp_path, settlements, bank_rows)

    result = rules.run(setl_path, bank_path)

    # Only one of the two can win the single bank line.
    assert len(result["matches"]) == 1
    assert len(result["exceptions"]) == 1


def test_score_counts_correct_incorrect_and_missing(tmp_path):
    truth_path = tmp_path / "truth.csv"
    write_csv(truth_path, [
        {"settlement_id": "S1", "bank_txn_id": "B1"},
        {"settlement_id": "S2", "bank_txn_id": "B2"},
        {"settlement_id": "S3", "bank_txn_id": ""},   # correct answer is "no match"
    ], ["settlement_id", "bank_txn_id"])

    matches = [
        {"settlement_id": "S1", "bank_txn_id": "B1"},   # correct
        {"settlement_id": "S2", "bank_txn_id": "B9"},   # incorrect — wrong bank line
        # S3 has no match in our results, and truth says no match too -> correct
    ]

    scoring = rules.score(matches, str(truth_path))

    assert scoring["correct"] == 2
    assert scoring["incorrect"] == 1
    assert scoring["total"] == 3
