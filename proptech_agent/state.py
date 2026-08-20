"""
PlotQueryState — one dict every desk reads and writes, same principle as the
insurance reference's case file: every field has a known writer, `audit` is
the R10 trail every desk appends to, and the desks run one at a time so a
plain list is all we need (no reducers, no parallel machinery).
"""
from typing import TypedDict, Optional


class PlotQueryState(TypedDict):
    # ── input ──
    cadastral_code: str
    tier: str                      # "regular" | "pro"
    rag_question: Optional[str]    # only set for Pro queries that also ask a legal question

    # ── validate & lookup (R1-R3) ──
    plot: Optional[dict]           # the matched record from PLOTS, or None
    not_found: bool

    # ── regular formatter (R4) ──
    regular_response: Optional[dict]

    # ── pro data engine (R5, R6, R14) ──
    pro_response: Optional[dict]
    pro_input_error: Optional[str]  # set if R14 validation rejects the raw zoning inputs

    # ── RAG legal chat (R7, R8, R12, R13, R15) ──
    rag_draft: Optional[str]
    rag_citation: Optional[str]
    grounded: Optional[bool]
    critic_approved: Optional[bool]
    critic_feedback: Optional[str]
    bounce_count: int
    rag_final_answer: Optional[dict]  # {"answer": ..., "citation": ...} or the not-covered fallback

    # ── R10 ──
    audit: list
