# Build Challenges & Technical Obstacles

A running log. Every entry: what broke, and how it was fixed. This feeds the
submission form field of the same name.

---

## 2026-08-23 — The answer key leaked into the record IDs

**Problem.** The first version of the generator created settlements and bank
lines in lockstep, so `SETL-0046` produced `ORD-7046` which produced
`BANK-0046`. Shuffling the rows before writing them hid this visually, but the
IDs still encoded the correct pairing. Any matcher could have scored near 100%
by comparing trailing digits — measuring nothing, and invalidating every
accuracy number the project reports.

**Fix.** Bank transaction IDs are now assigned *after* the shuffle, in shuffled
order, and the ground-truth table is remapped through a lookup of old ID to new
ID. `BANK-0034` now pairs with `SETL-0001`, with no relationship between the
numbers.

**Lesson.** When you generate your own test data, you also generate your own
ways to cheat on it. Worth auditing the dataset for leakage before trusting a
single metric derived from it.

---

## 2026-08-23 — A "garbling" step that garbled nothing

**Problem.** One of the reference-mangling styles truncated the bank narration
to the first 9 characters. Order references are only 8 characters long
(`ORD-7049`), so the truncation was a no-op and those records stayed trivially
matchable while being labelled as hard cases.

**Fix.** Truncate to 6 characters, which genuinely destroys the trailing digits
(`ORD-7049` becomes `ORD-70`). Verified by inspecting the generated file rather
than trusting the category label.

**Lesson.** Check that planted difficulty is actually difficult. A test case
that is labelled hard but isn't will silently inflate results.
