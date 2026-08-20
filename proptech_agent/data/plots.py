"""
PLOTS — the mock cadastral database.

Every rule-based desk (validate & lookup, tier dispatcher, regular formatter,
pro data engine) reads ONLY from this file. No agent ever touches it — it's
structured facts, so it's handled by structured code (R2, R3, R4, R5, R6, R9, R14).

legal_status is a closed enum, not free text — that's what makes it a lookup,
not a judgment call:
    "clean" | "active_mortgage" | "seizure" | "restricted"

zoning fields feed the Pro Data Engine's K1/K2/K3 calculation and are only
ever shown to Pro-tier queries (R9 tier gating).
"""

PLOTS = {
    "0100112233": {
        "owner_name": "Nino Beridze",
        "address": "12 Rustaveli Ave, Tbilisi",
        "total_area_sqm": 500,
        "land_designation": "non-agricultural",
        "legal_status": "clean",
        "legal_status_note": "No active encumbrances on record",
        "zoning": {
            "functional_zone": "residential_mixed_b2",
            "footprint_pct": 40,
            "far": 1.2,
            "green_space_pct": 15,
            "max_height_m": 15,
            "density_limit_units_per_ha": 60,
            "buffer_zones": [],
        },
    },
    "0200334455": {
        "owner_name": "Levan Kapanadze",
        "address": "45 Chavchavadze St, Batumi",
        "total_area_sqm": 1200,
        "land_designation": "agricultural",
        "legal_status": "active_mortgage",
        "legal_status_note": "Mortgage registered 2024-03-11, Bank of Georgia",
        "zoning": {
            "functional_zone": "agricultural_reserve",
            "footprint_pct": 5,
            "far": 0.1,
            "green_space_pct": 80,
            "max_height_m": 6,
            "density_limit_units_per_ha": 2,
            "buffer_zones": ["heritage_zone_100m"],
        },
    },
    "0300556677": {
        "owner_name": "Salome Janelidze",
        "address": "8 Agmashenebeli Ave, Tbilisi",
        "total_area_sqm": 350,
        "land_designation": "non-agricultural",
        "legal_status": "seizure",
        "legal_status_note": "Under court seizure order, case #4471-2026",
        "zoning": {
            "functional_zone": "residential_b1",
            "footprint_pct": 35,
            "far": 1.0,
            "green_space_pct": 20,
            "max_height_m": 12,
            "density_limit_units_per_ha": 45,
            "buffer_zones": [],
        },
    },
    "0400778899": {
        "owner_name": "Giorgi Melia",
        "address": "3 Kazbegi Ave, Tbilisi",
        "total_area_sqm": 800,
        "land_designation": "non-agricultural",
        "legal_status": "restricted",
        "legal_status_note": "Utility easement restricts construction on 30% of plot",
        "zoning": {
            "functional_zone": "residential_mixed_b3",
            "footprint_pct": 45,
            "far": 1.5,
            "green_space_pct": 10,
            "max_height_m": 21,
            "density_limit_units_per_ha": 90,
            "buffer_zones": ["utility_easement_gas"],
        },
    },
    "0500990011": {
        "owner_name": "Tamar Gogia",
        "address": "19 Pekini Ave, Tbilisi",
        "total_area_sqm": 600,
        "land_designation": "non-agricultural",
        "legal_status": "clean",
        "legal_status_note": "No active encumbrances on record",
        "zoning": {
            "functional_zone": "residential_mixed_b2",
            "footprint_pct": 140,  # deliberately malformed — exercises the R14 seatbelt
            "far": 1.3,
            "green_space_pct": 15,
            "max_height_m": 15,
            "density_limit_units_per_ha": 60,
            "buffer_zones": [],
        },
    },
}
