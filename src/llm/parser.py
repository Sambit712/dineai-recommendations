"""
src/llm/parser.py
Phase 5 — LLM Response Parser

Responsibilities:
  - Parse the raw LLM text into a list of ranked Recommendation objects.
  - Look up restaurant metadata (cuisine, rating, cost) from the candidates
    DataFrame using a case-insensitive name match.
  - Handle partial or malformed LLM output gracefully.

Parsing strategy:
  - Split on "#<digit>." boundary lines.
  - Extract rank number and restaurant name from the header line.
  - Extract explanation from the "Explanation: ..." line (multi-line aware).
  - If a name cannot be matched in the candidates DataFrame, the block is
    skipped (prevents fabricated restaurants leaking into results).

Edge cases:
  EC-P01  LLM returns 0 parseable blocks → caller gets empty list
  EC-P02  Name in LLM response doesn't match candidates → block skipped
  EC-P03  Explanation text contains newlines → captured with re.DOTALL
  EC-P04  LLM outputs duplicate ranks → deduplicated (keep first occurrence)
"""

import logging
import re

import pandas as pd

from src.models.recommendation import Recommendation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_response(
    raw: str,
    candidates: pd.DataFrame,
) -> list[Recommendation]:
    """
    Parse the LLM's raw text response into a sorted list of Recommendation objects.

    Parameters
    ----------
    raw : str
        The full text returned by call_groq().
    candidates : pd.DataFrame
        The filtered candidates DataFrame (used for metadata lookup).

    Returns
    -------
    list[Recommendation]
        Recommendations sorted by rank (ascending). May be empty if parsing
        completely fails (EC-P01).
    """
    if not raw or not raw.strip():
        logger.warning("parse_response received empty string — returning []")
        return []

    # Build a name→row lookup for O(1) lookups (case-insensitive)
    name_index: dict[str, pd.Series] = {
        str(row["name"]).lower().strip(): row
        for _, row in candidates.iterrows()
    }

    # Split raw text into recommendation blocks
    # Each block starts with a line like "#1. Restaurant Name"
    blocks = re.split(r"\n(?=#\d+\.)", raw.strip())

    seen_ranks: set[int] = set()
    recommendations: list[Recommendation] = []

    for block in blocks:
        rec = _parse_block(block, name_index, seen_ranks)
        if rec is not None:
            recommendations.append(rec)
            seen_ranks.add(rec.rank)

    if not recommendations:
        logger.warning(
            "No recommendations parsed from LLM response. "
            "Raw response (first 400 chars): %s",
            raw[:400],
        )

    return sorted(recommendations, key=lambda r: r.rank)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_block(
    block: str,
    name_index: dict[str, pd.Series],
    seen_ranks: set[int],
) -> Recommendation | None:
    """
    Parse a single text block into a Recommendation, or return None on failure.
    """
    # Match rank + name: "#1. Restaurant Name"
    rank_match = re.match(r"#(\d+)\.\s+(.+)", block)
    if not rank_match:
        return None

    rank = int(rank_match.group(1))
    raw_name = rank_match.group(2).strip()

    # Skip duplicate ranks (EC-P04)
    if rank in seen_ranks:
        logger.debug("Skipping duplicate rank %d from LLM response.", rank)
        return None

    # Extract explanation (everything after "Explanation: ", multi-line)
    expl_match = re.search(r"Explanation:\s+(.+)", block, re.DOTALL)
    explanation = expl_match.group(1).strip() if expl_match else ""

    # Lookup metadata in candidates DataFrame (case-insensitive)
    row = name_index.get(raw_name.lower())

    if row is None:
        # Try a fuzzy prefix match (handles trailing punctuation / truncation)
        row = _fuzzy_name_match(raw_name, name_index)

    if row is None:
        logger.warning(
            "LLM recommended '%s' (rank %d) but it was not found in candidates. "
            "Skipping.",
            raw_name, rank,
        )
        return None  # EC-P02: fabricated name → skip

    cost_val = row.get("avg_cost_for_two", "N/A")
    if pd.notna(cost_val):
        estimated_cost = f"₹{int(cost_val)} for two"
    else:
        estimated_cost = "N/A"

    return Recommendation(
        rank=rank,
        name=str(row["name"]),
        cuisine=str(row["cuisine"]),
        rating=float(row["rating"]),
        estimated_cost=estimated_cost,
        explanation=explanation,
    )


def _fuzzy_name_match(
    raw_name: str,
    name_index: dict[str, pd.Series],
) -> pd.Series | None:
    """
    Try a relaxed name match: check if any indexed name is a substring of
    raw_name or vice versa (handles LLM adding/dropping suffixes like 'Restaurant').
    """
    raw_lower = raw_name.lower().strip()
    for indexed_name, row in name_index.items():
        if indexed_name in raw_lower or raw_lower in indexed_name:
            logger.debug(
                "Fuzzy name match: '%s' ≈ '%s'", raw_name, indexed_name
            )
            return row
    return None
