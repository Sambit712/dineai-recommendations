"""
src/filter/engine.py
Phase 4 -- Filter Engine

Responsibilities:
  - Filter the preprocessed DataFrame using UserPreferences
  - Return top-N ranked candidates
  - Apply progressive fallback when too few results are found

Edge cases handled:
  EC-F01  Zero results after all filters   -- 3-level progressive fallback
  EC-F02  Only one candidate found         -- pass count to prompt builder via metadata
  EC-F03  Cuisine partial match too broad  -- handled upstream in handler (MIN_CUISINE_LEN)
  EC-F04  Location partial match ambiguity -- detect multi-city match; warn user
  EC-F05  All restaurants have same rating -- tertiary sort by cost ASC
  EC-F06  FILTER_TOP_N > available results -- return all available (head() handles this)
"""

import re
import pandas as pd
from dataclasses import dataclass, field
from rich.console import Console

from src.models.preferences import UserPreferences
from config.settings import FILTER_TOP_N

console = Console(stderr=True)

# Minimum results before fallback kicks in
FALLBACK_THRESHOLD   = 3
# How much to relax min_rating per fallback level
RATING_RELAXATION    = 0.5
# Maximum rating relaxation steps
MAX_RATING_RELAXATIONS = 2


# ---------------------------------------------------------------------------
# Result container — carries candidates + metadata about how they were found
# ---------------------------------------------------------------------------

@dataclass
class FilterResult:
    candidates: pd.DataFrame
    fallback_level: int = 0          # 0 = exact match; 1-3 = fallback applied
    fallback_message: str = ""       # human-readable description of relaxation
    matched_cities: list[str] = field(default_factory=list)  # for EC-F04 warning


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def filter_with_fallback(
    df: pd.DataFrame,
    prefs: UserPreferences,
) -> FilterResult:
    """
    Primary entry point. Filters restaurants using UserPreferences and
    applies up to 3 levels of progressive relaxation if results are scarce.

    Returns a FilterResult containing the candidate DataFrame and metadata.
    """
    # ── EC-F04: Detect multi-city location match and warn ────────────────────
    matched_cities = _detect_location_ambiguity(df, prefs.location)

    # ── Level 0: Full strict filter ──────────────────────────────────────────
    result = _apply_filters(df, prefs)
    if len(result) >= FALLBACK_THRESHOLD:
        return FilterResult(
            candidates=result,
            fallback_level=0,
            matched_cities=matched_cities,
        )

    # ── Level 1: Drop cuisine filter ─────────────────────────────────────────
    console.print(
        f"  [dim]Only {len(result)} result(s) found. "
        "Relaxing cuisine filter...[/dim]"
    )
    result = _apply_filters(df, prefs, drop_cuisine=True)
    if len(result) >= FALLBACK_THRESHOLD:
        if prefs.cuisine:
            _cuisines = [c.strip().title() for c in prefs.cuisine.split(",") if c.strip()]
            _cuisine_label = " / ".join(_cuisines) if _cuisines else prefs.cuisine.title()
            _fb_msg = (
                f"Cuisine filter removed (no {_cuisine_label} restaurants "
                f"found matching all criteria — showing all cuisines)."
            )
        else:
            _fb_msg = "Budget filter applied with broadened location matching."
        return FilterResult(
            candidates=result,
            fallback_level=1,
            fallback_message=_fb_msg,
            matched_cities=matched_cities,
        )

    # ── Level 2: Also drop budget filter ─────────────────────────────────────
    console.print(
        f"  [dim]Still only {len(result)} result(s). "
        "Relaxing budget filter...[/dim]"
    )
    result = _apply_filters(df, prefs, drop_cuisine=True, drop_budget=True)
    if len(result) >= FALLBACK_THRESHOLD:
        return FilterResult(
            candidates=result,
            fallback_level=2,
            fallback_message=(
                f"Cuisine and budget filters removed. "
                f"Showing restaurants in {prefs.location.title()} with rating >= {prefs.min_rating}."
            ),
            matched_cities=matched_cities,
        )

    # ── Level 3: Also lower min_rating ───────────────────────────────────────
    relaxed_rating = max(0.0, prefs.min_rating - RATING_RELAXATION)
    console.print(
        f"  [dim]Still only {len(result)} result(s). "
        f"Lowering minimum rating to {relaxed_rating}...[/dim]"
    )
    result = _apply_filters(
        df, prefs,
        drop_cuisine=True,
        drop_budget=True,
        override_rating=relaxed_rating,
    )

    fallback_msg = (
        f"All filters relaxed. Showing restaurants in {prefs.location.title()} "
        f"with rating >= {relaxed_rating} (was {prefs.min_rating})."
    )

    return FilterResult(
        candidates=result,
        fallback_level=3,
        fallback_message=fallback_msg if not result.empty else "",
        matched_cities=matched_cities,
    )


