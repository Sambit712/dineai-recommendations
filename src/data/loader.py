"""
src/data/loader.py
Phase 2 — Data Ingestion

Responsibilities:
  - Fetch the Zomato dataset from Hugging Face (first run)
  - Serve from local pickle cache on subsequent runs (EC-D08)
  - Handle network failures gracefully (EC-D01)
  - Validate dataset is non-empty after load (EC-D03)
"""

import os
import pickle
import sys

import pandas as pd
from datasets import load_dataset
from rich.console import Console

from config.settings import HF_DATASET_NAME, PROCESSED_DATA_PATH

console = Console(stderr=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_or_fetch() -> pd.DataFrame:
    """
    Return the raw (unprocessed) Zomato DataFrame.

    Load order:
      1. Valid pickle cache  → fast path, no network needed
      2. Hugging Face API    → downloaded and returned as raw DataFrame
                               (preprocessing + caching handled by preprocessor)
    """
    if os.path.exists(PROCESSED_DATA_PATH):
        df = _load_cache()
        if df is not None:
            console.print(
                f"[dim]Loaded dataset from cache: {PROCESSED_DATA_PATH}[/dim]"
            )
            return df
        # Cache was corrupt — fall through to re-fetch

    return _fetch_from_huggingface()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_cache() -> pd.DataFrame | None:
    """
    Load the preprocessed DataFrame from disk.
    Returns None if the file is corrupt or has an unexpected schema (EC-D08).
    """
    try:
        df = pd.read_pickle(PROCESSED_DATA_PATH)
        if not isinstance(df, pd.DataFrame) or df.empty:
            console.print(
                "[yellow]Warning:[/yellow] Cache file is invalid or empty. "
                "Re-fetching from Hugging Face..."
            )
            _delete_cache()
            return None
        return df
    except (pickle.UnpicklingError, EOFError, Exception) as exc:
        console.print(
            f"[yellow]Warning:[/yellow] Cache file is corrupt ({exc}). "
            "Re-fetching from Hugging Face..."
        )
        _delete_cache()
        return None


def _fetch_from_huggingface() -> pd.DataFrame:
    """
    Download the Zomato dataset from Hugging Face and return as a DataFrame.
    Handles network failures (EC-D01) and empty datasets (EC-D03).
    """
    console.print(
        "\n[bold cyan]Downloading dataset for the first time...[/bold cyan] "
        "(this may take a moment)\n"
    )

    try:
        dataset = load_dataset(HF_DATASET_NAME, split="train")
    except Exception as exc:
        # Covers ConnectionError, requests.Timeout, HF API errors, etc.
        _abort(
            f"Failed to download dataset from Hugging Face.\n"
            f"  Reason : {exc}\n"
            f"  Dataset: {HF_DATASET_NAME}\n\n"
            "Please check your internet connection and try again.\n"
            "If this is a recurring issue, check https://huggingface.co for outages."
        )

    df = dataset.to_pandas()  # type: ignore[union-attr]

    # EC-D03 — empty dataset guard
    if df.empty:
        _abort(
            "The downloaded dataset contains 0 rows.\n"
            "This may be a temporary Hugging Face issue. Please try again later."
        )

    console.print(
        f"[green]Dataset downloaded successfully.[/green] "
        f"({len(df):,} rows, {len(df.columns)} columns)\n"
    )
    return df


def _delete_cache() -> None:
    """Safely remove a corrupt or stale cache file."""
    try:
        os.remove(PROCESSED_DATA_PATH)
    except OSError:
        pass


def _abort(message: str) -> None:
    """Print a fatal error and exit."""
    console.print(f"\n[bold red][ERROR][/bold red] {message}\n")
    sys.exit(1)
