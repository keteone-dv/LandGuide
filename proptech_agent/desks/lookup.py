"""
Validate & lookup (R1-R3) and tier dispatcher (R9) — plain functions.

Format-checking a code and looking it up in a dict is arithmetic and lookup,
not judgment — no model call belongs here.
"""
import re
from data.plots import PLOTS
from state import PlotQueryState

CADASTRAL_CODE_PATTERN = re.compile(r"^\d{10}$")


def validate_and_lookup(state: PlotQueryState) -> dict:
    code = state["cadastral_code"]

    if not CADASTRAL_CODE_PATTERN.match(code):
        return {
            "plot": None,
            "not_found": True,
            "audit": state["audit"] + [f"validate_and_lookup: '{code}' failed format check"],
        }

    plot = PLOTS.get(code)
    if plot is None:
        return {
            "plot": None,
            "not_found": True,
            "audit": state["audit"] + [f"validate_and_lookup: '{code}' not in database"],
        }

    return {
        "plot": plot,
        "not_found": False,
        "audit": state["audit"] + [f"validate_and_lookup: found plot at {plot['address']}"],
    }


def tier_dispatch(state: PlotQueryState) -> str:
    """R9 — the fork. Not-found always wins; otherwise route by tier."""
    if state["not_found"]:
        return "not_found_response"
    return "regular_formatter" if state["tier"] == "regular" else "pro_data_engine"
