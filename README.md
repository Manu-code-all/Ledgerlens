# LedgerLens — AI Reconciliation Controller

**Razorpay Hackathon · Track 4: AI Finance Controller**

Reconciles payment settlements against a bank statement across a batch of 60+
synthetic records, and reports match rate, accuracy, exceptions and throughput.

---

## The problem

A finance team ends the month with two lists that are supposed to agree:

| The gateway says it paid out | What the bank actually shows |
| --- | --- |
| `settlements.csv` | `bank_statement.csv` |

They never line up cleanly:

- **Fees** — the bank credit is short by a platform fee plus GST on that fee
- **Settlement lag** — money lands 1–3 days after the settlement date
- **Garbled references** — bank narration truncates `ORD-7049` to `ORD-70`
- **Batched payouts** — one bank credit covers three separate settlements
- **Ambiguity** — two orders, same amount, same day, indistinguishable by rule
- **Genuinely missing money** — a settlement whose credit never arrived

Rule-based matching resolves the clean cases and then quietly guesses at the
rest. Someone reconciles the remainder by hand.

## The approach

Two stages, deliberately in this order:

1. **Deterministic rules first.** Exact reference and amount matches are cheap,
   instant and provably correct. No reason to spend an AI call on them.
2. **AI agent for the residue.** Only unmatched records escalate. The agent
   reasons about fee deltas, date windows, mangled references and one-to-many
   groupings, and returns a match, a confidence score, and a written
   justification.

Every decision — rule or agent — is written to an audit log.

## Reported metrics

| Metric | Meaning |
| --- | --- |
| Match rate | Share of settlements assigned to a bank line |
| Accuracy | Share of those assignments that are correct, vs. ground truth |
| Exceptions | Flagged for human review rather than auto-resolved |
| Unresolvable | Honestly reported as impossible to match |
| Throughput | Records processed per second |

Rules alone establish the baseline. The agent's contribution is measured as the
delta above it.

## Dataset

`engine/generate_data.py` builds the batch from a fixed seed, so every run is
reproducible.

| Category | Count | What it tests |
| --- | --- | --- |
| CLEAN | 24 | Baseline — rules should get all of these |
| FEE | 12 | Amount differs by fee + GST |
| LAG | 8 | Fee *and* a 1–3 day delay |
| GARBLED | 6 | Reference partially destroyed |
| BATCH | 6 | Three settlements, one bank credit |
| AMBIGUOUS | 4 | Identical amount and date |
| MISSING | 4 | Correct answer is "no match" |
| ORPHAN | 3 | Bank credits that aren't settlements at all |

`data/ground_truth.csv` holds the answer key and is used only for scoring —
never read by the matcher.

## Running it

```bash
python engine/generate_data.py
```

## Status

- [x] Synthetic data generator with planted, categorised failure modes
- [ ] Rule-based matcher (baseline)
- [ ] AI agent for unmatched residue
- [ ] Metrics + audit trail
- [ ] FastAPI service
- [ ] React dashboard
