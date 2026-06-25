"""
src/api/app.py
Phase 6 — FastAPI Application

Responsibilities:
  - Expose POST /recommend as the primary recommendation endpoint.
  - Load and preprocess the dataset once at server startup (shared state).
  - Serve frontend static files from the /frontend directory (single-server deployment).
  - Handle all error scenarios with appropriate HTTP status codes.

Error handling matrix:
  Scenario                        HTTP   Detail
  ─────────────────────────────────────────────────────────────────────────────
  No restaurants found            404    "No restaurants found — try relaxing filters"
  GROQ_API_KEY missing            500    "Groq API key not configured"
  Groq rate-limit / server error  503    "LLM service temporarily unavailable"
  LLM response unparseable        500    "Could not parse LLM response"
  Invalid request body            422    (FastAPI / Pydantic auto-validation)
  Startup data load failure       500    Logged; server stays up, returns 503 per request

CORS:
  Origins are open in development. Restrict origins in production via the
  CORS_ORIGINS environment variable (comma-separated list).
"""

import logging
import os

import pandas as pd
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api.schemas import (
    PreferencesRequest,
    RecommendationItem,
    RecommendResponse,
)
from src.models.preferences import UserPreferences
from src.models.recommendation import Recommendation
from src.filter.engine import filter_with_fallback
from src.prompt.builder import build_prompt
from src.llm.client import call_groq
from src.llm.parser import parse_response
from config.settings import OUTPUT_TOP_K

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared application state — DataFrame loaded once at startup
# ---------------------------------------------------------------------------

class _AppState:
    df: pd.DataFrame | None = None
    startup_error: str | None = None


