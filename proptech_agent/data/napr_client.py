"""
napr_client.py — live client for Georgia's National Public Registry (NAPR)
plot search API. Fetches real plot data to eventually replace the mock
records in plots.py.

NOTE: this endpoint (naprweb.reestri.gov.ge) is not a documented public API —
it was found by inspecting the registry's own search page. Treat it as
unofficial: no SLA, no rate-limit guarantees, and its shape could change
without notice. Wrap calls defensively.
"""
import requests
import json

NAPR_SEARCH_URL = "https://naprweb.reestri.gov.ge/api/search"


def fetch_plot_from_napr(cadastral_code: str) -> dict | None:
    payload = json.dumps({
        "address": "", "cadcode": cadastral_code, "datefrom": None,
        "dateto": None, "page": 1, "person": "", "regno": "", "search": "",
    })
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(NAPR_SEARCH_URL, headers=headers, data=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"napr_client: request failed for {cadastral_code}: {e}")
        return None


# TODO (Claude Code): add normalize_napr_response(raw: dict) -> dict here,
# mapping the real fields (see data/samples/napr_sample_response.json) into
# the same shape as records in plots.py, so desks/lookup.py can swap sources
# without any other file changing.