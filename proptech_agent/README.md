# PropTech agent — MVP core

Multi-agent land-plot intelligence system. Two tiers (Regular / Pro) over a
mock cadastral database, plus a RAG legal chat with a grounding + compliance
double gate. Built to the architecture from the design phase — see the org
chart below for how it maps to code.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then paste your OPENAI_API_KEY into .env
```

## Run

```bash
python main.py
```

Runs six scenarios: Regular happy path, unmatched code, Pro coefficients, a
deliberately malformed plot (tests the input-validation seatbelt), a grounded
RAG legal answer, and a RAG question that isn't in the corpus (tests the
grounding seatbelt).

## Project structure

```
proptech_agent/
├── config.py                # API key + model setup
├── state.py                  # PlotQueryState — the shared "case file"
├── graph.py                   # wires every desk into the compiled graph
├── main.py                     # test scenarios / entry point
├── ingest_pdf.py                # extracts legal_corpus.json from the real PDF
├── data/
│   ├── plots.py                  # mock cadastral database (R2-R6, R9, R14)
│   ├── legal_corpus.json          # GENERATED — real extracted articles, don't hand-edit
│   └── source_documents/
│       └── დანართი_2_ზონირების_რეგლამენტი.pdf   # the real source of truth
└── desks/
    ├── lookup.py               # validate & lookup, tier dispatcher (R1-R3, R9)
    ├── regular.py                # Regular Plan formatter (R4)
    ├── pro.py                      # Pro Data Engine — K1/K2/K3 (R5, R6, R14)
    └── rag.py                        # RAG answer agent, grounding check, critic (R7, R8, R12, R13, R15)
```

## Org chart (rule vs. judgment)

| Desk | Kind | Requirement |
|---|---|---|
| validate_and_lookup | function | R1-R3 |
| tier_dispatch | function | R9 |
| regular_formatter | function | R4 |
| pro_data_engine | function | R5, R6, R14 |
| rag_answer_agent | **agent** | R7 |
| grounding_check | function | R12 |
| compliance_critic | **agent** | R8 |
| not_covered_fallback | rule constrains agent | R13, R15 |

Two agents total. Everything else is deterministic — cheap, fast, and it
never hallucinates a coefficient or a plot's legal status.

## Swapping in the real legal PDF

**Already done.** `data/legal_corpus.json` is generated from the real Batumi
municipal zoning regulation PDF (`data/source_documents/`) — 32 articles,
real page numbers, real Georgian text, extracted by `ingest_pdf.py`.

To regenerate (e.g. if the source PDF is updated, or you add another
document):

```bash
python ingest_pdf.py
```

This overwrites `data/legal_corpus.json`. That file is a **generated
artifact** — never hand-edit it; edit `ingest_pdf.py`'s extraction logic or
replace the source PDF instead. The RAG agent's tool and the grounding check
both read only from the JSON, so nothing else needs to change when you
re-run ingestion.

**Note on language:** the source document is in Georgian, so citations use
Georgian article numbers (e.g. `[BAT-4]` = მუხლი 4). The RAG agent is
instructed to answer in whatever language the question was asked in, while
keeping the citation bracket exact. If you want guaranteed bilingual
coverage, that's worth testing explicitly in your eval suite.

## Post-MVP: real data sources

- Regular Plan fields largely overlap Georgia's public NAPR registry
  (maps.gov.ge) — the value-add here is aggregation, simplification, and a
  usable UX layer, not exclusive data access. Worth stating this explicitly
  in any pitch.
- Pro Plan zoning/coefficient data is more fragmented across municipal
  systems — this is where a real API integration project would add the most
  differentiated value.
