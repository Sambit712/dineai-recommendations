"""
src/prompt/builder.py
Phase 5 — Prompt Builder

Responsibilities:
  - Construct a high-quality LLM prompt from filtered restaurant candidates
    and user preferences.
  - Returns a (system_prompt, user_prompt) tuple consumed by src/llm/client.py

Design decisions:
  - System prompt is kept short and role-specific (concierge persona)
  - User prompt embeds both the preferences AND the candidate list so the LLM
    has full context in a single message.
  - Each candidate row is formatted compactly to stay within token limits even
    when FILTER_TOP_N is large.
"""

import pandas as pd
from src.models.preferences import UserPreferences


# ---------------------------------------------------------------------------
# System prompt — defines the LLM persona and output format
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert restaurant concierge. Given a list of candidate restaurants \
and a user's dining preferences, rank the top 3–5 best-matching restaurants \
and explain concisely why each is a great fit.

Respond ONLY in this exact format for each recommendation:

#<rank>. <Restaurant Name>
Explanation: <2–3 sentences that reference the user's preferences specifically>

Do not add extra commentary before or after the ranked list.\
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_prompt(
    candidates: pd.DataFrame,
    prefs: UserPreferences,
) -> tuple[str, str]:
    """
    Build the (system_prompt, user_prompt) pair for the Groq LLM call.

    Parameters
    ----------
    candidates : pd.DataFrame
        Filtered restaurant candidates (output of filter_with_fallback).
    prefs : UserPreferences
        Validated user preferences.

    Returns
    -------
    tuple[str, str]
        (system_prompt, user_prompt) — pass directly to call_groq().
    """
    restaurant_list = _format_candidates(candidates)

    # Format cuisine preference: list selected vibes, or "any" if none picked
    if prefs.cuisine:
        cuisines = [c.strip().title() for c in prefs.cuisine.split(",") if c.strip()]
        cuisine_display = ", ".join(cuisines) if cuisines else "Any"
        cuisine_note = (
            f"(match ANY of: {cuisine_display})"
            if len(cuisines) > 1
            else f"(preference: {cuisine_display})"
        )
    else:
        cuisine_display = "Any"
        cuisine_note = "(no preference — consider all cuisines)"

    user_prompt = (
        f"User Preferences:\n"
        f"- Location  : {prefs.location.title()}\n"
        f"- Budget    : {prefs.budget.title()}\n"
        f"- Cuisine   : {cuisine_display} {cuisine_note}\n"
        f"- Min Rating: {prefs.min_rating:.1f} / 5.0\n"
        f"- Additional: {prefs.extras if prefs.extras else 'None'}\n"
        f"\n"
        f"Candidate Restaurants:\n"
        f"{restaurant_list}\n"
        f"Please rank the top restaurants and provide a short, specific explanation for each. "
        f"When cuisine preference is specified, prioritise restaurants matching those vibes "
        f"and mention the cuisine match in the explanation."
    )

    return SYSTEM_PROMPT, user_prompt


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _format_candidates(candidates: pd.DataFrame) -> str:
    """
    Format each candidate row as a compact single-line string for the prompt.

    Example output:
        1. Truffles | Cuisine: american | Rating: 4.6 | Cost: ₹800 | Tags: Casual Dining
    """
    lines: list[str] = []
    for i, (_, row) in enumerate(candidates.iterrows(), start=1):
        cost = int(row["avg_cost_for_two"]) if pd.notna(row.get("avg_cost_for_two")) else "N/A"
        cost_str = f"₹{cost}" if isinstance(cost, int) else cost
        tags = row.get("features", "N/A") or "N/A"

        lines.append(
            f"{i}. {row['name']} | "
            f"Cuisine: {row['cuisine']} | "
            f"Rating: {row['rating']:.1f} | "
            f"Cost for two: {cost_str} | "
            f"Tags: {tags}"
        )

    return "\n".join(lines)
