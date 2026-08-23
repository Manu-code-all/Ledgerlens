# LedgerLens — Project Plan & Working Notes

Living reference for the Razorpay Hackathon build. Started 2026-08-23,
submission due **2026-09-05**.

---

## 1. The hackathon

Five tracks were offered. Summary of all five, for context on why we chose ours:

| # | Track | Objective | Evaluation bar |
| --- | --- | --- | --- |
| 01 | AI Growth & Agentic Commerce | Increase merchant revenue, or make merchants transactable by AI buyers | Money actions must be **explainable, bounded, gated**; audit trail; ≥1 failure scenario; graceful failure handling |
| 02 | AI Risk Manager | Reduce losses from fraud, returns, chargebacks, financial abuse | Precision, recall, **held-out test data**, false-positive cost. *Strictly defense-only — offensive capability is disqualifying* |
| 03 | AI Revenue Recovery | Identify revenue at risk → choose intervention → run a bounded recovery workflow | Measured money recovered, batch-level results, compliant escalation, stopping rules |
| **04** | **AI Finance Controller** | **Finance-ops workflow across ≥50 synthetic records** | **Match rate, accuracy, exceptions, unresolved records, throughput. "A single cherry-picked match is not sufficient"** |
| 05 | Open Track | Any meaningful problem outside the other four | Real problem, working product, meaningful AI usage, evidence of value, reliability, technical depth |

### Why Track 4

Chosen deliberately, on these grounds:

- **No external integration required.** No Razorpay API keys, no payment
  gateway, no live merchant account, no hosting. Tracks 01 and 03 all need at
  least one of those.
- **The spec permits self-generated data** — "a batch of at least 50 synthetic
  records." That removes the single biggest blocker for a first backend build.
- **The eval bar is arithmetic, not persuasion.** Match rate, accuracy,
  exceptions, throughput. Run the batch, print the numbers. Compare with Track
  03, which demands *measured money recovered* — hard to demonstrate honestly
  without a real payment loop.
- **No ML metrics prerequisite.** Track 02 requires precision/recall on held-out
  data and train/test discipline.

---

## 2. What we are building

**LedgerLens — AI Reconciliation Controller.**

Reconciles payment settlements against a bank statement across a 64-record
batch, and reports match rate, accuracy, exceptions and throughput.

### Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  React +Vite │───▶│   FastAPI    │───▶│  Reconciler  │
│  dashboard   │    │  2 endpoints │    │    engine    │
└──────────────┘    └──────────────┘    └──────────────┘
     known           ~40 lines           the real work
```

### The two-stage matcher

Order matters, and is itself part of the pitch:

1. **Deterministic rules first.** Exact reference and exact amount matches are
   cheap, instant and provably correct. Spending an AI call on them would be
   waste.
2. **AI agent on the residue only.** Unmatched records escalate to Claude,
   which reasons about fee deltas, date windows, mangled references and
   one-to-many groupings, returning a match, a confidence score and a written
   justification.

Every decision — rule or agent — is written to an audit log. The agent's
justification text *is* the audit trail.

Rules alone give the **baseline**. The agent's value is the measured delta above
it. Without a baseline, "our agent got 92%" means nothing.

---

## 3. Dataset design

`engine/generate_data.py`, fixed seed `20260823`, fully reproducible.

| Category | n | What it tests |
| --- | --- | --- |
| CLEAN | 24 | Baseline — rules should get all of these |
| FEE | 12 | Credit short by 2% platform fee + 18% GST on the fee |
| LAG | 8 | Fee *and* arrival delayed 1–3 days |
| GARBLED | 6 | Bank narration destroys the reference (`ORD-7049` → `ORD-70`) |
| BATCH | 6 | Three settlements collapse into one bank credit (one-to-many) |
| AMBIGUOUS | 4 | Identical amount, identical date — rules cannot choose |
| MISSING | 4 | Correct answer is "no match" |
| ORPHAN | 3 | Bank credits that are not settlements at all |

**64 settlements, 59 bank lines** — comfortably above the ≥50 requirement.

`data/ground_truth.csv` is the answer key. It is used only for scoring and is
never read by the matcher.

---

## 4. Submission requirements

The form has these fields. Only two artifacts are actually judged: **the repo**
and **the video**. No deployment, no hosting, no live URL required.

| Field | Status |
| --- | --- |
| Selected Track | Track 4: AI Finance Controller |
| Project Name / Title | LedgerLens — AI Reconciliation Controller |
| Project Objectives | Draft written (below) |
| GitHub Repository URL | ✅ `https://github.com/Manu-code-all/Ledgerlens` |
| 5-min Pitch Video Link | Record 2026-09-03 |
| Build Challenges & Technical Obstacles | Accumulating in `CHALLENGES.md` |
| Final Submission Confirmation | Tick last. **No edits after submitting** |

### Draft — Project Objectives

> Finance teams manually reconcile payment settlements against bank statements —
> matching hundreds of records where amounts differ by gateway fees, dates lag by
> days, and bank references are truncated or merged. Rule-based matching handles
> only the clean cases and silently mismatches the rest.
>
> LedgerLens processes a batch of 60+ settlement records end to end.
> Deterministic rules resolve exact matches first; unmatched records escalate to
> a Claude-powered agent that reasons over fee deltas, date windows, garbled
> references and one-to-many bank lines, returning a match with a confidence
> score and a written justification.
>
> It reports match rate, accuracy against ground truth, throughput, and —
> critically — every exception and unresolvable record rather than hiding them.
> Rules alone reach roughly 60%; the agent lifts this substantially, with each
> decision individually auditable.

