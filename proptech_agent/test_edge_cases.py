"""
Edge-case hardening tests, beyond the six happy/seatbelt scenarios in main.py.

Kept separate from main.py on purpose:
  - several of these tests call desk functions directly (bypassing PLOTS) to hit
    boundary values that don't exist in data/plots.py, without editing that file
  - test 4 monkeypatches the compliance_critic's model to force a REJECT, which
    doesn't belong in main.py's "run the real graph, eyeball the JSON" pattern
  - this file prints PASS/FAIL + explanation per test, not just raw output

Run with:  python test_edge_cases.py
Writes to: edge_case_results.txt (mirrors console via redirect, same as main.py)

NOTE: this is a reporting/diagnostic script, not a fix. No core desk file
(lookup.py, pro.py, rag.py, graph.py) is modified by running this.
"""
import json
import re

from graph import proptech_system
from desks.lookup import CADASTRAL_CODE_PATTERN, validate_and_lookup
from desks.pro import pro_data_engine, needs_rag
import desks.rag as rag_module

results = []  # (name, "PASS"|"FAIL", detail)


def record(name, passed, detail):
    results.append((name, "PASS" if passed else "FAIL", detail))
    print(f"\n[{'PASS' if passed else 'FAIL'}] {name}")
    print(f"  {detail}")


def blank_state(**overrides):
    base = {
        "cadastral_code": "0000000000",
        "tier": "regular",
        "rag_question": None,
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
    base.update(overrides)
    return base


def invoke(cadastral_code, tier, thread_id, rag_question=None):
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 15}
    return proptech_system.invoke(
        blank_state(cadastral_code=cadastral_code, tier=tier, rag_question=rag_question),
        config,
    )


# ─────────────────────────────────────────────────────────────────────────
# 1. Cadastral code format edge cases (R1 regex)
# ─────────────────────────────────────────────────────────────────────────
def test_1_cadastral_format():
    malformed_cases = {
        "9 digits": "010011223",
        "11 digits": "01001122334",
        "10 chars with a letter": "010011223A",
        "10 letters": "abcdefghij",
    }
    failures = []
    for label, code in malformed_cases.items():
        matched = bool(CADASTRAL_CODE_PATTERN.match(code))
        if matched:
            failures.append(f"'{code}' ({label}) WAS accepted by the regex — should be rejected")
        out = validate_and_lookup(blank_state(cadastral_code=code))
        if not out["not_found"]:
            failures.append(f"'{code}' ({label}) did not set not_found=True")

    # control: a well-formed 10-digit code that's simply not in the DB should
    # match the regex (format is fine) but still end in not_found via DB miss,
    # not via the format check — different failure mode, same user-facing result.
    control_code = "0100112234"
    if not CADASTRAL_CODE_PATTERN.match(control_code):
        failures.append(f"control code '{control_code}' unexpectedly failed the regex (test setup bug)")
    control_out = validate_and_lookup(blank_state(cadastral_code=control_code))
    if not control_out["not_found"]:
        failures.append(f"control code '{control_code}' unexpectedly found in DB (test setup bug)")
    elif "failed format check" in control_out["audit"][-1]:
        failures.append("control code was rejected by the FORMAT check, not the DB lookup — regex too strict")

    record(
        "1. Cadastral code format edge cases",
        not failures,
        "all malformed codes correctly rejected by regex; well-formed-but-unknown code rejected via DB miss, not format" if not failures else "; ".join(failures),
    )


# ─────────────────────────────────────────────────────────────────────────
# 2. buffer_zones: empty list vs multiple entries
# ─────────────────────────────────────────────────────────────────────────
def test_2_buffer_zones():
    def make_plot(buffer_zones):
        return {
            "owner_name": "Test Owner",
            "address": "Test Address",
            "total_area_sqm": 100,
            "land_designation": "non-agricultural",
            "legal_status": "clean",
            "legal_status_note": "n/a",
            "zoning": {
                "functional_zone": "residential_b1",
                "footprint_pct": 40,
                "far": 1.0,
                "green_space_pct": 20,
                "max_height_m": 10,
                "density_limit_units_per_ha": 50,
                "buffer_zones": buffer_zones,
            },
        }

    problems = []
    for label, zones in [
        ("empty list", []),
        ("single zone", ["heritage_zone_100m"]),
        ("multiple zones", ["heritage_zone_100m", "utility_easement_gas", "flood_plain_50m"]),
    ]:
        try:
            out = pro_data_engine(blank_state(plot=make_plot(zones)))
            resp = out["pro_response"]
            if resp is None or resp["buffer_zones"] != zones:
                problems.append(f"{label}: response buffer_zones mismatch ({resp})")
            json.dumps(resp)  # confirm it's JSON-serializable (what the formatter/UI needs)
        except Exception as e:
            problems.append(f"{label}: raised {type(e).__name__}: {e}")

    record(
        "2. buffer_zones empty vs multiple",
        not problems,
        "handled 0/1/3-item buffer_zones lists without error" if not problems else "; ".join(problems),
    )


