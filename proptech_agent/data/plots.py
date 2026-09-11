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

Required record shape — every entry in PLOTS, keyed by a 10-digit cadastral
code string (matches lookup.py's CADASTRAL_CODE_PATTERN), must be a dict with:

    owner_name                str   required
    address                   str   required
    total_area_sqm            int | float   required, > 0
    land_designation          str   required, e.g. "agricultural" | "non-agricultural"
    legal_status              str   required, closed enum (see above)
    legal_status_note         str   required (free text, shown as-is to users)
    zoning                    dict  required, see below

    zoning = {
        functional_zone               str    required (free text zone label —
                                                see the known limitation in
                                                CLAUDE.md: these are placeholders
                                                and don't match legal_corpus.json)
        footprint_pct                 int | float   required
                                                — validated by pro.py as
                                                0 < footprint_pct <= 100
        far                            int | float   required
                                                — validated by pro.py as far > 0
        green_space_pct               int | float   required
                                                — validated by pro.py as
                                                0 < green_space_pct <= 100
        max_height_m                   int | float   required, shown as-is (R14
                                                does not range-check this field)
        density_limit_units_per_ha     int | float   required, shown as-is (R14
                                                does not range-check this field)
        buffer_zones                   list[str]     required, may be empty []
    }

No field is Optional at the data layer — pro_data_engine (R14) validates
footprint_pct, far, and green_space_pct before use and rejects the record
with pro_input_error if they're out of range, but it assumes every key above
is present and will raise KeyError on a record missing one. If you add a
plot with different fields, update pro.py's _validate_zoning_inputs and the
response dicts in pro.py / regular.py to match — this file is data only.
"""

PLOTS = {
    "0100112233": {
        "owner_name": "ნინო ბერიძე",
        "address": "რუსთაველის ქ. 12, ბათუმი",
        "total_area_sqm": 500,
        "land_designation": "non-agricultural",
        "legal_status": "clean",
        "legal_status_note": "რეესტრში აქტიური დატვირთვები არ ფიქსირდება",
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
        "owner_name": "ლევან კაპანაძე",
        "address": "ჭავჭავაძის ქ. 45, ბათუმი",
        "total_area_sqm": 1200,
        "land_designation": "agricultural",
        "legal_status": "active_mortgage",
        "legal_status_note": "იპოთეკა რეგისტრირებულია 2024-03-11, საქართველოს ბანკი",
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
        "owner_name": "სალომე ჯანელიძე",
        "address": "აკაკი წერეთლის ქ. 8, ბათუმი",
        "total_area_sqm": 350,
        "land_designation": "non-agricultural",
        "legal_status": "seizure",
        "legal_status_note": "დაყადაღებულია სასამართლოს განჩინებით, საქმე #4471-2026",
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
        "owner_name": "გიორგი მელია",
        "address": "ხიმშიაშვილის ქ. 3, ბათუმი",
        "total_area_sqm": 800,
        "land_designation": "non-agricultural",
        "legal_status": "restricted",
        "legal_status_note": "კომუნალური სერვიტუტი ზღუდავს მშენებლობას ნაკვეთის 30%-ზე",
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
        "owner_name": "თამარ გოგია",
        "address": "პარნავაზ მეფის გამზ. 19, ბათუმი",
        "total_area_sqm": 600,
        "land_designation": "non-agricultural",
        "legal_status": "clean",
        "legal_status_note": "რეესტრში აქტიური დატვირთვები არ ფიქსირდება",
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
