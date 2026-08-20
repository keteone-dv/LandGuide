"""
Pro data engine (R5, R6, R14) — plain function, no model call.

K1/K2/K3 are arithmetic derived from raw zoning inputs, not opinions, so this
is a deterministic function like the reference's policy desk. R14 validates
the raw inputs before calculating anything, so a malformed plot record fails
loudly instead of silently producing a nonsense coefficient.
"""
from state import PlotQueryState


def _validate_zoning_inputs(z: dict) -> str | None:
    """Returns an error string if inputs are out of sane range, else None."""
    if not (0 < z["footprint_pct"] <= 100):
        return f"footprint_pct {z['footprint_pct']} is out of range (0-100)"
    if not (0 < z["green_space_pct"] <= 100):
        return f"green_space_pct {z['green_space_pct']} is out of range (0-100)"
    if z["far"] <= 0:
        return f"far {z['far']} must be positive"
    return None


def pro_data_engine(state: PlotQueryState) -> dict:
    p = state["plot"]
    z = p["zoning"]

    error = _validate_zoning_inputs(z)
    if error:
        return {
            "pro_input_error": error,
            "pro_response": None,
            "audit": state["audit"] + [f"pro_data_engine: REJECTED — {error}"],
        }

    area = p["total_area_sqm"]
    k1_footprint_sqm = round(area * z["footprint_pct"] / 100, 1)
    k2_buildable_floor_area_sqm = round(area * z["far"], 1)
    k3_green_space_sqm = round(area * z["green_space_pct"] / 100, 1)

    response = {
        "owner_name": p["owner_name"],
        "address": p["address"],
        "total_area_sqm": area,
        "land_designation": p["land_designation"],
        "legal_status": p["legal_status"],
        "legal_status_note": p["legal_status_note"],
        "functional_zone": z["functional_zone"],
        "k1_footprint_sqm": k1_footprint_sqm,
        "k2_buildable_floor_area_sqm": k2_buildable_floor_area_sqm,
        "k3_green_space_sqm": k3_green_space_sqm,
        "max_height_m": z["max_height_m"],
        "density_limit_units_per_ha": z["density_limit_units_per_ha"],
        "buffer_zones": z["buffer_zones"],
    }
    return {
        "pro_response": response,
        "pro_input_error": None,
        "audit": state["audit"] + [
            f"pro_data_engine: K1={k1_footprint_sqm}, K2={k2_buildable_floor_area_sqm}, "
            f"K3={k3_green_space_sqm}"
        ],
    }


def needs_rag(state: PlotQueryState) -> str:
    """Fork after the Pro data engine: only enter the RAG chat if a question was asked."""
    if state.get("rag_question"):
        return "rag_answer_agent"
    return "__end__"