# ─────────────────────────────────────────────────────────────────────────
# 3. R14 boundary values: footprint_pct exactly 0 and exactly 100
# ─────────────────────────────────────────────────────────────────────────
def test_3_r14_boundaries():
    def make_plot(footprint_pct):
        return {
            "owner_name": "Test Owner",
            "address": "Test Address",
            "total_area_sqm": 100,
            "land_designation": "non-agricultural",
            "legal_status": "clean",
            "legal_status_note": "n/a",
            "zoning": {
                "functional_zone": "residential_b1",
                "footprint_pct": footprint_pct,
                "far": 1.0,
                "green_space_pct": 20,
                "max_height_m": 10,
                "density_limit_units_per_ha": 50,
                "buffer_zones": [],
            },
        }

    out_0 = pro_data_engine(blank_state(plot=make_plot(0)))
    out_100 = pro_data_engine(blank_state(plot=make_plot(100)))

    detail = (
        f"footprint_pct=0 -> pro_input_error={out_0['pro_input_error']!r}; "
        f"footprint_pct=100 -> pro_input_error={out_100['pro_input_error']!r}"
    )
    # Not asserting pass/fail here since "correct" behavior at 0 is a judgment
    # call — see write-up. Recorded as informational so the asymmetry is visible.
    record(
        "3. R14 boundary values (0 and 100)",
        True,
        detail + " -- see report for whether this asymmetry (0 rejected, 100 accepted) is intended",
    )


# ─────────────────────────────────────────────────────────────────────────
# 4. Force a real compliance_critic bounce
# ─────────────────────────────────────────────────────────────────────────
def test_4_critic_bounce():
    original_model = rag_module.model
    call_log = []

    class FakeResponse:
        def __init__(self, text):
            self.text = text

    class FakeModel:
        def invoke(self, prompt, *args, **kwargs):
            call_log.append(prompt)
            n = len(call_log)
            if n == 1:
                return FakeResponse("REJECT\nMissing the required municipal-authority disclaimer.")
            return FakeResponse("APPROVE\nLooks complete now.")

    # ChatOpenAI is a pydantic model — it forbids setting arbitrary instance
    # attributes (invoke isn't a declared field), so we swap the whole module
    # global rather than patching .invoke on the existing instance.
    rag_module.model = FakeModel()
    try:
        result = invoke(
            "0100112233", "pro", "test-edge-4-critic-bounce-recovers",
            rag_question="What are the K1, K2, and K3 coefficients for a low-intensity residential zone (სზ-2)?",
        )
    finally:
        rag_module.model = original_model

    problems = []
    if result["bounce_count"] != 1:
        problems.append(f"expected bounce_count=1 after one reject+approve, got {result['bounce_count']}")
    if len(call_log) != 2:
        problems.append(f"expected exactly 2 critic calls (reject, approve), got {len(call_log)}")
    if not any("rag_answer_agent: drafted" in a for a in result["audit"] if a.count("rag_answer_agent") ) or \
       sum(1 for a in result["audit"] if a.startswith("rag_answer_agent:")) != 2:
        problems.append("expected rag_answer_agent to run twice (initial draft + retry after bounce)")
    if not result.get("rag_final_answer") or result["rag_final_answer"]["answer"] == "This question is not covered in the available regulations.":
        problems.append("expected a real finalized answer, got fallback or nothing")

    record(
        "4a. compliance_critic bounce-then-recover",
        not problems,
        "bounce fired once, retry loop re-ran rag_answer_agent, then approved" if not problems else "; ".join(problems),
    )

    # ---- exhaust the bounce budget entirely (always REJECT) ----
    call_log_2 = []

    class AlwaysRejectModel:
        def invoke(self, prompt, *args, **kwargs):
            call_log_2.append(prompt)
            return FakeResponse("REJECT\nStill missing something.")

    rag_module.model = AlwaysRejectModel()
    try:
        result2 = invoke(
            "0100112233", "pro", "test-edge-4b-critic-exhausts-budget",
            rag_question="What are the K1, K2, and K3 coefficients for a low-intensity residential zone (სზ-2)?",
        )
    finally:
        rag_module.model = original_model

    problems2 = []
    if result2["bounce_count"] != 2:
        problems2.append(f"expected bounce_count capped at MAX_CRITIC_BOUNCES=2, got {result2['bounce_count']}")
    if not result2.get("rag_final_answer") or result2["rag_final_answer"]["answer"] != "This question is not covered in the available regulations.":
        problems2.append(f"expected not_covered_fallback after budget exhausted, got {result2.get('rag_final_answer')}")
    if "not_covered_fallback: returned safe default" not in result2["audit"]:
        problems2.append("audit trail missing not_covered_fallback entry")

    record(
        "4b. compliance_critic bounce budget exhausted -> fallback",
        not problems2,
        "after 2 rejects, routed to not_covered_fallback as designed" if not problems2 else "; ".join(problems2),
    )


