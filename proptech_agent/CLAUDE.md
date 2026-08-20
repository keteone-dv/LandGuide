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

## Current status
- Core pipeline + RAG agent loop: built, tested, working (see test_results.txt)
- Presentation deck: complete
- Tech stack decided for the web product: FastAPI (backend) + Next.js (frontend),
  hosted on Render/Railway + Vercel (free tier), Supabase Postgres later
- NOT yet built: the FastAPI wrapper layer, the frontend, real API integration
  for plot data (currently mock)

## Next step (fill in before starting a session)
Integrating an external API: ___________________________
[Paste what the API provides, its docs link, and whether it replaces
data/plots.py, feeds data/legal_corpus.json, or is something else entirely.]

## Conventions to follow when adding code
- Keep the rule-vs-judgment split explicit — new functions get a one-line
  docstring saying which requirement they satisfy and whether they're a
  rule or judgment call.
- Any new agent needs a verification step before its output reaches a user,
  same pattern as grounding_check + compliance_critic.
- Prefer editing/extending existing desks/ files over creating new top-level
  modules, unless the new code is a genuinely separate concern.
