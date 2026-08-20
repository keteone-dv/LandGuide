"""
Run realistic scenarios through the compiled graph — never just the happy path.
Covers: Regular happy path, unmatched code, Pro coefficients, malformed zoning
data (R14 seatbelt), a grounded RAG answer, and a not-covered RAG question
(R12/R13 seatbelt).

Run with:  python main.py
"""
import json
from graph import proptech_system


def process_query(cadastral_code: str, tier: str, folder: str, rag_question: str = None):
    config = {"configurable": {"thread_id": folder}, "recursion_limit": 15}
    initial_state = {
        "cadastral_code": cadastral_code,
        "tier": tier,
        "rag_question": rag_question, 
        "plot": None,
        "not_found": False,
        "regular_response": None,
        "pro_response": None,
        "pro_input_error": None,
        "rag_draft": None,
        "rag_citations": None,
        "grounded": None,
        "critic_approved": None,
        "critic_feedback": None,
        "bounce_count": 0,
        "rag_final_answer": None,
        "audit": [],
    }
    result = proptech_system.invoke(initial_state, config)

    print(f"\n{'=' * 70}\n{folder} — {tier.upper()} query for {cadastral_code}")
    if rag_question:
        print(f"RAG question: {rag_question}")
    print("=" * 70)

    if result["not_found"]:
        print("→ No data available for this cadastral code.")
    elif tier == "regular":
        print(json.dumps(result["regular_response"], indent=2))
    else:
        if result["pro_input_error"]:
            print(f"→ REJECTED by input validation: {result['pro_input_error']}")
        else:
            print(json.dumps(result["pro_response"], indent=2))
        if result.get("rag_final_answer"):
            print("\n--- RAG legal chat answer ---")
            print(result["rag_final_answer"]["answer"])

    print("\naudit trail:")
    for line in result["audit"]:
        print(f"  - {line}")

    return result


if __name__ == "__main__":
    import contextlib
    import os

    output_path = "test_results.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        with contextlib.redirect_stdout(f):
            # Test 1 — Regular happy path
            process_query("0100112233", "regular", "test-1-regular-clean")

            # Test 2 — unmatched code (R3 fallback)
            process_query("9999999999", "regular", "test-2-not-found")

            # Test 3 — Pro happy path, K-coefficients calculated live
            process_query("0100112233", "pro", "test-3-pro-coefficients")

            # Test 4 — Pro with malformed zoning data (R14 seatbelt)
            process_query("0500990011", "pro", "test-4-pro-input-validation")

            # Test 5 — Pro + RAG question that IS covered by the corpus
            process_query(
                "0100112233", "pro", "test-5-rag-grounded",
                rag_question="What are the K1, K2, and K3 coefficients for a low-intensity residential zone (სზ-2)?",
            )

            # Test 6 — Pro + RAG question NOT covered by the corpus (grounding seatbelt)
            process_query(
                "0100112233", "pro", "test-6-rag-not-covered",
                rag_question="What's the maximum allowed noise level for a construction site at night?",
            )
            #Test 7 
            process_query("0100112233", "pro", "test-7-pro-rag-max-height", rag_question="what is the max height of building I can build here?")

            process_query(
                "0200334455", "pro", "test-6-rag-not-covered",
                rag_question="What are the K1, K2, and K3 coefficients for a low-intensity residential zone (სზ-2)?",
            )
    print(f"Done. Full results written to {output_path}")
    os.startfile(output_path)  # Windows only — opens it in your default text editor