# ─────────────────────────────────────────────────────────────────────────
# 5. Ambiguous question (touches both parking and green space articles)
# ─────────────────────────────────────────────────────────────────────────
def test_5_ambiguous_question():
    result = invoke(
        "0100112233", "pro", "test-edge-5-ambiguous",
        rag_question="What are the parking and green space requirements for my plot?",
    )
    answer = (result.get("rag_final_answer") or {}).get("answer", "")
    citations = (result.get("rag_final_answer") or {}).get("citations")
    hedge_fallback = answer == "This question is not covered in the available regulations."

    detail = f"citations={citations!r}, answer preview={answer[:200]!r}"
    # Informational — "sensible" here means either (a) it picked one citation and
    # answered clearly, or (b) it addressed both topics with the citations available.
    # We report what happened rather than asserting a specific behavior.
    record(
        "5. Ambiguous question (parking + green space)",
        not hedge_fallback,
        detail if not hedge_fallback else "fell back to not-covered instead of answering either topic: " + detail,
    )


# ─────────────────────────────────────────────────────────────────────────
# 6. Same RAG question asked in Georgian
# ─────────────────────────────────────────────────────────────────────────
GEORGIAN_LETTERS = re.compile(r"[Ⴀ-ჿ]")


def test_6_georgian_question():
    # Georgian for: "What is the maximum height for a low-intensity residential zone (სზ-2)?"
    georgian_q = "რა არის მაქსიმალური სიმაღლე დაბალი ინტენსივობის საცხოვრებელი ზონისთვის (სზ-2)?"
    result = invoke("0100112233", "pro", "test-edge-6-georgian", rag_question=georgian_q)
    answer = (result.get("rag_final_answer") or {}).get("answer", "")

    is_georgian = bool(GEORGIAN_LETTERS.search(answer))
    record(
        "6. Georgian-language RAG question",
        is_georgian,
        f"answer language {'is Georgian as instructed' if is_georgian else 'is NOT Georgian — system prompt instruction failed'}: {answer[:200]!r}",
    )


# ─────────────────────────────────────────────────────────────────────────
# 7. Pro query with rag_question="" (empty string, not None)
# ─────────────────────────────────────────────────────────────────────────
def test_7_empty_rag_question():
    # unit-level: does the router itself treat "" as falsy?
    router_result = needs_rag(blank_state(rag_question=""))
    router_ok = router_result == "__end__"

    # full graph: confirm rag_answer_agent never actually runs
    result = invoke("0100112233", "pro", "test-edge-7-empty-rag-question", rag_question="")
    ran_rag = result.get("rag_draft") is not None or any(
        a.startswith("rag_answer_agent:") for a in result["audit"]
    )

    problems = []
    if not router_ok:
        problems.append(f"needs_rag('') returned {router_result!r}, expected '__end__'")
    if ran_rag:
        problems.append("rag_answer_agent ran despite rag_question=='' ")

    record(
        "7. rag_question='' (empty string) falsy check",
        not problems,
        "needs_rag correctly treats '' as falsy, RAG never invoked" if not problems else "; ".join(problems),
    )


# ─────────────────────────────────────────────────────────────────────────
# 8. Two different thread_ids back-to-back — no state leak via InMemorySaver
# ─────────────────────────────────────────────────────────────────────────
def test_8_thread_isolation():
    result_a = invoke(
        "0200334455", "pro", "test-edge-8-thread-a",
        rag_question="What's the maximum allowed noise level for a construction site at night?",
    )
    result_b = invoke("0400778899", "pro", "test-edge-8-thread-b", rag_question=None)

    problems = []
    if result_b.get("rag_draft") is not None:
        problems.append(f"thread B rag_draft leaked from thread A: {result_b['rag_draft']!r}")
    if result_b.get("bounce_count", 0) != 0:
        problems.append(f"thread B bounce_count leaked: {result_b['bounce_count']}")
    if any("0200334455" in a or "Levan" in a for a in result_b["audit"]):
        problems.append("thread B audit trail contains thread A's plot data")
    if result_b["pro_response"]["owner_name"] != "Giorgi Melia":
        problems.append(f"thread B returned wrong plot owner: {result_b['pro_response']['owner_name']}")
    if result_a["pro_response"]["owner_name"] != "Levan Kapanadze":
        problems.append(f"thread A returned wrong plot owner: {result_a['pro_response']['owner_name']}")

    record(
        "8. Thread isolation across different thread_ids",
        not problems,
        "no cross-thread state leakage observed" if not problems else "; ".join(problems),
    )


if __name__ == "__main__":
    import contextlib
    import os

    output_path = "edge_case_results.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        with contextlib.redirect_stdout(f):
            test_1_cadastral_format()
            test_2_buffer_zones()
            test_3_r14_boundaries()
            test_4_critic_bounce()
            test_5_ambiguous_question()
            test_6_georgian_question()
            test_7_empty_rag_question()
            test_8_thread_isolation()

            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            for name, status, detail in results:
                print(f"[{status}] {name}")

    print(f"Done. Full results written to {output_path}")
    for name, status, detail in results:
        line = f"[{status}] {name}: {detail}"
        print(line.encode("ascii", errors="replace").decode("ascii"))
