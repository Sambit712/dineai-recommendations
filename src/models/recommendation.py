from dataclasses import dataclass


@dataclass
class Recommendation:
    """A single restaurant recommendation produced by the LLM pipeline."""

    rank: int               # 1-indexed ranking from LLM
    name: str               # Restaurant name
    cuisine: str            # Cuisine type(s)
    rating: float           # Average rating (0.0 – 5.0)
    estimated_cost: str     # Human-readable cost string, e.g., "₹800 for two"
    explanation: str        # LLM-generated explanation of why this fits the user
