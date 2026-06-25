import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ── Groq LLM ─────────────────────────────────────────────────
GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
LLM_MODEL       = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS  = int(os.getenv("LLM_MAX_TOKENS", "1024"))

# ── Dataset ───────────────────────────────────────────────────
HF_DATASET_NAME     = "ManikaSaini/zomato-restaurant-recommendation"
PROCESSED_DATA_PATH = "data/zomato_processed.pkl"

# Column alias map — handles different HuggingFace dataset versions (EC-S07)
# Maps canonical name -> list of possible source column names (tried left to right)
COLUMN_ALIASES = {
    "name":             ["name", "restaurant_name", "Restaurant Name"],
    "location":         ["location", "city", "City"],
    "cuisine":          ["cuisines", "cuisine", "Cuisines"],
    "avg_cost_for_two": ["approx_cost(for two people)", "cost", "avg_cost", "Cost"],
    "rating":           ["aggregate_rating", "rating", "Rating", "rate"],
    "votes":            ["votes", "Votes"],
    "features":         ["listed_in(type)", "features", "type", "Tags"],
}

# Budget thresholds (Rs per two people)
BUDGET_THRESHOLDS = {
    "low":    (0,    500),
    "medium": (501,  1500),
    "high":   (1501, float("inf")),
}

# ── Pipeline ──────────────────────────────────────────────────
FILTER_TOP_N = int(os.getenv("FILTER_TOP_N", "10"))   # candidates sent to LLM
OUTPUT_TOP_K = int(os.getenv("OUTPUT_TOP_K", "5"))    # final results shown


# ── Startup Validators (called explicitly by main.py) ─────────
def validate_api_key() -> None:
    """
    Fail fast if GROQ_API_KEY is missing (EC-S03).
    Called explicitly in main.py -- NOT at import time -- so data-only
    scripts (e.g. data/validate.py) can import settings without exiting.
    """
    if not GROQ_API_KEY:
        print(
            "\n[ERROR] GROQ_API_KEY is not set.\n"
            "  1. Copy .env.example to .env\n"
            "  2. Add your Groq API key from https://console.groq.com/keys\n"
            "  Then run the app again.\n"
        )
        sys.exit(1)


def validate_python_version() -> None:
    """Enforce Python 3.10+ (EC-S06)."""
    if sys.version_info < (3, 10):
        print(
            f"[ERROR] Python 3.10+ required. You are running {sys.version}.\n"
            "Please upgrade your Python installation."
        )
        sys.exit(1)