### Video structure (5:00, rehearse it)

| Time | Content |
| --- | --- |
| 0:00–0:30 | The problem — two messy CSVs side by side |
| 0:30–1:00 | The baseline — rules alone, and what they miss |
| 1:00–3:00 | Live run — upload, batch processes, metrics fill in |
| 3:00–4:00 | Audit trail — open one hard match, read the reasoning aloud |
| 4:00–4:30 | Honest failures — exceptions tab, the unresolvable records |
| 4:30–5:00 | The numbers — match rate, accuracy, throughput |

No market-size slides, no team intros. Track 4 rewards measured performance and
honest exception reporting. The exceptions tab is what proves nothing was
cherry-picked.

---

## 5. Schedule

| Dates | Work | Status |
| --- | --- | --- |
| Aug 23–24 | Python basics, synthetic data generator, repo live | ✅ done |
| Aug 25–26 | Rule-based matcher → baseline number | next |
| Aug 27–28 | Claude agent for unmatched residue + reasoning output | |
| Aug 29–30 | Metrics, audit trail, exception report | |
| Aug 31–Sep 1 | FastAPI + React dashboard | |
| Sep 2 | Break it on purpose, harden, README | |
| Sep 3 | Record pitch video (expect 4–5 takes) | |
| Sep 4 | Buffer, finalise form answers | |
| Sep 5 | Submit | |

Commit and push every session. Thirty commits over two weeks reads as real
work; one commit on Sep 4 reads as a dump.

---

## 6. Environment

Verified present on this machine 2026-08-23:

- Python 3.14.3, pip 25.3
- Git 2.55.0
- Node 24.12.0, npm 11.6.2
- GitHub CLI at `C:\Program Files\GitHub CLI\gh.exe` (not on PATH in some
  shells — invoke with `& "C:\Program Files\GitHub CLI\gh.exe"`)

### PowerShell gotchas

Most tutorials are written for Bash/macOS. In Windows PowerShell 5.1:

| Bash | PowerShell |
| --- | --- |
| `cmd1 && cmd2` | `cmd1; cmd2` |
| `/e/razorpay-hackathon` | `E:\razorpay-hackathon` |
| `./prog` | `& "C:\full path\prog.exe"` |

### Routine commands

```powershell
python engine/generate_data.py          # regenerate the dataset
git add -A; git commit -m "msg"; git push
```

---

## 7. Session log

### 2026-08-23 — Day 1

**Decided.** Track 4. Project named LedgerLens. Stack: Python engine → FastAPI →
React + Vite dashboard. Repo location `E:\razorpay-hackathon`.

**Built.** `engine/generate_data.py` — generates the three CSVs from a fixed
seed with seven planted difficulty categories and a ground-truth answer key.

**Two bugs found and fixed** (both written up in `CHALLENGES.md`):

1. *The answer key leaked into the record IDs.* Settlements and bank lines were
   generated in lockstep, so `SETL-0046` → `ORD-7046` → `BANK-0046`. Shuffling
   the rows hid it visually but the numbering still encoded the correct pairing —
   a matcher could have scored ~100% by comparing trailing digits while
   reconciling nothing. Fixed by assigning bank IDs *after* the shuffle and
   remapping ground truth through an old-ID → new-ID lookup.
2. *A garbling step that garbled nothing.* One reference-mangling style truncated
   to 9 characters, but references are 8 characters long, so it was a no-op —
   those records sat in the "hard" bucket while being trivially easy. Now
   truncates to 6.

The lesson generalises and belongs in the pitch: **when you generate your own
test data, you also generate your own ways to cheat on it.**

**Repo published.** `https://github.com/Manu-code-all/Ledgerlens`, public,
commit `c39a04f`.

**Hit a git auth wall.** Push returned 403 despite correct ownership. Cause was
a chain of misdirection worth recording: the Windows credential store was empty,
because `.gitconfig` overrides the github.com credential helper to use GitHub
CLI (`gh auth git-credential`), and `gh` held a **fine-grained** PAT scoped to a
list of repositories that predated `Ledgerlens`. Public reads succeeded, writes
did not. Resolved by re-running `gh auth login` through the browser device flow
— and letting it finish, since an interrupted run leaves the old token in place.

**Open items.**

- Read through `engine/generate_data.py` and be able to explain the CLEAN, FEE
  and BATCH blocks aloud.
- Obtain an Anthropic API key from `console.anthropic.com` before Aug 27
  (requires billing setup — do not leave to the morning of).

---

## 8. Next up — Aug 25–26

Build `engine/rules.py`: exact reference match, then exact amount match, nothing
clever. Expected to land near 55–65%, failing completely on FEE, GARBLED, BATCH
and AMBIGUOUS.

That failure is the deliverable. It is the baseline that converts "our AI got
92%" into "rules got 58%, the agent got 92%, here is the delta and exactly which
categories it came from."
