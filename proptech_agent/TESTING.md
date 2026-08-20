# Edge-case testing

`main.py` covers the six-scenario happy/seatbelt path (see README). This
file documents the edge cases tested beyond that, in `test_edge_cases.py` —
what each test checks, what actually happened, and what's still open.

## Why a separate file from main.py

`test_edge_cases.py` calls desk functions directly (bypassing `PLOTS`) to
hit boundary values that don't exist in `data/plots.py`, and monkeypatches
the compliance critic's model to force a REJECT — neither fits `main.py`'s
"run the real graph, eyeball the JSON" pattern. It prints PASS/FAIL +
explanation per test rather than raw output.

## Run

```bash
python test_edge_cases.py
```

Writes full traces to `edge_case_results.txt` (overwritten each run, same
pattern as `main.py` → `test_results.txt` — a snapshot of the last run, not
a log).

## A note on flakiness

Tests 5 and 6 drive the real `rag_answer_agent` → `grounding_check` →
`compliance_critic` loop with a live model call. `compliance_critic`'s
REJECT/APPROVE judgment is not deterministic — the same question can pass
on one run and bounce to the fallback on another (see test 5 below). This
is expected given an LLM-as-judge critic, not a test bug; where it matters,
each test was re-run multiple times and the result noted below is the
pattern across runs, not a single sample.

## Results

### 1. Cadastral code format edge cases — PASS
9-digit, 11-digit, letter-containing, and all-letter codes are all rejected
by `CADASTRAL_CODE_PATTERN` (`^\d{10}$`) in `desks/lookup.py`. A
well-formed-but-unknown code correctly falls through to a DB-miss
`not_found`, not a format rejection — the two failure paths are properly
distinguished in the audit trail.

### 2. buffer_zones: empty list vs. multiple entries — PASS
`pro_data_engine` passes the list through untouched; `[]`, 1-item, and
3-item lists all serialize fine. Nothing in the current code does
per-zone formatting, so there was nothing to break.

### 3. R14 boundary values (footprint_pct = 0, = 100) — FIXED
`_validate_zoning_inputs` in `desks/pro.py` originally checked
`0 < footprint_pct <= 100` — an open lower bound but a closed upper bound.
Result: `footprint_pct=0` was **rejected** ("out of range"), but
`footprint_pct=100` was **silently accepted** with no warning.

**Fix applied:** `footprint_pct` is now checked as `0 <= footprint_pct <
100` — 0% (no building allowed, e.g. a protected parcel) is accepted, 100%
(zero setback, building covers the entire lot) is rejected.
`green_space_pct` keeps its original `0 < green_space_pct <= 100` bound
unchanged — it's the physical mirror of footprint_pct, not its
mathematical twin: `green_space_pct=100` (fully green, nothing built,
e.g. a landscape reserve) is legitimate, while `green_space_pct=0` (no
green space at all) is not. The two fields are now bounded in opposite
directions on purpose; see the docstring on `_validate_zoning_inputs`.
Verified: the existing seatbelt case (`footprint_pct=140` in
`data/plots.py`) still rejects correctly, and all `main.py` scenarios are
unaffected.

### 4a/4b. Forced compliance_critic bounce — PASS
This path had never been exercised before. Monkeypatched the critic's
model (in the test file only, not in `desks/rag.py`) to force REJECT then
APPROVE: `bounce_count` went to 1, `rag_answer_agent` re-ran with the
critic's feedback appended to the prompt, and it finalized correctly.
Then forced REJECT twice: `bounce_count` capped at `MAX_CRITIC_BOUNCES=2`
and correctly routed to `not_covered_fallback`. The bounce loop mechanics
are sound.

### 5. Ambiguous question (parking + green space) — FIXED (underlying flakiness remains, by design)
Same question ("What are the parking and green space requirements for my
plot?") run 4 times. `grounding_check` passed every single time with a
valid citation (`BAT-17`). But `compliance_critic` bounced the multi-topic
answer non-deterministically — 2 of 4 runs approved on the first pass, 2 of
4 bounced twice and hit `not_covered_fallback`, which then told the user
*"This question is not covered in the available regulations"* — false; it
was covered and grounded, the critic just couldn't be satisfied within
budget on a two-part answer.

**Fix applied:** `not_covered_fallback` in `desks/rag.py` now branches on
`state["grounded"]`, which reliably distinguishes the two routes into this
node (the grounding-failure route always arrives with `grounded=False`; the
bounce-budget-exhausted route only ever arrives after a grounding pass, so
`grounded=True`). On the exhausted-budget route it now reports *"Relevant
regulation was found (clause(s): ...), but this answer did not fully clear
compliance review after multiple attempts. Please consult these clauses
directly..."* instead of the misleading "not covered" message, and still
returns the actual citation(s) rather than `[]`. The critic's non-determinism
on multi-topic answers itself is unchanged (still worth being aware of),
but the user is no longer told the regulation is silent when it isn't.
Verified via a forced-rejection run (both routes produce visibly distinct
messages) and confirmed naturally in a live `main.py` run, where one RAG
scenario organically bounced twice and correctly surfaced the new grounded
message with its real citation.

### 6. Georgian-language question — PASS (see flakiness note)
Answered fully in Georgian per the system prompt, disclaimer sentence
stayed in English as designed, citation bracket preserved
(`[BAT-32]`). Re-run 3x standalone after an unrelated code change: 3/3
PASS. One earlier run in the full suite did hit the same
critic-bounce flakiness as test 5 (fell back to "not covered") — confirmed
via repeat runs to be the pre-existing issue in finding 5, not specific to
Georgian input.

### 7. rag_question="" (empty string) — PASS
`needs_rag`'s `state.get("rag_question")` in `desks/pro.py` correctly
treats `""` as falsy — routes straight to `__end__`, `rag_answer_agent`
never runs, no wasted API call.

### 8. Thread isolation across different thread_ids — PASS
Ran two different thread_ids back-to-back with different plots/questions;
no cross-contamination in `rag_draft`, `bounce_count`, `audit`, or
`pro_response`. Each `invoke()` call supplies a complete fresh
`initial_state`, so `InMemorySaver` has nothing stale to leak for a new
thread_id.

## Fixes applied since this round

- **Multi-citation capture** (`desks/rag.py`, `state.py`) — found while
  investigating test 5: the citation regex used `re.search`, which only
  captures the *first* bracketed clause_id in a draft. On a multi-topic
  answer citing two articles, the second citation was silently dropped
  from both `grounding_check` and the final answer. Fixed: `re.findall` +
  dedupe, `rag_citation: Optional[str]` → `rag_citations: Optional[list[str]]`
  throughout, `grounding_check` now requires every cited clause_id to
  exist in the corpus (a hallucinated second citation now fails grounding
  instead of being invisible), and `rag_final_answer["citation"]` →
  `rag_final_answer["citations"]` (list; `[]` on the fallback path).
  Verified against `main.py`'s existing test-5/test-6/test-7 scenarios
  (single-citation behavior unchanged) and the edge-case suite.

## Still open

None from this round — all findings from tests 1-8 are either passing as
designed or fixed above. The compliance_critic's non-determinism on
multi-topic answers (test 5) is a known characteristic of an LLM-as-judge
critic, not something further code can fully eliminate; the fallback
message fix above makes its failure mode honest rather than misleading.
