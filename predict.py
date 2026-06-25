"""
predict.py — Standalone Restaurant Recommendation Script
Phases 4 + 5 + 6: Filter → Prompt → LLM → Display

Usage:
    python predict.py --location bellandur --rating 4.2 --budget 1500
"""

import sys
import io
import re
import json
import argparse

# ── UTF-8 stdout (prevents Windows cp1252 crash) ──────────────────────────────
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import requests
import pandas as pd
from dotenv import load_dotenv
from datasets import load_dataset

load_dotenv()

import os
GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
LLM_MODEL       = os.getenv("LLM_MODEL", "llama3-70b-8192")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS  = int(os.getenv("LLM_MAX_TOKENS", "1024"))
FILTER_TOP_N    = int(os.getenv("FILTER_TOP_N", "10"))
OUTPUT_TOP_K    = int(os.getenv("OUTPUT_TOP_K", "5"))
PROCESSED_DATA_PATH = "data/zomato_processed.pkl"

BUDGET_THRESHOLDS = {
    "low":    (0,    500),
    "medium": (501,  1500),
    "high":   (1501, float("inf")),
}

COLUMN_ALIASES = {
    "name":             ["name", "restaurant_name", "Restaurant Name"],
    "location":         ["location", "city", "City"],
    "cuisine":          ["cuisines", "cuisine", "Cuisines"],
    "avg_cost_for_two": ["approx_cost(for two people)", "cost", "avg_cost", "Cost"],
    "rating":           ["aggregate_rating", "rating", "Rating", "rate"],
    "votes":            ["votes", "Votes"],
    "features":         ["listed_in(type)", "features", "type", "Tags"],
}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Data loading & preprocessing
# ─────────────────────────────────────────────────────────────────────────────

def load_data() -> pd.DataFrame:
    if os.path.exists(PROCESSED_DATA_PATH):
        df = pd.read_pickle(PROCESSED_DATA_PATH)
        if isinstance(df, pd.DataFrame) and not df.empty:
            print(f"[Cache] Loaded {len(df):,} restaurants from local cache.")
            return df

    print("[Download] Fetching dataset from HuggingFace (this may take a moment)...")
    dataset = load_dataset("ManikaSaini/zomato-restaurant-recommendation", split="train")
    df = dataset.to_pandas()
    df = preprocess(df)
    return df


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    # Resolve column aliases
    rename_map = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        matched = next((a for a in aliases if a in df.columns), None)
        if matched and matched != canonical:
            rename_map[matched] = canonical
    if rename_map:
        df = df.rename(columns=rename_map)

    if "features" not in df.columns:
        df["features"] = "N/A"
    if "votes" not in df.columns:
        df["votes"] = 0

    # Normalize
    df["location"] = df["location"].astype(str).str.strip().str.lower()
    df["cuisine"]  = df["cuisine"].astype(str).str.strip().str.lower().replace("nan", "unknown")

    # Rating: handle "3.5/5", "NEW", "-"
    df["rating"] = df["rating"].astype(str).str.extract(r"(\d+\.?\d*)", expand=False)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["rating"] = df["rating"].fillna(df["rating"].median()).clip(0.0, 5.0)

    # Cost
    df["avg_cost_for_two"] = (
        df["avg_cost_for_two"].astype(str).str.replace(",", "", regex=False)
    )
    df["avg_cost_for_two"] = pd.to_numeric(df["avg_cost_for_two"], errors="coerce").fillna(500.0).clip(50, 10_000)

    # Budget category
    def _bucket(cost):
        for cat, (lo, hi) in BUDGET_THRESHOLDS.items():
            if lo <= cost <= hi:
                return cat
        return "high"
    df["budget_category"] = df["avg_cost_for_two"].apply(_bucket)

    # Votes
    df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int).clip(lower=0)

    # Dedup
    df["_n"] = df["name"].str.strip().str.lower()
    df["_l"] = df["location"].str.strip().str.lower()
    df = df.sort_values("votes", ascending=False).drop_duplicates(subset=["_n","_l"], keep="first")
    df = df.drop(columns=["_n","_l"]).reset_index(drop=True)

    # Persist
    os.makedirs(os.path.dirname(PROCESSED_DATA_PATH) or ".", exist_ok=True)
    df.to_pickle(PROCESSED_DATA_PATH)
    print(f"[Preprocessed] {len(df):,} restaurants ready. Cache saved.")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 2. Filter engine
# ─────────────────────────────────────────────────────────────────────────────

def budget_category(amount: float) -> str:
    for cat, (lo, hi) in BUDGET_THRESHOLDS.items():
        if lo <= amount <= hi:
            return cat
    return "high"


def filter_restaurants(df: pd.DataFrame, location: str, min_rating: float, budget_cat: str) -> pd.DataFrame:
    loc_pattern = re.escape(location.lower())
    result = df[df["location"].str.contains(loc_pattern, case=False, na=False)]

    # Level 0: strict — location + budget + rating
    strict = result[
        (result["budget_category"] == budget_cat) &
        (result["rating"] >= min_rating)
    ]
    if len(strict) >= 3:
        print(f"[Filter] {len(strict)} restaurants matched (strict). Sending top {FILTER_TOP_N} to LLM.")
        return strict.sort_values(["rating","votes","avg_cost_for_two"], ascending=[False,False,True]).head(FILTER_TOP_N).reset_index(drop=True)

    # Level 1: drop budget
    relaxed = result[result["rating"] >= min_rating]
    if len(relaxed) >= 3:
        print(f"[Filter] Budget relaxed. {len(relaxed)} restaurants matched.")
        return relaxed.sort_values(["rating","votes","avg_cost_for_two"], ascending=[False,False,True]).head(FILTER_TOP_N).reset_index(drop=True)

    # Level 2: drop rating too
    print(f"[Filter] Rating also relaxed (found only {len(relaxed)}). Showing all in location.")
    return result.sort_values(["rating","votes","avg_cost_for_two"], ascending=[False,False,True]).head(FILTER_TOP_N).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Prompt builder
