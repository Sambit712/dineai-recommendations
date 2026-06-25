"""
src/input/handler.py
Phase 3 -- User Input Handler

Responsibilities:
  - Collect all 5 user preference fields interactively
  - Validate and re-prompt on bad input
  - Normalize strings before returning

Edge cases handled:
  EC-I01  Empty input             -- re-prompt with clear message
  EC-I03  Invalid budget          -- case-insensitive; re-prompt with options
  EC-I04  Out-of-range rating     -- clamp check with re-prompt
  EC-I05  Rating = 5.0            -- warn user, proceed
  EC-I06  Special chars in input  -- strip non-alphanumeric (allow spaces/hyphens)
  EC-I07  Extremely long extras   -- truncate to MAX_EXTRAS_LEN with warning
  EC-I08  Non-ASCII input         -- detect and warn (proceed, filter will handle miss)
"""

import re

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box

from src.models.preferences import UserPreferences

console = Console()

# ── Constants ─────────────────────────────────────────────────────────────────
VALID_BUDGETS    = {"low", "medium", "high"}
MIN_CUISINE_LEN  = 2          # EC-F03 guard (minimum chars for cuisine)
MAX_EXTRAS_LEN   = 300        # EC-I07 -- truncate beyond this
RATING_MIN       = 0.0
RATING_MAX       = 5.0
RATING_WARN      = 4.8        # EC-I05 -- warn if rating is very high


# ── Public API ─────────────────────────────────────────────────────────────────

def collect_preferences() -> UserPreferences:
    """
    Interactively collect and validate all 5 user preference fields.
    Returns a clean, normalized UserPreferences dataclass instance.
    """
    _print_header()

    location   = _prompt_location()
    budget     = _prompt_budget()
    cuisine    = _prompt_cuisine()
    min_rating = _prompt_rating()
    extras     = _prompt_extras()

    prefs = UserPreferences(
        location=location,
        budget=budget,
        cuisine=cuisine,
        min_rating=min_rating,
        extras=extras,
    )

    _print_summary(prefs)
    return prefs


# ── Header ─────────────────────────────────────────────────────────────────────

def _print_header() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]AI-Powered Restaurant Recommendation System[/bold cyan]\n"
            "[dim]Powered by Groq x Zomato Dataset[/dim]",
            box=box.DOUBLE_EDGE,
            border_style="cyan",
        )
    )
    console.print(
        "\n[bold]Tell us your preferences[/bold] and we'll find the perfect restaurant for you.\n"
    )


# ── Field Collectors ───────────────────────────────────────────────────────────

def _prompt_location() -> str:
    """
    Collect and normalize city/location.
    EC-I01: re-prompt on empty
    EC-I06: strip special characters
    EC-I08: warn on non-ASCII
    """
    while True:
        raw = Prompt.ask("[bold]Location[/bold] [dim](e.g. Bangalore, Delhi)[/dim]")
        val = _sanitize(raw)

        # EC-I01 -- empty after sanitization
        if not val:
            console.print(
                "  [yellow]Location cannot be empty. Please enter a city name.[/yellow]"
            )
            continue

        # EC-I08 -- non-ASCII characters detected
        if not _is_ascii(val):
            console.print(
                "  [yellow]Please enter the city name in English "
                "(e.g. Bangalore, not \u092c\u0947\u0902\u0917\u0932\u0941\u0930\u0941).[/yellow]"
            )
            continue

        return val.lower()


def _prompt_budget() -> str:
    """
    Collect budget preference.
    EC-I01: re-prompt on empty
    EC-I03: case-insensitive; re-prompt if not in valid set
    """
    while True:
        raw = Prompt.ask(
            "[bold]Budget[/bold]",
            choices=["low", "medium", "high"],
            default="medium",
        )
        val = raw.strip().lower()

        if val in VALID_BUDGETS:
            return val

        # Shouldn't reach here due to rich choices, but guard anyway
        console.print(
            f"  [yellow]Invalid budget '{raw}'. "
            "Choose from: [bold]low[/bold], [bold]medium[/bold], [bold]high[/bold].[/yellow]"
        )


