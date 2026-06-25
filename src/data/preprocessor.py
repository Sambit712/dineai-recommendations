"""
src/data/preprocessor.py
Phase 2 — Data Preprocessing

Preprocessing pipeline (in order):
  Step 1  Resolve column aliases          (EC-S07 — schema changes across dataset versions)
  Step 2  Drop nulls in required columns  (EC-D04)
  Step 3  Drop duplicates                 (EC-D07)
  Step 4  Normalize location              (lowercase + strip)
  Step 5  Normalize cuisine               (lowercase + strip)
  Step 6  Cast & clean rating             (EC-D05 — "NEW", "-", "3.5/5", etc.)
  Step 7  Clean & clip avg cost           (EC-D06 — negatives, zeros, extreme outliers)
  Step 8  Categorize budget               (low / medium / high)
  Step 9  Normalize votes
  Step 10 Persist cache atomically        (EC-S02 — safe on Ctrl+C; EC-S04 — disk full)
"""

import os
import sys
import tempfile
import logging

import pandas as pd
from rich.console import Console

from config.settings import (
    COLUMN_ALIASES,
    BUDGET_THRESHOLDS,
    PROCESSED_DATA_PATH,
)

console = Console(stderr=True)
logger = logging.getLogger(__name__)

# Required columns (canonical names) that MUST be present after alias resolution
REQUIRED_COLUMNS = ["name", "location", "rating"]

# Cost clipping range (₹) — EC-D06
COST_MIN = 50.0
COST_MAX = 10_000.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run the full preprocessing pipeline on a raw Zomato DataFrame.
    Returns a clean, normalized DataFrame and persists it to disk.
    """
    original_count = len(df)
    console.print("[bold cyan]Preprocessing dataset...[/bold cyan]")

    df = _resolve_columns(df)
    df = _drop_nulls(df, original_count)
    df = _drop_duplicates(df)
    df = _normalize_location(df)
    df = _normalize_cuisine(df)
    df = _clean_rating(df)
    df = _clean_cost(df)
    df = _categorize_budget(df)
    df = _normalize_votes(df)
    df = df.reset_index(drop=True)

    console.print(
        f"[green]Preprocessing complete.[/green] "
        f"{len(df):,} restaurants ready "
        f"(dropped {original_count - len(df):,} rows).\n"
    )

    _save_cache(df)
    return df


# ---------------------------------------------------------------------------
# Step 1 — Resolve column aliases
# ---------------------------------------------------------------------------

def _resolve_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename raw dataset columns to canonical names using COLUMN_ALIASES.
    Raises a descriptive error if a required canonical column cannot be found (EC-D02, EC-S07).
    """
    rename_map: dict[str, str] = {}
    missing_required: list[str] = []

    for canonical, aliases in COLUMN_ALIASES.items():
        matched = next((a for a in aliases if a in df.columns), None)
        if matched and matched != canonical:
            rename_map[matched] = canonical
        elif matched is None:
            if canonical in REQUIRED_COLUMNS:
                missing_required.append(canonical)
            # Optional columns (e.g. features) are allowed to be absent

    if rename_map:
        df = df.rename(columns=rename_map)
        logger.debug("Renamed columns: %s", rename_map)

    if missing_required:
        _abort(
            "Dataset is missing required columns after alias resolution.\n"
            f"  Missing : {missing_required}\n"
            f"  Available columns: {list(df.columns)}\n\n"
            "The dataset schema may have changed. "
            "Update COLUMN_ALIASES in config/settings.py."
        )

    # Add optional columns with defaults if completely absent
    if "features" not in df.columns:
        df["features"] = "N/A"
    if "votes" not in df.columns:
        df["votes"] = 0

    return df


# ---------------------------------------------------------------------------
# Step 2 — Drop nulls in required columns
# ---------------------------------------------------------------------------

def _drop_nulls(df: pd.DataFrame, original_count: int) -> pd.DataFrame:
    """Drop rows where any required column is null (EC-D04)."""
    before = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS)
    dropped = before - len(df)

    if dropped:
        console.print(
            f"  [dim]Dropped {dropped:,} rows with missing required fields.[/dim]"
        )

    # EC-D04 — if ALL rows were dropped, abort with a clear message
    if df.empty:
        _abort(
            f"All {original_count:,} rows were dropped during null-cleaning.\n"
            "The dataset appears to be entirely corrupt or incompatible.\n"
            "Try deleting the cache and re-running to fetch a fresh copy."
        )

    return df


# ---------------------------------------------------------------------------
# Step 3 — Drop duplicates
# ---------------------------------------------------------------------------

def _drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate restaurants by (normalized name, location).
    Keeps the entry with the highest votes (EC-D07).
    """
    # Temporary normalized keys for deduplication
    df["_name_norm"] = df["name"].str.strip().str.lower()
    df["_loc_norm"]  = df["location"].str.strip().str.lower()

    # Ensure votes is numeric before sorting for dedup
    df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)

    before = len(df)
    df = (
        df.sort_values("votes", ascending=False)
          .drop_duplicates(subset=["_name_norm", "_loc_norm"], keep="first")
    )
    dropped = before - len(df)

    if dropped:
        console.print(
            f"  [dim]Removed {dropped:,} duplicate restaurant entries.[/dim]"
        )

    df = df.drop(columns=["_name_norm", "_loc_norm"])
    return df


# ---------------------------------------------------------------------------
# Step 4 — Normalize location
# ---------------------------------------------------------------------------

def _normalize_location(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace and lowercase the location column."""
    df["location"] = df["location"].astype(str).str.strip().str.lower()
    return df