# ─────────────────────────────────────────────────────────────────────────────

def build_prompt(candidates: pd.DataFrame, location: str, min_rating: float, budget: int) -> str:
    rows = []
    for i, row in candidates.iterrows():
        rows.append(
            f"{i+1}. {row['name']} | Location: {row['location'].title()} | "
            f"Cuisine: {row['cuisine'].title()} | Rating: {row['rating']:.1f}/5 | "
            f"Cost for two: ₹{int(row['avg_cost_for_two'])} | "
            f"Votes: {row['votes']}"
        )

    restaurant_list = "\n".join(rows)

    return f"""You are an expert restaurant recommendation assistant for Zomato (Bangalore, India).

A user is looking for restaurants with these preferences:
- Location: {location.title()}
- Minimum Rating: {min_rating}/5
- Budget (for two people): ₹{budget}

Here are the top candidate restaurants found in the dataset:

{restaurant_list}

Based on the above data, recommend the TOP 5 restaurants that best match the user's preferences.

Respond ONLY in this exact JSON format (no extra text, no markdown code fences):
{{
  "recommendations": [
    {{
      "rank": 1,
      "name": "Restaurant Name",
      "cuisine": "Cuisine Type",
      "rating": 4.5,
      "cost_for_two": "₹800",
      "why": "Brief reason why this restaurant fits the user's needs"
    }}
  ]
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
# 4. LLM call
# ─────────────────────────────────────────────────────────────────────────────

def local_rank(candidates: pd.DataFrame, budget: int) -> dict:
    """Fallback: score & rank locally when LLM API is unreachable."""
    print("[Fallback] LLM unreachable — using local scoring (rating × votes).")
    top = candidates.head(OUTPUT_TOP_K).copy()
    recs = []
    for rank, (_, row) in enumerate(top.iterrows(), start=1):
        cost_diff = abs(row["avg_cost_for_two"] - budget)
        why = (
            f"Rating {row['rating']:.1f}/5 with {row['votes']:,} votes. "
            f"Cost ₹{int(row['avg_cost_for_two'])} for two is "
            f"{'within' if row['avg_cost_for_two'] <= budget else 'slightly above'} your budget."
        )
        recs.append({
            "rank": rank,
            "name": row["name"],
            "cuisine": row["cuisine"].title(),
            "rating": round(row["rating"], 1),
            "cost_for_two": f"₹{int(row['avg_cost_for_two'])}",
            "why": why,
            "source": "local-scoring",
        })
    return {"recommendations": recs}


def call_llm(prompt: str) -> dict | None:
    """
    Call Groq LLM API. Returns parsed JSON dict, or None if unreachable.
    """
    print(f"[LLM] Calling {LLM_MODEL} via Groq API...")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
    }

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
    except Exception as exc:
        print(f"[LLM] API unavailable ({exc}). Falling back to local scoring.")
        return None

    raw = resp.json()["choices"][0]["message"]["content"].strip()

    # Strip markdown code fences if LLM adds them anyway
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print("[LLM] JSON parse error. Falling back to local scoring.")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 5. Display
# ─────────────────────────────────────────────────────────────────────────────

def display_results(data: dict, location: str, min_rating: float, budget: int):
    recs = data.get("recommendations", [])
    print()
    print("=" * 65)
    print(f"  TOP {len(recs)} RESTAURANT RECOMMENDATIONS")
    print(f"  Location: {location.title()}  |  Min Rating: {min_rating}  |  Budget: ₹{budget}")
    print("=" * 65)
    for rec in recs:
        print()
        print(f"  #{rec['rank']}  {rec['name']}")
        print(f"       Cuisine : {rec['cuisine']}")
        print(f"       Rating  : {rec['rating']}/5")
        print(f"       Cost    : {rec['cost_for_two']} for two")
        print(f"       Why     : {rec['why']}")
        print("  " + "-" * 63)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# 6. Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI Restaurant Recommender")
    parser.add_argument("--location", default="bellandur")
    parser.add_argument("--rating",   type=float, default=4.2)
    parser.add_argument("--budget",   type=int,   default=1500)
    args = parser.parse_args()

    location   = args.location.strip().lower()
    min_rating = args.rating
    budget     = args.budget
    budget_cat = budget_category(budget)

    print()
    print(f"  Preferences  ->  Location: {location.title()}  |  Min Rating: {min_rating}  |  Budget: ₹{budget} ({budget_cat})")
    print()

    # Step 1: Load data
    df = load_data()

    # Step 2: Filter
    candidates = filter_restaurants(df, location, min_rating, budget_cat)

    if candidates.empty:
        print(f"[!] No restaurants found in '{location.title()}'. Try a different location.")
        sys.exit(1)

    print(f"[Candidates] Sending {len(candidates)} restaurants to LLM for ranking...")

    # Step 3: Build prompt
    prompt = build_prompt(candidates, location, min_rating, budget)

    # Step 4: Call LLM (with local fallback)
    result = call_llm(prompt)
    if result is None:
        result = local_rank(candidates, budget)

    # Step 5: Display
    source = "LLM" if result.get("recommendations", [{}])[0].get("source") != "local-scoring" else "Local Scoring (LLM unreachable)"
    print(f"[Source] Rankings generated by: {source}")
    display_results(result, location, min_rating, budget)


if __name__ == "__main__":
    main()
