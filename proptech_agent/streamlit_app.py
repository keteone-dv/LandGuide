"""
Streamlit demo UI for live investor/accelerator pitches.

This is a DEMO frontend only — the real product frontend is the planned
Next.js app (see CLAUDE.md roadmap). This file calls proptech_system
(graph.py) directly in-process, exactly like main.py, so there is only one
process to keep alive on stage. No auth, no payment gate, no PDF export —
those are separate roadmap items and are intentionally not here.
"""
import re
import traceback
import uuid

import streamlit as st

st.set_page_config(
    page_title="LandGuide ნაკვეთის ანალიტიკა — დემო",
    page_icon="🏗️",
    layout="centered",
)

# ── palette (pitch deck) ──────────────────────────────────────────────
NAVY = "#1E2761"
TEAL = "#00A896"
CORAL = "#F96167"
AMBER = "#E8A33D"
RED = "#D64545"

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: #F7F8FC; }}
    .demo-header {{
        background: {NAVY};
        color: white;
        padding: 1.25rem 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.25rem;
    }}
    .demo-header h1 {{ margin: 0; font-size: 1.5rem; }}
    .demo-header p {{ margin: 0.25rem 0 0 0; opacity: 0.85; font-size: 0.95rem; }}
    .plot-card {{
        background: white;
        border: 1px solid #E3E6F0;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
    }}
    .field-label {{
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #6B7280;
        margin-bottom: 0.1rem;
    }}
    .field-value {{ font-size: 1.05rem; color: #1F2333; margin-bottom: 0.9rem; }}
    .badge {{
        display: inline-block;
        padding: 0.3rem 0.9rem;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.9rem;
        color: white;
    }}
    .tag {{
        display: inline-block;
        background: #EEF0F9;
        color: {NAVY};
        border-radius: 999px;
        padding: 0.25rem 0.75rem;
        margin: 0.15rem 0.3rem 0.15rem 0;
        font-size: 0.85rem;
    }}
    .rag-answer {{
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-top: 0.75rem;
    }}
    .rag-citation {{
        display: inline-block;
        color: white;
        font-weight: 600;
        border-radius: 6px;
        padding: 0.15rem 0.6rem;
        margin: 0.15rem 0.3rem 0.15rem 0;
        font-size: 0.85rem;
    }}
    .disclaimer {{
        margin-top: 0.75rem;
        padding: 0.6rem 0.9rem;
        background: #FFF8E8;
        border: 1px solid {AMBER};
        border-radius: 8px;
        font-size: 0.85rem;
        color: #6B4E00;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="demo-header">
        <h1>🏗️ LandGuide და ურბანული ინტელექტი — ლაივ დემო</h1>
        <p>საკადასტრო ძებნა, ზონირების კოეფიციენტები და AI იურიდიული ჩატი, დაფუძნებული ბათუმის რეალურ სამშენებლო კანონმდებლობაზე.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── import the real system (with a graceful failure path) ────────────
try:
    from graph import proptech_system
    from data.plots import PLOTS
    SYSTEM_READY = True
    SYSTEM_ERROR = None
except Exception as e:  # e.g. missing OPENAI_API_KEY, import error
    SYSTEM_READY = False
    SYSTEM_ERROR = str(e)

if not SYSTEM_READY:
    st.error(
        "სისტემის გაშვება ვერ მოხერხდა, ამიტომ დემოს გაშვება ამჟამად შეუძლებელია.\n\n"
        f"დეტალები: {SYSTEM_ERROR}"
    )
    st.stop()

CADASTRAL_CODE_PATTERN = re.compile(r"^\d{10}$")

STATUS_COLORS = {
    "clean": TEAL,
    "active_mortgage": AMBER,
    "seizure": RED,
    "restricted": RED,
}
STATUS_LABELS = {
    "clean": "სუფთა",
    "active_mortgage": "აქტიური იპოთეკა",
    "seizure": "დაყადაღებული",
    "restricted": "შეზღუდული",
}

VERIFIED_QUESTION = (
    "დაბალი ინტენსივობის საცხოვრებელი ზონა (სზ-2) — რა არის მისი K1, K2 და K3 კოეფიციენტები?"
)
EDGE_CASE_QUESTION = "რა არის მშენებლობის მაქსიმალური დასაშვები ხმაურის დონე ღამის საათებში?"

# ── session state ──────────────────────────────────────────────────────
if "cadastral_code" not in st.session_state:
    st.session_state.cadastral_code = ""
if "tier" not in st.session_state:
    st.session_state.tier = "Regular"
if "rag_question_to_ask" not in st.session_state:
    st.session_state.rag_question_to_ask = None
if "rag_history" not in st.session_state:
    st.session_state.rag_history = []  # list of (question, result_dict) for the current plot
if "last_plot_key" not in st.session_state:
    st.session_state.last_plot_key = None


# ── run the graph ──────────────────────────────────────────────────────
def run_query(code: str, tier: str, rag_question: str | None):
    """Invoke proptech_system exactly like main.py does."""
    thread_id = f"streamlit-demo-{code}-{tier}-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 15}
    initial_state = {
        "cadastral_code": code,
        "tier": "regular" if tier == "Regular" else "pro",
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
    return proptech_system.invoke(initial_state, config)


def do_lookup(code: str):
    """Runs the plot lookup and stashes the result + the tier/code that
    produced it. Used as a button callback (quick-select) and from the
    manual Search button, so both paths behave identically."""
    code = code.strip()
    st.session_state.cadastral_code = code
    if not CADASTRAL_CODE_PATTERN.match(code):
        st.session_state.plot_result = None
        st.session_state.search_error = (
            f"'{code}' არასწორი საკადასტრო კოდია — უნდა შედგებოდეს ზუსტად 10 ციფრისგან. "
            "სცადეთ ერთ-ერთი სწრაფი არჩევის ღილაკი ზემოთ."
        )
        return
    tier = st.session_state.tier
    try:
        result = run_query(code, tier, None)
        st.session_state.plot_result = result
        st.session_state.result_tier = tier
        st.session_state.result_code = code
        st.session_state.search_error = None
        plot_key = (code, tier)
        if plot_key != st.session_state.last_plot_key:
            st.session_state.rag_history = []
            st.session_state.last_plot_key = plot_key
    except Exception:
        st.session_state.plot_result = None
        st.session_state.search_error = (
            "ნაკვეთის მოძებნისას მოხდა შეცდომა. გთხოვთ სცადოთ თავიდან ან გამოიყენოთ "
            "ერთ-ერთი სწრაფი არჩევის ღილაკი ზემოთ."
        )


# ── search interface ──────────────────────────────────────────────────
st.subheader("მოძებნეთ ნაკვეთი")

st.session_state.tier = st.radio(
    "გეგმა", ["Regular", "Pro"], horizontal=True,
    index=0 if st.session_state.tier == "Regular" else 1,
    format_func=lambda t: "სტანდარტული" if t == "Regular" else "პრო",
)

st.markdown("**სწრაფი არჩევა (გარანტირებულად კარგი სადემონსტრაციო ნაკვეთები) — მყისიერი ძებნა:**")
quick_cols = st.columns(len(PLOTS))
for col, (code, rec) in zip(quick_cols, PLOTS.items()):
    with col:
        st.button(
            f"{rec['address']}\n({code})",
            key=f"quick_{code}",
            on_click=do_lookup,
            args=(code,),
            use_container_width=True,
        )

code_input = st.text_input(
    "ან შეიყვანეთ 10-ნიშნა საკადასტრო კოდი ხელით",
    value=st.session_state.cadastral_code,
    max_chars=10,
    placeholder="მაგ. 0100112233",
)
st.session_state.cadastral_code = code_input

search_clicked = st.button("🔍 ძებნა", type="primary")
if search_clicked:
    do_lookup(st.session_state.cadastral_code)

# ── render results ──────────────────────────────────────────────────────
# Branch on the tier/code that PRODUCED `result`, not the live widget state —
# otherwise flipping the Regular/Pro toggle after a search (without
# re-searching) renders a stale result under the wrong branch and crashes.
search_error = st.session_state.get("search_error")
result = st.session_state.get("plot_result")
result_tier = st.session_state.get("result_tier")
result_code = st.session_state.get("result_code")

if search_error:
    st.warning(search_error)

if result is not None:
    if result.get("not_found"):
        st.info("ამ საკადასტრო კოდისთვის მონაცემები არ მოიძებნა. სცადეთ ერთ-ერთი სწრაფი არჩევის ღილაკი ზემოთ.")
    elif result_tier == "Regular":
        r = result["regular_response"]
        color = STATUS_COLORS.get(r["legal_status"], "#6B7280")
        label = STATUS_LABELS.get(r["legal_status"], r["legal_status"])
        st.markdown(
            f"""
            <div class="plot-card">
                <div class="field-label">მესაკუთრე</div>
                <div class="field-value">{r['owner_name']}</div>
                <div class="field-label">მისამართი</div>
                <div class="field-value">{r['address']}</div>
                <div class="field-label">საერთო ფართობი</div>
                <div class="field-value">{r['total_area_sqm']:,} m²</div>
                <div class="field-label">მიწის დანიშნულება</div>
                <div class="field-value">{r['land_designation']}</div>
                <div class="field-label">სამართლებრივი სტატუსი</div>
                <div class="field-value"><span class="badge" style="background:{color};">{label}</span></div>
                <div class="field-label">შენიშვნა</div>
                <div class="field-value">{r['legal_status_note']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Pro tier
        if result.get("pro_input_error"):
            st.error(
                "ამ ნაკვეთის ზონირების მონაცემებმა ვერიფიკაცია ვერ გაიარა და ვერ გამოჩნდება "
                f"(უსაფრთხოების შემოწმება R14-მა აღმოაჩინა): {result['pro_input_error']}"
            )
        else:
            r = result["pro_response"]
            color = STATUS_COLORS.get(r["legal_status"], "#6B7280")
            label = STATUS_LABELS.get(r["legal_status"], r["legal_status"])
            st.markdown(
                f"""
                <div class="plot-card">
                    <div class="field-label">მესაკუთრე</div>
                    <div class="field-value">{r['owner_name']}</div>
                    <div class="field-label">მისამართი</div>
                    <div class="field-value">{r['address']}</div>
                    <div class="field-label">საერთო ფართობი</div>
                    <div class="field-value">{r['total_area_sqm']:,} m²</div>
                    <div class="field-label">მიწის დანიშნულება</div>
                    <div class="field-value">{r['land_designation']}</div>
                    <div class="field-label">სამართლებრივი სტატუსი</div>
                    <div class="field-value"><span class="badge" style="background:{color};">{label}</span></div>
                    <div class="field-label">ფუნქციური ზონა</div>
                    <div class="field-value">{r['functional_zone']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            m1, m2, m3 = st.columns(3)
            m1.metric("K1 — ნაშენი ფართობი", f"{r['k1_footprint_sqm']:,.1f} m²")
            m2.metric("K2 — ასაშენებელი ფართობი", f"{r['k2_buildable_floor_area_sqm']:,.1f} m²")
            m3.metric("K3 — მწვანე სივრცე", f"{r['k3_green_space_sqm']:,.1f} m²")

            st.markdown(
                f"**მაქსიმალური სიმაღლე:** {r['max_height_m']} m &nbsp;&nbsp; "
                f"**სიმჭიდროვის ლიმიტი:** {r['density_limit_units_per_ha']} units/ha"
            )
            if r["buffer_zones"]:
                tags = "".join(f'<span class="tag">{bz}</span>' for bz in r["buffer_zones"])
                st.markdown(f"**ბუფერული ზონები:** {tags}", unsafe_allow_html=True)
            else:
                st.markdown("**ბუფერული ზონები:** არცერთი")

            # ── RAG chat ──────────────────────────────────────────────
            st.divider()
            st.subheader("💬 ჰკითხეთ AI იურიდიულ ასისტენტს")
            st.caption(
                "დაფუძნებულია ბათუმის ზონირების რეგულაციების რეალურ კორპუსზე — ყველა პასუხი "
                "უნდა ეყრდნობოდეს გადამოწმებად მუხლს, წინააღმდეგ შემთხვევაში სისტემა უარს იტყვის პასუხზე."
            )

            b1, b2 = st.columns(2)
            with b1:
                if st.button("✓ დადასტურებული კითხვა: K1/K2/K3 დაბალინტენსივიან საცხოვრებელ ზონაში", use_container_width=True):
                    st.session_state.rag_question_to_ask = VERIFIED_QUESTION
            with b2:
                if st.button("⚠ სცადეთ სასაზღვრო შემთხვევა: მშენებლობის ხმაურის ლიმიტები", use_container_width=True):
                    st.session_state.rag_question_to_ask = EDGE_CASE_QUESTION

            free_text = st.text_input("ან დასვით საკუთარი კითხვა", key="free_text_question")
            if st.button("კითხვა", key="ask_free_text"):
                if free_text.strip():
                    st.session_state.rag_question_to_ask = free_text.strip()

            if st.session_state.rag_question_to_ask:
                question = st.session_state.rag_question_to_ask
                st.session_state.rag_question_to_ask = None
                try:
                    with st.spinner("მიმდინარეობს იურიდიულ კორპუსში ძიება და დასაბუთებული პასუხის მომზადება... (რამდენიმე წამი)"):
                        rag_result = run_query(result_code, "Pro", question)
                    final = rag_result.get("rag_final_answer")
                    if final:
                        # "Approved" means the draft actually cleared both gates
                        # (grounded + critic-approved) via finalize_rag_answer.
                        # A bounce-exhausted fallback can still carry a valid,
                        # non-empty citation, so citation-presence alone isn't
                        # a reliable success signal — check the audit trail.
                        final = dict(final)
                        final["approved"] = any(
                            line.startswith("finalize_rag_answer")
                            for line in rag_result.get("audit", [])
                        )
                        st.session_state.rag_history.insert(0, (question, final, None))
                    else:
                        st.session_state.rag_history.insert(
                            0, (question, None, "ამ კითხვაზე პასუხი ვერ მომზადდა.")
                        )
                except Exception as e:
                    print(f"[RAG ERROR] {type(e).__name__}: {e}")
                    print(traceback.format_exc())
                    st.session_state.rag_history.insert(
                        0,
                        (
                            question,
                            None,
                            "იურიდიულმა ასისტენტმა მოულოდნელი შეცდომა დააფიქსირა და პასუხის "
                            "მომზადება ვერ მოხერხდა. გთხოვთ სცადოთ თავიდან.",
                        ),
                    )

            for question, final, error_msg in st.session_state.rag_history:
                st.markdown(f"**კითხვა: {question}**")
                if error_msg:
                    st.warning(error_msg)
                else:
                    citations = final.get("citations") or []
                    grounded = final.get("approved", False)
                    accent = TEAL if grounded else CORAL
                    box_bg = "#EAFBF8" if grounded else "#FFF5F4"
                    citation_html = "".join(
                        f'<span class="rag-citation" style="background:{accent};">{c}</span>'
                        for c in citations
                    )
                    st.markdown(
                        f"""
                        <div class="rag-answer" style="background:{box_bg}; border-left: 4px solid {accent};">
                            {final['answer']}
                            <div style="margin-top:0.6rem;">{citation_html}</div>
                        </div>
                        <div class="disclaimer">
                            ⚠️ მხოლოდ საკონსულტაციო ინფორმაცია — ამ პასუხზე დაყრდნობამდე აუცილებლად
                            გადაამოწმეთ შესაბამის მუნიციპალურ ორგანოსთან.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                st.markdown("")