_state = _AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the dataset once at startup and release resources on shutdown."""
    global _state
    try:
        logger.info("Loading dataset at startup...")
        from src.data.loader import load_or_fetch
        from src.data.preprocessor import preprocess

        raw = load_or_fetch()

        # Only preprocess if the loaded data is raw (no budget_category column).
        # If load_or_fetch returns the cached preprocessed DataFrame, skip preprocess.
        if "budget_category" not in raw.columns:
            _state.df = preprocess(raw)
        else:
            _state.df = raw

        logger.info(
            "Dataset ready: %d restaurants loaded.",
            len(_state.df),
        )
    except SystemExit:
        _state.startup_error = (
            "Dataset failed to load at startup. "
            "Check server logs for details."
        )
        logger.error("Dataset load raised SystemExit — server degraded.")
    except Exception as exc:
        _state.startup_error = str(exc)
        logger.exception("Unexpected error during dataset startup: %s", exc)

    yield  # Server is now running
    # (shutdown cleanup can be added here if needed)


app = FastAPI(
    title="Restaurant Recommender API",
    description=(
        "AI-powered restaurant recommendation system powered by Groq LLM. "
        "Submit user preferences and receive ranked, explained recommendations."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS middleware
# ---------------------------------------------------------------------------

_cors_origins_env = os.getenv("CORS_ORIGINS", "")
_cors_origins = (
    [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
    if _cors_origins_env
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health-check endpoint
# ---------------------------------------------------------------------------


@app.get("/health", tags=["meta"])
async def health_check() -> JSONResponse:
    """
    Returns 200 OK if the dataset is loaded and the server is ready.
    Returns 503 if the dataset failed to load.
    """
    if _state.startup_error:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "detail": _state.startup_error},
        )
    return JSONResponse(
        content={
            "status": "ok",
            "restaurants_loaded": len(_state.df) if _state.df is not None else 0,
        }
    )


# ---------------------------------------------------------------------------
# Primary recommendation endpoint
# ---------------------------------------------------------------------------


def _local_rank_fallback(
    candidates: pd.DataFrame,
    prefs,
    top_k: int,
) -> list[Recommendation]:
    """
    Score and rank candidates locally without calling the LLM.
    Used as a fallback when the Groq API is unavailable.

    Scoring: rating (60%) + normalised vote count (35%) + cuisine match bonus (5%).
    Cuisine match is optional — no penalty for restaurants that don't match if
    the user selected cuisine vibes.
    """
    import re as _re
    logger.warning("Using local scoring fallback (LLM unavailable).")
    df = candidates.head(top_k * 2).copy()  # take extra headroom

    # Parse requested cuisines (comma-separated, may be empty)
    requested_cuisines: list[str] = []
    if prefs.cuisine:
        requested_cuisines = [c.strip().lower() for c in prefs.cuisine.split(",") if c.strip()]

    # Cuisine match helper — True if restaurant serves any requested cuisine
    def _cuisine_match(row_cuisine: str) -> bool:
        if not requested_cuisines:
            return False
        row_lower = str(row_cuisine).lower()
        return any(
            _re.search(_re.escape(c), row_lower) for c in requested_cuisines
        )

    # Normalise votes to [0, 1]
    max_votes = df["votes"].max() or 1
    df["_cuisine_match"] = df["cuisine"].apply(_cuisine_match)
    df["_score"] = (
        df["rating"] * 0.60
        + (df["votes"] / max_votes) * 0.35 * 5.0   # scale votes to ~5-pt range
        + df["_cuisine_match"].astype(float) * 0.50  # cuisine match bonus
    )
    df = df.sort_values("_score", ascending=False).head(top_k).reset_index(drop=True)

    results: list[Recommendation] = []
    for rank, (_, row) in enumerate(df.iterrows(), start=1):
        cost_val = row.get("avg_cost_for_two", None)
        estimated_cost = f"\u20b9{int(cost_val)} for two" if pd.notna(cost_val) else "N/A"

        cuisine_display = str(row["cuisine"]).title()
        is_match = bool(row.get("_cuisine_match", False))

        cuisine_note = ""
        if requested_cuisines and is_match:
            cuisine_note = f"Matches your {', '.join(c.title() for c in requested_cuisines)} preference. "
        elif requested_cuisines and not is_match:
            cuisine_note = f"Cuisine broadened beyond your selection — included by rating & popularity. "

        explanation = (
            f"Ranked #{rank} by algorithm score (rating {row['rating']:.1f}/5 \u00b7 "
            f"{int(row['votes']):,} votes). "
            f"{cuisine_note}"
            f"{cuisine_display} cuisine in {str(row['location']).title()} "
            f"at {estimated_cost}. "
            f"Note: AI explanations unavailable \u2014 Groq API is currently unreachable "
            f"from this network."
        )

        results.append(Recommendation(
            rank=rank,
            name=str(row["name"]),
            cuisine=str(row["cuisine"]),
            rating=float(row["rating"]),
            estimated_cost=estimated_cost,
            explanation=explanation,
        ))

    return results


@app.post("/recommend", response_model=RecommendResponse, tags=["recommend"])
async def recommend(prefs_req: PreferencesRequest) -> RecommendResponse:
    """
    Accept user dining preferences and return AI-ranked restaurant recommendations.

    **Flow:**
    1. Validate input (Pydantic — automatic HTTP 422 on failure)
    2. Filter dataset candidates using progressive fallback
    3. Build LLM prompt from candidates + preferences
    4. Call Groq API (with retry/backoff)
    5. Parse ranked recommendations from LLM response
    6. Return top-K results

    **Errors:**
    - `404` — No restaurants match the given preferences
    - `500` — Groq API key not configured / LLM response unparseable
    - `503` — Dataset not loaded / Groq service temporarily unavailable
    """
    # Guard: dataset must be ready
    if _state.startup_error or _state.df is None:
        raise HTTPException(
            status_code=503,
            detail=_state.startup_error or "Dataset not yet loaded. Please retry.",
        )

    # ── Step 1: Normalize input and build internal UserPreferences ────────────
    prefs = UserPreferences(
        location=prefs_req.location.strip().lower(),
        budget=prefs_req.budget.strip().lower(),
        cuisine=prefs_req.cuisine.strip().lower(),
        min_rating=prefs_req.min_rating,
        extras=prefs_req.extras.strip(),
    )

    # ── Step 2: Filter candidates ─────────────────────────────────────────────
    filter_result = filter_with_fallback(_state.df, prefs)
    candidates = filter_result.candidates

    if candidates.empty:
        raise HTTPException(
            status_code=404,
            detail=(
                "No restaurants found matching your preferences. "
                "Try a broader location, different cuisine, or lower minimum rating."
            ),
        )

    logger.info(
        "Filter returned %d candidates (fallback_level=%d) for location='%s'.",
        len(candidates),
        filter_result.fallback_level,
        prefs.location,
    )

    # ── Step 3: Build LLM prompt ──────────────────────────────────────────────
    system_prompt, user_prompt = build_prompt(candidates, prefs)

    # ── Step 4: Call Groq LLM (with local fallback on failure) ────────────────
    use_fallback = False
    raw_response = ""
    fallback_note = ""

    try:
        raw_response = call_groq(system_prompt, user_prompt)
    except (RuntimeError, ValueError) as exc:
        msg = str(exc)
        logger.error("Groq call failed — activating local scoring fallback: %s", msg)
        use_fallback = True

        if "GROQ_API_KEY" in msg:
            fallback_note = "Groq API key not configured — using local algorithm scoring."
        elif "403" in msg or "access denied" in msg.lower() or "network" in msg.lower():
            fallback_note = (
                "Groq API unreachable (network/firewall block) — "
                "showing algorithm-scored results instead."
            )
        else:
            fallback_note = "AI service temporarily unavailable — using local algorithm scoring."

    if use_fallback:
        recs = _local_rank_fallback(candidates, prefs, OUTPUT_TOP_K)
        if not recs:
            raise HTTPException(
                status_code=404,
                detail="No restaurants found matching your preferences.",
            )
        return RecommendResponse(
            recommendations=[
                RecommendationItem(
                    rank=r.rank,
                    name=r.name,
                    cuisine=r.cuisine,
                    rating=r.rating,
                    estimated_cost=r.estimated_cost,
                    explanation=r.explanation,
                )
                for r in recs
            ],
            total_found=len(candidates),
            fallback_level=max(filter_result.fallback_level, 1),
            fallback_message=fallback_note or filter_result.fallback_message,
        )

    # ── Step 5: Parse LLM response ────────────────────────────────────────────
    recs = parse_response(raw_response, candidates)

    if not recs:
        logger.error(
            "Parser returned 0 recommendations. Raw response: %s",
            raw_response[:500],
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Could not parse AI recommendations from the response. "
                "Please try again."
            ),
        )

    # ── Step 6: Build and return response ─────────────────────────────────────
    top_k = recs[:OUTPUT_TOP_K]
    return RecommendResponse(
        recommendations=[
            RecommendationItem(
                rank=r.rank,
                name=r.name,
                cuisine=r.cuisine,
                rating=r.rating,
                estimated_cost=r.estimated_cost,
                explanation=r.explanation,
            )
            for r in top_k
        ],
        total_found=len(candidates),
        fallback_level=filter_result.fallback_level,
        fallback_message=filter_result.fallback_message,
    )


# ---------------------------------------------------------------------------
# Serve frontend static files
# ---------------------------------------------------------------------------

_FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "frontend",
)

if os.path.isdir(_FRONTEND_DIR):
    # Mount at "/" — must come LAST so it doesn't shadow the API routes
    app.mount(
        "/",
        StaticFiles(directory=_FRONTEND_DIR, html=True),
        name="frontend",
    )
    logger.info("Serving frontend from: %s", _FRONTEND_DIR)
else:
    logger.warning(
        "Frontend directory not found at '%s'. "
        "Skipping static file mount (Phase 7 not yet built).",
        _FRONTEND_DIR,
    )
