"""
Wires every desk into one graph. Compare this against the Phase 3 architecture
diagram — they should match. That comparison is the design review.

    validate_and_lookup -> [not found -> not_found_response -> END]
                         -> tier_dispatch
                              -> regular -> regular_formatter -> END
                              -> pro     -> pro_data_engine
                                              -> [no rag_question -> END]
                                              -> [rag_question -> rag_answer_agent]
                                                    -> grounding_check
                                                         -> [fail -> not_covered_fallback -> END]
                                                         -> [pass -> compliance_critic]
                                                              -> [approved -> finalize_rag_answer -> END]
                                                              -> [bounced, budget left -> rag_answer_agent]
                                                              -> [bounced, budget exhausted -> not_covered_fallback -> END]
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from state import PlotQueryState
from desks.lookup import validate_and_lookup, tier_dispatch
from desks.regular import regular_formatter, not_found_response
from desks.pro import pro_data_engine, needs_rag
from desks.rag import (
    rag_answer_agent, grounding_check, compliance_critic,
    not_covered_fallback, finalize_rag_answer, after_grounding, after_critic,
)


def build_graph():
    g = StateGraph(PlotQueryState)

    for name, fn in [
        ("validate_and_lookup", validate_and_lookup),
        ("not_found_response", not_found_response),
        ("regular_formatter", regular_formatter),
        ("pro_data_engine", pro_data_engine),
        ("rag_answer_agent", rag_answer_agent),
        ("grounding_check", grounding_check),
        ("compliance_critic", compliance_critic),
        ("not_covered_fallback", not_covered_fallback),
        ("finalize_rag_answer", finalize_rag_answer),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "validate_and_lookup")
    g.add_conditional_edges(
        "validate_and_lookup", tier_dispatch,
        ["not_found_response", "regular_formatter", "pro_data_engine"],
    )
    g.add_edge("not_found_response", END)
    g.add_edge("regular_formatter", END)

    g.add_conditional_edges("pro_data_engine", needs_rag, ["rag_answer_agent", END])

    g.add_edge("rag_answer_agent", "grounding_check")
    g.add_conditional_edges(
        "grounding_check", after_grounding, ["compliance_critic", "not_covered_fallback"]
    )
    g.add_conditional_edges(
        "compliance_critic", after_critic,
        ["finalize_rag_answer", "rag_answer_agent", "not_covered_fallback"],
    )
    g.add_edge("not_covered_fallback", END)
    g.add_edge("finalize_rag_answer", END)

    return g.compile(checkpointer=InMemorySaver())


proptech_system = build_graph()
