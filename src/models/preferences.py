from dataclasses import dataclass


@dataclass
class UserPreferences:
    """Represents validated preferences collected from the user."""

    location: str       # e.g., "bangalore" — normalized to lowercase
    budget: str         # "low" | "medium" | "high"
    cuisine: str        # e.g., "italian" — normalized to lowercase
    min_rating: float   # 0.0 – 5.0
    extras: str         # free-text additional preferences (optional)