# ---------------------------------------------------------------------------
# Core filter function
# ---------------------------------------------------------------------------

def _apply_filters(
    df: pd.DataFrame,
    prefs: UserPreferences,
    *,
    drop_cuisine: bool = False,
    drop_budget: bool = False,
    override_rating: float | None = None,
) -> pd.DataFrame:
    """
    Apply up to 4 filters on the DataFrame and return top-N sorted results.

    Parameters
    ----------
    drop_cuisine     : Skip cuisine filter (fallback Level 1+)
    drop_budget      : Skip budget_category filter (fallback Level 2+)
    override_rating  : Use this value instead of prefs.min_rating (fallback Level 3)
    """
    result = df.copy()
    min_rating = override_rating if override_rating is not None else prefs.min_rating

    # ── Filter 1: Location (partial, regex-safe) ──────────────────────────────
    loc_pattern = re.escape(prefs.location)
    result = result[
        result["location"].str.contains(loc_pattern, case=False, na=False, regex=True)
    ]

    # ── Filter 2: Budget ──────────────────────────────────────────────────────
    if not drop_budget:
        result = result[result["budget_category"] == prefs.budget]

    # ── Filter 3: Cuisine (Optional Prediction Criteria) ──────────────────────
    # We no longer filter out restaurants that don't match the cuisine.
    # Instead, we flag them to prioritize them during sorting.
    result["cuisine_match"] = True
    if not drop_cuisine and prefs.cuisine:
        cuisines = [c.strip() for c in prefs.cuisine.split(",") if c.strip()]
        if len(cuisines) == 1:
            cui_pattern = re.escape(cuisines[0])
        else:
            cui_pattern = "|".join(re.escape(c) for c in cuisines)
        # Restaurants matching ANY of the selected cuisines get True
        result["cuisine_match"] = result["cuisine"].str.contains(cui_pattern, case=False, na=False, regex=True)

    # ── Filter 4: Minimum rating ──────────────────────────────────────────────
    result = result[result["rating"] >= min_rating]

    # ── EC-F05: Sort by cuisine match DESC → rating DESC → votes DESC → cost ASC
    result = result.sort_values(
        by=["cuisine_match", "rating", "votes", "avg_cost_for_two"],
        ascending=[False, False, False, True],
    )
    result = result.drop(columns=["cuisine_match"])

    # ── EC-F06: head() gracefully handles fewer rows than FILTER_TOP_N ────────
    return result.head(FILTER_TOP_N).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Location ambiguity detection (EC-F04)
# ---------------------------------------------------------------------------

def _detect_location_ambiguity(df: pd.DataFrame, location: str) -> list[str]:
    """
    Check if the user's location string partially matches more than one
    distinct city in the dataset.

    Returns a sorted list of matched city names (empty if unambiguous).
    """
    pattern = re.escape(location)
    matched = (
        df[df["location"].str.contains(pattern, case=False, na=False, regex=True)][
            "location"
        ]
        .str.title()
        .unique()
        .tolist()
    )

    if len(matched) > 1:
        console.print(
            f"\n  [yellow]Note:[/yellow] '{location}' matches multiple areas: "
            + ", ".join(f"[bold]{c}[/bold]" for c in sorted(matched)[:5])
            + (f" (+{len(matched)-5} more)" if len(matched) > 5 else "")
            + "\n  Showing combined results. Enter a more specific name to narrow down.\n"
        )

    return sorted(matched)
