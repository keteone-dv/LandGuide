# PropTech & Urban Intelligence Platform — Project Context

## What this is
A multi-agent AI system that takes a 10-digit cadastral code and returns
legal, spatial, and regulatory analysis for a land plot. Two tiers:
- **Regular Plan** (citizens): owner, address, area, land designation, legal status
- **Pro Plan** (architects/developers): + K1/K2/K3 zoning coefficients, height/density
  limits, buffer zones, and an AI legal chat grounded in real construction law

## Core design principle
Every requirement is tagged **Rule** (→ becomes a deterministic Python function)
or **Judgment** (→ becomes an AI agent). Rules are preferred by default — only
use an agent where real interpretation is required, and always double-check
agent output with a rule-based verification step before it reaches a user.
Do not add agents or LLM calls where a plain function would do the job.

## Architecture (as built)
```
validate_and_lookup → tier_dispatch → regular_formatter → END
                                    → pro_data_engine → (if rag_question) → rag_answer_agent
                                                                              → grounding_check
                                                                                   → compliance_critic (bounce loop, max 2)
                                                                                        → finalize_rag_answer / not_covered_fallback
```

| Desk | Type | File |
|---|---|---|
| validate_and_lookup, tier_dispatch | function | desks/lookup.py |
| regular_formatter | function | desks/regular.py |
| pro_data_engine | function | desks/pro.py |
| rag_answer_agent | **agent** | desks/rag.py |
| grounding_check | function (verifies agent output) | desks/rag.py |
| compliance_critic | **agent** (checks agent output) | desks/rag.py |
| not_covered_fallback | function | desks/rag.py |

Full requirements table (R1–R15) and rationale: see README.md.

## Key files
- `state.py` — PlotQueryState, the shared dict every node reads/writes
- `graph.py` — wires all desks into the compiled LangGraph StateGraph
- `main.py` — test harness, writes results to test_results.txt
- `data/plots.py` — MOCK cadastral database (invented test data, not real)
- `data/legal_corpus.json` — REAL data, extracted from a real Batumi zoning PDF
  via `ingest_pdf.py` — never hand-edit this file, regenerate it instead
- `config.py` — model + API key config (currently OpenAI, gpt-4o-mini)
- `visualize_graph.py` — renders the actual compiled graph (mermaid/ASCII)

## Known, documented limitations (do not "fix" without discussion first)
- `data/plots.py` zone labels (e.g. "residential_mixed_b2") are placeholders and
  don't match real Batumi zone codes used in legal_corpus.json — so the RAG
  chat currently can't answer plot-specific questions, only general zone
  questions. This is a planned post-MVP integration, not a bug.
- RAG chat has intentionally NO access to plots.json, and plot desks have NO
  access to legal_corpus.json — this separation is deliberate, keep it that way
  unless explicitly asked to build the cross-reference feature.
- The eval bar for the RAG chat is 100% on the curated test set — any change
  to desks/rag.py should be re-verified against test-5/test-6 in main.py.
- Plot data is intentionally mock-only for now. A NAPR (Georgia's public
  registry) plot search API integration was attempted and abandoned — the
  endpoint's response data wasn't sufficient to populate the full record
  shape needed. Future integration is undecided and not actively planned.

## Current status
- Core pipeline + RAG agent loop: built, tested, working (see test_results.txt)
- Presentation deck: complete
- Tech stack decided for the web product: FastAPI (backend) + Next.js (frontend),
  hosted on Render/Railway + Vercel (free tier), Supabase Postgres later
- NOT yet built: the FastAPI wrapper layer, the frontend, real API integration
  for plot data (currently mock)
- Pricing decided — exactly two packages, no more:
  - **Free / Regular Plan**: unlimited basic lookups (owner, address, area,
    land designation, legal status), no account needed
  - **Pro**: pay-per-report, ~15 GEL, includes full coefficient/zoning
    analysis + unlimited RAG legal chat questions about that specific report
    for 7 days after purchase. Access is time-boxed, not question-counted —
    per-question cost is negligible on gpt-4o-mini, so time is the right
    lever, not a quota.
  - No monthly/subscription/firm tiers yet — this is deliberately deferred,
    not a "coming soon" placeholder

## Roadmap — not yet built
Rough priority order:
1. Frontend (Next.js) connected to the existing api.py
2. Basic user accounts — required before payment can work at all
3. Stripe integration for the pay-per-report flow
4. A payment/credit gate in api.py, placed BEFORE `proptech_system.invoke()`
   is called for any Pro-tier or RAG request. This is a plain rule-based
   check ("does this user have valid access") — it does NOT belong in
   graph.py or any desk, and must never be added there.
5. Downloadable PDF report feature (see below)
6. Real NAPR API integration to replace mock plots.py — see "Known,
   documented limitations" above (attempted once, abandoned, undecided)

### PDF report feature (new, not yet built)
- **Purpose**: the actual tangible deliverable a Pro customer keeps after
  their 7-day access window ends. Right now the product's only deliverable
  is temporary chat access, which is a weak thing to sell.
- **Content**: the plot's Pro-tier data (coefficients, zoning, limits) +
  every RAG question asked, its answer, and its citation, for that report.
- Zero new agent/LLM logic required — this is pure formatting of data that
  already exists in `pro_response` and `rag_final_answer`. A **Rule**, not a
  judgment call, consistent with the project's core design principle.
- Two open design decisions to resolve before building, not during:
  (a) is the report a live/regenerate-on-demand snapshot, or locked at
  first download — leaning toward always-regenerate; and (b) the "confirm
  with municipal authority" disclaimer must be printed directly on the
  document itself (ideally every page with a citation), not just shown in
  the chat UI, since a PDF can leave the product's context entirely once
  downloaded or forwarded.
- Sequencing: build this AFTER the core paid flow is validated with a real
  payment (frontend + accounts + Stripe + gate all working) — not before.
  Explicitly deprioritized below items 1–4 above.

## Conventions to follow when adding code
- Keep the rule-vs-judgment split explicit — new functions get a one-line
  docstring saying which requirement they satisfy and whether they're a
  rule or judgment call.
- Any new agent needs a verification step before its output reaches a user,
  same pattern as grounding_check + compliance_critic.
- Prefer editing/extending existing desks/ files over creating new top-level
  modules, unless the new code is a genuinely separate concern.
