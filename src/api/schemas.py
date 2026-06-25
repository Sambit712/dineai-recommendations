"""
src/api/schemas.py -- Pydantic request/response models for the REST API

These schemas sit at the API boundary and are separate from the internal
dataclasses (UserPreferences, Recommendation) so that API validation,
serialization, and documentation (OpenAPI) are handled cleanly by FastAPI/Pydantic.
"""

from typing import List, Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class PreferencesRequest(BaseModel):
    """
    Body sent by the frontend when requesting restaurant recommendations.

    All string fields are expected to already be lowercase/stripped by the
    frontend; the API does a final normalization before passing to the filter
    engine.
    """

    location:   str   = Field(..., min_length=1, description="City or area, e.g. 'bangalore'")
    budget:     Literal["low", "medium", "high"] = Field(..., description="Budget tier")
    cuisine:    str   = Field("", description="Preferred cuisine type, e.g. 'italian' (empty = any cuisine)")
    min_rating: float = Field(0.0, ge=0.0, le=5.0, description="Minimum acceptable rating (0.0–5.0)")
    extras:     str   = Field("", description="Free-text additional preferences (optional)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "location": "bangalore",
                    "budget": "medium",
                    "cuisine": "north indian",
                    "min_rating": 4.0,
                    "extras": "family-friendly, quick service",
                }
            ]
        }
    }


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class RecommendationItem(BaseModel):
    """
    A single ranked restaurant recommendation returned to the frontend.
    Mirrors the internal Recommendation dataclass but as a Pydantic model
    so FastAPI can serialize/validate it automatically.
    """

    rank:           int   = Field(..., description="1-indexed rank assigned by the LLM")
    name:           str   = Field(..., description="Restaurant name")
    cuisine:        str   = Field(..., description="Cuisine type(s)")
    rating:         float = Field(..., ge=0.0, le=5.0, description="Average rating")
    estimated_cost: str   = Field(..., description="Human-readable cost string, e.g. '₹800 for two'")
    explanation:    str   = Field(..., description="LLM-generated explanation of why this fits the user")


class RecommendResponse(BaseModel):
    """
    Full response payload for a POST /recommend call.

    `total_found` reflects the number of candidates that passed the filter
    engine (before LLM re-ranking to OUTPUT_TOP_K), which is useful for the
    frontend to show context like '3 of 8 matching restaurants shown'.

    `fallback_level` (0–3) and `fallback_message` are populated when the
    filter engine had to relax criteria to find enough candidates. The
    frontend can surface these to inform the user that results were broadened.
    """

    recommendations:  List[RecommendationItem] = Field(..., description="Ranked list of recommendations")
    total_found:      int                       = Field(..., description="Total candidates found before LLM ranking")
    fallback_level:   int                       = Field(0,  description="0 = exact match; 1–3 = filters progressively relaxed")
    fallback_message: str                       = Field("", description="Human-readable description of filter relaxation applied")
