"""
AI agent for reconciling the hard cases the rule-based matcher could not resolve.

Only called for settlements that rules left unmatched. For each one, it:
  1. Builds a prompt describing the settlement and all remaining bank lines
  2. Sends it to Groq (qwen3.8-27b)
  3. Parses the JSON response: match, confidence, reason
  4. Returns the result for audit logging

The model is asked to return strict JSON — no prose, no markdown fences.
If the JSON parse fails, the record is escalated as an exception rather than
silently guessing.
"""

import json
import os
import time

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = "qwen/qwen3.8-27b"
MAX_TOKENS = 512

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set in .env")
        _client = Groq(api_key=api_key)
    return _client


SYSTEM_PROMPT = """You are a financial reconciliation assistant.
You will be given one payment settlement record and a list of bank credit lines.
Your job is to find which bank line best matches the settlement, or determine that no match exists.

Rules you must follow:
- Gateway fee is 2% of gross amount, then 18% GST on that fee. Bank credit = gross - fee - GST.
- Bank credit may arrive 1-3 days after the settlement date.
- Bank narration may be truncated or garbled — partial order ID matches are valid clues.
- One bank line may cover multiple settlements (batch payout) — in that case the bank amount equals the SUM of net amounts.
- If no bank line is a plausible match, return bank_txn_id as null.

Respond ONLY with a JSON object. No markdown, no explanation, no extra text. Format:
{
  "bank_txn_id": "BANK-XXXX or null",
  "confidence": 0.0 to 1.0,
  "reason": "one sentence explaining why this is the best match"
}"""


def _build_prompt(settlement, bank_candidates):
    """Build the user message for one unmatched settlement."""
    lines = [
        "SETTLEMENT TO MATCH:",
        "  settlement_id : " + settlement["settlement_id"],
        "  order_id      : " + settlement["order_id"],
        "  gross_amount  : " + settlement["gross_amount"],
        "  date          : " + settlement["settlement_date"],
        "",
        "AVAILABLE BANK LINES:",
    ]
    for b in bank_candidates:
        lines.append(
            "  %s | %s | %s | %s"
            % (b["bank_txn_id"], b["value_date"], b["credit_amount"], b["description"])
        )
    return "\n".join(lines)


def resolve(settlement, bank_candidates, retries=2):
    """
    Ask the AI to match one settlement against the remaining bank lines.

    Returns a dict:
      bank_txn_id  - matched id, or None
      confidence   - float 0-1
      reason       - the model's written justification (this is the audit trail)
      used_ai      - always True
      error        - set only if parsing failed after all retries
    """
    client = _get_client()
    prompt = _build_prompt(settlement, bank_candidates)

    last_error = None
    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                max_tokens=MAX_TOKENS,
                temperature=0.1,   # low temperature = more deterministic
            )
            raw = response.choices[0].message.content.strip()

            # Strip markdown fences if the model added them despite instructions
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            parsed = json.loads(raw)
            bid = parsed.get("bank_txn_id")
            if bid == "null" or bid == "":
                bid = None

            return {
                "bank_txn_id": bid,
                "confidence":  float(parsed.get("confidence", 0.5)),
                "reason":      parsed.get("reason", ""),
                "used_ai":     True,
            }

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            last_error = str(e)
            time.sleep(1)   # brief pause before retry

    # All retries exhausted — escalate rather than guess
    return {
        "bank_txn_id": None,
        "confidence":  0.0,
        "reason":      "AI parse failed after retries: " + last_error,
        "used_ai":     True,
        "error":       last_error,
    }


def run_batch(unmatched_settlements, bank_candidates):
    """
    Resolve a list of unmatched settlements.

    bank_candidates is a dict of {bank_txn_id: row} — the pool of
    still-unclaimed bank lines passed in from the rules stage.

    Returns a list of result dicts, one per settlement, in input order.
    Removes successfully matched bank lines from bank_candidates in-place
    so they cannot be claimed twice.
    """
    results = []
    remaining_bank = dict(bank_candidates)   # local copy we can shrink

    for settlement in unmatched_settlements:
        # Pass all remaining bank lines to each agent call.
        # The agent sees the full context — important for BATCH detection.
        candidates = list(remaining_bank.values())

        result = resolve(settlement, candidates)
        result["settlement_id"] = settlement["settlement_id"]

        bid = result.get("bank_txn_id")
        if bid and bid in remaining_bank:
            # Claimed — remove so no other settlement grabs it
            del remaining_bank[bid]
            result["decision"] = "AI_MATCHED"
        elif bid and bid not in remaining_bank:
            # Agent returned an id that was already claimed (hallucination guard)
            result["bank_txn_id"] = None
            result["decision"] = "AI_HALLUCINATION"
            result["reason"] += " [rejected: bank line already claimed]"
        else:
            result["decision"] = "AI_EXCEPTION"

        results.append(result)

    return results