def _prompt_cuisine() -> str:
    """
    Collect cuisine preference.
    EC-I01: re-prompt on empty
    EC-I06: strip special characters
    """
    while True:
        raw = Prompt.ask(
            "[bold]Cuisine[/bold] [dim](e.g. Italian, North Indian, Chinese)[/dim]"
        )
        val = _sanitize(raw)

        # EC-I01 -- empty
        if not val:
            console.print(
                "  [yellow]Cuisine cannot be empty. "
                "Enter a cuisine type (e.g. Italian, Chinese).[/yellow]"
            )
            continue

        # EC-F03 guard -- too short, would match everything
        if len(val) < MIN_CUISINE_LEN:
            console.print(
                f"  [yellow]Please enter at least {MIN_CUISINE_LEN} characters "
                "for cuisine (e.g. 'Italian' not 'I').[/yellow]"
            )
            continue

        return val.lower()


def _prompt_rating() -> float:
    """
    Collect minimum rating.
    EC-I04: validate range [0.0, 5.0]; re-prompt on bad value or non-numeric
    EC-I05: warn if rating is very high (>= RATING_WARN) but proceed
    """
    while True:
        raw = Prompt.ask(
            f"[bold]Minimum rating[/bold] [dim]({RATING_MIN} – {RATING_MAX})[/dim]",
            default="3.5",
        )

        try:
            val = float(raw.strip())
        except ValueError:
            console.print(
                f"  [yellow]Please enter a number between "
                f"{RATING_MIN} and {RATING_MAX} (e.g. 4.0).[/yellow]"
            )
            continue

        # EC-I04 -- out of range
        if not (RATING_MIN <= val <= RATING_MAX):
            console.print(
                f"  [yellow]Rating must be between {RATING_MIN} and {RATING_MAX}. "
                f"You entered {val}.[/yellow]"
            )
            continue

        # EC-I05 -- very high rating warning
        if val >= RATING_WARN:
            console.print(
                f"  [yellow]Note:[/yellow] Very few restaurants have a rating >= {val}. "
                "Results may be limited. Consider trying 4.0 or 4.5 for more options."
            )

        return val


def _prompt_extras() -> str:
    """
    Collect optional additional preferences.
    EC-I07: truncate to MAX_EXTRAS_LEN with warning
    EC-I06: sanitize input (allow letters, numbers, spaces, hyphens, commas)
    EC-I08: warn on non-ASCII
    """
    raw = Prompt.ask(
        "[bold]Any additional preferences?[/bold] "
        "[dim](e.g. family-friendly, quick service, outdoor seating — optional)[/dim]",
        default="",
    )

    # Allow a broader character set for extras (commas, hyphens, spaces OK)
    val = _sanitize_extras(raw)

    # EC-I07 -- truncate if too long
    if len(val) > MAX_EXTRAS_LEN:
        console.print(
            f"  [yellow]Additional preferences truncated to {MAX_EXTRAS_LEN} characters.[/yellow]"
        )
        val = val[:MAX_EXTRAS_LEN].rstrip()

    return val


# ── Summary Display ────────────────────────────────────────────────────────────

def _print_summary(prefs: UserPreferences) -> None:
    """Print a confirmation of collected preferences before proceeding."""
    summary = (
        f"[bold]Location  :[/bold] {prefs.location.title()}\n"
        f"[bold]Budget    :[/bold] {prefs.budget.capitalize()}\n"
        f"[bold]Cuisine   :[/bold] {prefs.cuisine.title()}\n"
        f"[bold]Min Rating:[/bold] {prefs.min_rating} / 5.0\n"
        f"[bold]Extras    :[/bold] {prefs.extras if prefs.extras else '[dim]None[/dim]'}"
    )
    console.print(
        Panel(
            summary,
            title="[bold green]Your Preferences[/bold green]",
            border_style="green",
            box=box.ROUNDED,
        )
    )
    console.print()


# ── Sanitization Helpers ───────────────────────────────────────────────────────

def _sanitize(text: str) -> str:
    """
    Strip special characters from location/cuisine fields.
    Allows: letters, digits, spaces, hyphens.
    EC-I06 -- prevents regex errors in filter and prompt injection.
    """
    return re.sub(r"[^\w\s\-]", "", text, flags=re.UNICODE).strip()


def _sanitize_extras(text: str) -> str:
    """
    Lighter sanitization for the extras field.
    Allows: letters, digits, spaces, hyphens, commas, periods, apostrophes.
    Still strips characters that could cause LLM prompt injection (EC-P04).
    """
    return re.sub(r"[^\w\s\-,\.\']", "", text, flags=re.UNICODE).strip()


def _is_ascii(text: str) -> bool:
    """Return True if all characters in text are ASCII (EC-I08)."""
    try:
        text.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False
