"""
data/validate.py
Phase 2 — Preprocessing Sanity Check

Run this script directly after Phase 2 to verify the processed dataset:
  python data/validate.py

Checks:
  - DataFrame shape and dtypes
  - Null counts in all columns
  - Unique locations (top 20)
  - Unique cuisine types (top 20)
  - Budget category distribution
  - Rating distribution summary
  - Cost distribution summary

Note: This script does NOT require a GROQ_API_KEY — it only exercises
Phase 2 (data ingestion & preprocessing).
"""

import sys
import os

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env manually (without triggering the GROQ_API_KEY guard in settings.py)
from dotenv import load_dotenv
load_dotenv()  # populates os.environ from .env if it exists

import pandas as pd
from rich.console import Console
from rich.table import Table
from rich import box

# Import only data-related settings (does NOT trigger the GROQ_API_KEY guard)
from config.settings import HF_DATASET_NAME, PROCESSED_DATA_PATH  # noqa: F401

from src.data.loader import load_or_fetch
from src.data.preprocessor import preprocess

console = Console()


def validate() -> None:
    console.rule("[bold yellow]Phase 2 — Dataset Validation Report[/bold yellow]")

    # Load + preprocess
    raw_df = load_or_fetch()
    df = preprocess(raw_df)

    # ── 1. Shape & dtypes ────────────────────────────────────────────────────
    console.print(f"\n[bold]Shape:[/bold] {df.shape[0]:,} rows × {df.shape[1]} columns")

    dtype_table = Table("Column", "Dtype", "Nulls", box=box.SIMPLE)
    for col in df.columns:
        nulls = int(df[col].isna().sum())
        dtype_table.add_row(col, str(df[col].dtype), str(nulls))
    console.print("\n[bold]Column Info:[/bold]")
    console.print(dtype_table)

    # ── 2. Null counts summary ───────────────────────────────────────────────
    total_nulls = df.isna().sum().sum()
    if total_nulls == 0:
        console.print("[green]No nulls found in any column.[/green]")
    else:
        console.print(f"[yellow]Total nulls remaining: {total_nulls}[/yellow]")

    # ── 3. Unique locations ──────────────────────────────────────────────────
    locations = df["location"].value_counts().head(20)
    loc_table = Table("Location", "Count", box=box.SIMPLE)
    for loc, cnt in locations.items():
        loc_table.add_row(str(loc), str(cnt))
    console.print(f"\n[bold]Top Locations (of {df['location'].nunique()} unique):[/bold]")
    console.print(loc_table)

    # ── 4. Unique cuisines ───────────────────────────────────────────────────
    cuisines = df["cuisine"].value_counts().head(20)
    cui_table = Table("Cuisine", "Count", box=box.SIMPLE)
    for cui, cnt in cuisines.items():
        cui_table.add_row(str(cui), str(cnt))
    console.print(f"\n[bold]Top Cuisines (of {df['cuisine'].nunique()} unique):[/bold]")
    console.print(cui_table)

    # ── 5. Budget distribution ───────────────────────────────────────────────
    budget_dist = df["budget_category"].value_counts()
    bud_table = Table("Budget", "Count", "Pct", box=box.SIMPLE)
    for bud, cnt in budget_dist.items():
        pct = cnt / len(df) * 100
        bud_table.add_row(str(bud), str(cnt), f"{pct:.1f}%")
    console.print("\n[bold]Budget Distribution:[/bold]")
    console.print(bud_table)

    # ── 6. Rating distribution ───────────────────────────────────────────────
    r = df["rating"]
    console.print(
        f"\n[bold]Rating:[/bold]  "
        f"min={r.min():.2f}  max={r.max():.2f}  "
        f"mean={r.mean():.2f}  median={r.median():.2f}"
    )

    # ── 7. Cost distribution ─────────────────────────────────────────────────
    c = df["avg_cost_for_two"]
    console.print(
        f"[bold]Cost (₹):[/bold] "
        f"min={c.min():.0f}  max={c.max():.0f}  "
        f"mean={c.mean():.0f}  median={c.median():.0f}"
    )

    console.rule("[bold green]Validation Complete[/bold green]")


if __name__ == "__main__":
    validate()
