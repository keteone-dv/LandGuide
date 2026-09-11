"""
RAG legal chat — the one genuine multi-agent judgment pair in this system.

    rag_answer_agent  → drafts an answer, must cite a clause_id in [brackets]
    grounding_check    → RULE: does that clause_id actually exist in the corpus?
    compliance_critic  → AGENT: tone/completeness/disclaimer checklist, can bounce
                          the draft back to the answer agent up to 2 times (R8)

Grounding failing, or the critic's bounce budget running out, both route to the
SAME not-covered fallback (R13, R15) — no answer reaches the architect without
clearing both gates.
"""
import json
import re
import sys
from pathlib import Path

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool

from config import MODEL
from state import PlotQueryState

# The legal corpus and agent output are Georgian-language text. On Windows,
# stdout defaults to the legacy cp1252 codepage, which can't encode Georgian
# script — the debug prints below would crash the whole RAG pipeline the
# moment a tool hit or answer contained non-cp1252 characters.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

model = init_chat_model(MODEL)

MAX_CRITIC_BOUNCES = 3

_CORPUS_PATH = Path(__file__).parent.parent / "data" / "legal_corpus.json"
with open(_CORPUS_PATH, encoding="utf-8") as f:
    LEGAL_CORPUS = json.load(f)


@tool
def search_legal_corpus(query: str) -> str:
    """Search the construction/zoning legal corpus by keyword. Returns matching
    clauses with their clause_id, article, page, and text."""
    print(f"    [TOOL CALL] search_legal_corpus(query={query!r})")

    query_words = set(query.lower().split())
    hits = []
    for clause in LEGAL_CORPUS:
        haystack = " ".join(clause["topic_tags"] + [clause["title"], clause["text"]]).lower()
        if any(w in haystack for w in query_words):
            hits.append(clause)

    if not hits:
        print("    [TOOL RESULT] no matching articles found")
        return "No matching clauses found in the corpus."

    print(f"    [TOOL RESULT] found {len(hits)} article(s): {[c['clause_id'] for c in hits]}")
    return "\n\n".join(
        f"[{c['clause_id']}] {c['article']} (page {c['page']}, {c['source_document']}):\n{c['text']}"
        for c in hits
    )


rag_agent = create_agent(
    model=MODEL,
    tools=[search_legal_corpus],
    system_prompt=(
        "You are a construction/zoning regulation assistant for architects working in "
        "Batumi, Georgia. Your only source of truth is the search_legal_corpus tool, "
        "which searches the real Batumi municipal zoning regulation (in Georgian). "
        "Use the tool before answering. Answer ONLY using information returned by the "
        "tool — never from general knowledge. "
        "You MUST cite the exact clause_id you used, in square brackets, e.g. [BAT-4]. "
        "If the question is asked in English, answer in English but keep the citation "
        "bracket exactly as returned by the tool. If asked in Georgian, answer in Georgian. "
        "Always end your answer with: 'This is advisory information — confirm with the "
        "relevant municipal authority before relying on it.' "
        "If the tool returns no matching articles, say plainly that this is not covered "
        "in the available regulations — do not guess or invent a citation."
    ),
)


def rag_answer_agent(state: PlotQueryState) -> dict:
    feedback_note = ""
    if state.get("critic_feedback"):
        feedback_note = f"\n\nYour previous draft was bounced by compliance:\n{state['critic_feedback']}\nFix every point."

    r = rag_agent.invoke({"messages": [("user", state["rag_question"] + feedback_note)]})

    print(f"    [AGENT TRACE] {len(r['messages'])} messages in this turn:")
    for msg in r["messages"]:
        msg_type = type(msg).__name__
        preview = str(msg.content)[:80] if hasattr(msg, "content") else ""
        print(f"      - {msg_type}: {preview}")

    draft = r["messages"][-1].text
    raw_citations = re.findall(r"\[([A-Z]{2,3}-[\d.]+)\]", draft)
    citations = list(dict.fromkeys(raw_citations))  # dedupe, preserve first-seen order

    return {
        "rag_draft": draft,
        "rag_citations": citations,
        "audit": state["audit"] + [f"rag_answer_agent: drafted, citations={citations}"],
    }