# ---------------------------------------------------------------------------
# Step 5 — Normalize cuisine
# ---------------------------------------------------------------------------

def _normalize_cuisine(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace and lowercase the cuisine column."""
    df["cuisine"] = df["cuisine"].astype(str).str.strip().str.lower()
    # Replace literal "nan" strings that arise from astype(str) on NaN cells
    df["cuisine"] = df["cuisine"].replace("nan", "unknown")
    return df


# ---------------------------------------------------------------------------
# Step 6 — Cast & clean rating
# ---------------------------------------------------------------------------

def _clean_rating(df: pd.DataFrame) -> pd.DataFrame:
    """
    Robustly parse ratings that may be strings like "NEW", "-", "3.5/5" (EC-D05).
    Fills unparseable values with the column median.
    """
    # Handle "3.5/5" style — extract numerator
    df["rating"] = (
        df["rating"]
        .astype(str)
        .str.extract(r"(\d+\.?\d*)", expand=False)
    )
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

    n_bad = df["rating"].isna().sum()
    if n_bad:
        median_rating = df["rating"].median()
        df["rating"] = df["rating"].fillna(median_rating)
        console.print(
            f"  [dim]Filled {n_bad:,} unparseable rating values with median "
            f"({median_rating:.2f}).[/dim]"
        )

    # Clip to valid Zomato range
    df["rating"] = df["rating"].clip(lower=0.0, upper=5.0)
    return df


# ---------------------------------------------------------------------------
# Step 7 — Clean & clip average cost
# ---------------------------------------------------------------------------

def _clean_cost(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse cost column; clip extreme outliers to [COST_MIN, COST_MAX] (EC-D06).
    Also removes commas from values like "1,200".
    """
    if "avg_cost_for_two" not in df.columns:
        df["avg_cost_for_two"] = 500.0   # sensible default if column absent
        return df

    df["avg_cost_for_two"] = (
        df["avg_cost_for_two"]
        .astype(str)
        .str.replace(",", "", regex=False)   # "1,200" → "1200"
    )
    df["avg_cost_for_two"] = pd.to_numeric(df["avg_cost_for_two"], errors="coerce")

    n_bad = df["avg_cost_for_two"].isna().sum()
    if n_bad:
        df["avg_cost_for_two"] = df["avg_cost_for_two"].fillna(500.0)
        console.print(
            f"  [dim]Filled {n_bad:,} unparseable cost values with ₹500.[/dim]"
        )

    # Clip outliers
    n_outliers = (
        (df["avg_cost_for_two"] < COST_MIN) | (df["avg_cost_for_two"] > COST_MAX)
    ).sum()
    if n_outliers:
        df["avg_cost_for_two"] = df["avg_cost_for_two"].clip(
            lower=COST_MIN, upper=COST_MAX
        )
        console.print(
            f"  [dim]Clipped {n_outliers:,} cost outliers to "
            f"[{COST_MIN:.0f}, {COST_MAX:.0f}].[/dim]"
        )

    return df


# ---------------------------------------------------------------------------
# Step 8 — Categorize budget
# ---------------------------------------------------------------------------

def _categorize_budget(df: pd.DataFrame) -> pd.DataFrame:
    """Map avg_cost_for_two → budget_category using BUDGET_THRESHOLDS."""

    def _bucket(cost: float) -> str:
        for category, (lo, hi) in BUDGET_THRESHOLDS.items():
            if lo <= cost <= hi:
                return category
        return "high"   # fallback for any cost above all thresholds

    df["budget_category"] = df["avg_cost_for_two"].apply(_bucket)
    return df


# ---------------------------------------------------------------------------
# Step 9 — Normalize votes
# ---------------------------------------------------------------------------

def _normalize_votes(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure votes is a non-negative integer; fill missing with 0."""
    df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)
    df["votes"] = df["votes"].clip(lower=0)
    return df


# ---------------------------------------------------------------------------
# Step 10 — Persist cache atomically
# ---------------------------------------------------------------------------

def _save_cache(df: pd.DataFrame) -> None:
    """
    Write the processed DataFrame to disk atomically using a temp file +
    os.replace() to prevent corrupt cache on Ctrl+C (EC-S02) or disk-full
    errors (EC-S04).
    """
    cache_dir = os.path.dirname(PROCESSED_DATA_PATH)
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)

    try:
        # Write to a temp file in the same directory so os.replace() is atomic
        with tempfile.NamedTemporaryFile(
            dir=cache_dir or ".", suffix=".pkl.tmp", delete=False
        ) as tmp:
            tmp_path = tmp.name

        df.to_pickle(tmp_path)
        os.replace(tmp_path, PROCESSED_DATA_PATH)
        console.print(
            f"[dim]Dataset cached to: {PROCESSED_DATA_PATH}[/dim]\n"
        )
    except OSError as exc:
        # EC-S04 — disk full or permission error; proceed without caching
        console.print(
            f"[yellow]Warning:[/yellow] Could not write cache ({exc}). "
            "The dataset will be re-fetched on next run."
        )
        # Clean up orphaned temp file if it exists
        try:
            os.remove(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _abort(message: str) -> None:
    console.print(f"\n[bold red][ERROR][/bold red] {message}\n")
    sys.exit(1)
