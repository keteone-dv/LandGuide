"""
Regular formatter (R4) — filters the full plot record down to the citizen-facing
fields. Plain formatting, no judgment: covers R4 and the tier gating half of R9.
"""
from state import PlotQueryState


def regular_formatter(state: PlotQueryState) -> dict:
    p = state["plot"]
    response = {
        "owner_name": p["owner_name"],
        "address": p["address"],
        "total_area_sqm": p["total_area_sqm"],
        "land_designation": p["land_designation"],
        "legal_status": p["legal_status"],
        "legal_status_note": p["legal_status_note"],
    }
    return {
        "regular_response": response,
        "audit": state["audit"] + ["regular_formatter: basic plot details returned"],
    }


def not_found_response(state: PlotQueryState) -> dict:
    return {
        "audit": state["audit"] + ["not_found_response: no data available for this cadastral code"],
    }
