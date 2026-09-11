"""
api.py — the thin web layer around your existing agent.

This does NOT change anything in desks/, graph.py, or state.py — it just
gives your compiled graph (proptech_system) a door that a website can
knock on.

Run locally with:
    uvicorn api:app --reload

Then open http://127.0.0.1:8000/docs in a browser — that's a free,
auto-generated page where you can test this without writing any frontend
code at all.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from graph import proptech_system

app = FastAPI(title="PropTech Intelligence API")

# CORS: without this, a browser will BLOCK your future Next.js frontend
# from calling this API, even on your own machine, because they run on
# different ports (different "origins"). "*" means "allow any website" —
# fine for local development, but tighten this to your real frontend's
# domain before this ever goes to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# This class defines exactly what a request to /api/query must look like.
# FastAPI uses it to auto-validate incoming data — if someone sends a
# request missing cadastral_code, they get a clear error before your
# code even runs.
class QueryRequest(BaseModel):
    cadastral_code: str
    tier: str  # "regular" or "pro"
    rag_question: Optional[str] = None


@app.post("/api/query")
def query_plot(req: QueryRequest):
    initial_state = {
        "cadastral_code": req.cadastral_code,
        "tier": req.tier,
        "rag_question": req.rag_question,
        "plot": None, "not_found": False,
        "regular_response": None, "pro_response": None, "pro_input_error": None,
        "rag_draft": None, "rag_citation": None, "grounded": None,
        "critic_approved": None, "critic_feedback": None, "bounce_count": 0,
        "rag_final_answer": None, "audit": [],
    }
    config = {"configurable": {"thread_id": f"api-{req.cadastral_code}"}, "recursion_limit": 15}
    result = proptech_system.invoke(initial_state, config)

    # Return only what a frontend actually needs — not the internal audit trail
    return {
        "not_found": result["not_found"],
        "tier": req.tier,
        "regular_response": result["regular_response"],
        "pro_response": result["pro_response"],
        "pro_input_error": result["pro_input_error"],
        "rag_final_answer": result["rag_final_answer"],
    }


@app.get("/")
def health_check():
    return {"status": "ok", "message": "PropTech Intelligence API is running"}