def grounding_check(state: PlotQueryState) -> dict:
    """R12 — a RULE, not an opinion. Does every cited clause_id actually exist?
    A draft that cites nothing, or cites even one clause_id not in the corpus
    (e.g. a hallucinated bracket), fails grounding — same bar as before for the
    common single-citation case, now enforced across every citation in a
    multi-topic answer."""
    citations = state["rag_citations"]
    known_ids = {c["clause_id"] for c in LEGAL_CORPUS}
    grounded = bool(citations) and all(cid in known_ids for cid in citations)
    return {
        "grounded": grounded,
        "audit": state["audit"] + [f"grounding_check: {'PASS' if grounded else 'FAIL'} ({citations})"],
    }


def compliance_critic(state: PlotQueryState) -> dict:
    answer = model.invoke(
        "You are reviewing a draft regulatory answer given to an architect.\n"
        "Checklist — REJECT if any of these are missing:\n"
        "1. Cites a specific clause in [BRACKETS] matching the source material.\n"
        "2. Ends with an advisory disclaimer telling the reader to confirm with the "
        "municipal authority.\n"
        "3. Directly and completely answers the question asked.\n"
        "Respond with the single word APPROVE or REJECT on the first line, then one "
        "line of feedback.\n\n"
        f"QUESTION: {state['rag_question']}\n\nDRAFT ANSWER:\n{state['rag_draft']}"
    )
    first_line = next((ln for ln in answer.text.splitlines() if ln.strip()), "")
    approved = first_line.strip().lstrip("*#>-• ").upper().startswith("APPROVE")
    return {
        "critic_approved": approved,
        "critic_feedback": answer.text,
        "bounce_count": state["bounce_count"] + (0 if approved else 1),
        "audit": state["audit"] + [f"compliance_critic: {'APPROVED' if approved else 'BOUNCED'}"],
    }


def not_covered_fallback(state: PlotQueryState) -> dict:
    """R13 + R15 — the single honest fallback for both a failed grounding check
    and an exhausted critic bounce budget. No unverified draft ever reaches the
    architect, but the two routes mean different things: a failed grounding
    check means the citation itself doesn't check out (missing or hallucinated),
    while an exhausted bounce budget means a grounded, correctly-cited draft
    still failed the critic's tone/completeness bar — the regulation WAS found,
    the critic just couldn't be satisfied. Reporting both as "not covered"
    misleads the architect into thinking the regulation is silent on the topic,
    so the two cases get distinct messages. `state["grounded"]` reliably tells
    them apart: it's only ever True here via the bounce-budget-exhausted route,
    since the grounding-failure route jumps straight here with grounded=False.
    """
    if state.get("grounded"):
        citations = ", ".join(state["rag_citations"])
        answer = (
            f"Relevant regulation was found (clause(s): {citations}), but this answer "
            "did not fully clear compliance review after multiple attempts. Please "
            "consult these clauses directly, or confirm with the relevant municipal "
            "authority before relying on this."
        )
        reason = "bounce budget exhausted on a grounded draft"
    else:
        answer = "This question is not covered in the available regulations."
        reason = "grounding check failed"

    return {
        "rag_final_answer": {
            "answer": answer,
            "citations": state.get("rag_citations") or [],
        },
        "audit": state["audit"] + [f"not_covered_fallback: returned safe default ({reason})"],
    }


def finalize_rag_answer(state: PlotQueryState) -> dict:
    return {
        "rag_final_answer": {"answer": state["rag_draft"], "citations": state["rag_citations"]},
        "audit": state["audit"] + ["finalize_rag_answer: answer cleared both gates"],
    }


def after_grounding(state: PlotQueryState) -> str:
    return "compliance_critic" if state["grounded"] else "not_covered_fallback"


def after_critic(state: PlotQueryState) -> str:
    if state["critic_approved"]:
        return "finalize_rag_answer"
    if state["bounce_count"] >= MAX_CRITIC_BOUNCES:
        return "not_covered_fallback"
    return "rag_answer_agent"
