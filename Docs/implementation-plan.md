# Implementation Plan: AI-Powered Restaurant Recommendation System

> Derived from [`Docs/context.md`](file:///c:/Users/kumar/Downloads/Project%20!/Docs/context.md) and [`Docs/architecture.md`](file:///c:/Users/kumar/Downloads/Project%20!/Docs/architecture.md)

---

## Overview

| Attribute | Detail |
|---|---|
| **Project** | AI-Powered Restaurant Recommendation System (Zomato Use Case) |
| **LLM Provider** | Groq API (`llama3-70b-8192`) |
| **Dataset** | [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) |
| **Total Phases** | 7 |
| **Backend Stack** | Python, FastAPI, Uvicorn, Groq SDK, HuggingFace `datasets`, Pandas |
| **Frontend Stack** | HTML5, Vanilla CSS (glassmorphism/dark mode), Vanilla JavaScript |

---

## Phase Summary

```
Phase 1 → Project Setup & Environment
Phase 2 → Data Ingestion & Preprocessing
Phase 3 → User Input Handler (optional/legacy CLI fallback)
Phase 4 → Filter Engine
Phase 5 → Prompt Builder + Groq LLM Integration
Phase 6 → Backend API (FastAPI)
Phase 7 → Frontend Web UI
```

---

## Phase 1: Project Setup & Environment

### Goal
Establish the project skeleton, dependency management, and configuration foundation before writing any feature code.

### Tasks

#### 1.1 — Initialize Project Structure
Create the following directory and file layout:

```
project/
│
├── data/                           # Cached preprocessed dataset
├── src/
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   └── preprocessor.py
│   ├── input/
│   │   ├── __init__.py
│   │   └── handler.py
│   ├── filter/
│   │   ├── __init__.py
│   │   └── engine.py
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── builder.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── parser.py
│   ├── output/
│   │   ├── __init__.py
│   │   └── renderer.py
│   └── models/
│       ├── __init__.py
│       ├── preferences.py
│       └── recommendation.py
├── config/
│   └── settings.py
├── main.py
├── .env                            # API keys (never commit)
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

#### 1.2 — Install Dependencies
Populate `requirements.txt`:

```
datasets==2.18.0
pandas==2.2.0
groq==0.5.0
python-dotenv==1.0.1
rich==13.7.0
```

Install via:
```bash
pip install -r requirements.txt
```

#### 1.3 — Configure Settings
Create `config/settings.py`:

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Groq LLM
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
LLM_MODEL      = os.getenv("LLM_MODEL", "llama3-70b-8192")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS  = int(os.getenv("LLM_MAX_TOKENS", "1024"))

# Dataset
HF_DATASET_NAME = "ManikaSaini/zomato-restaurant-recommendation"
PROCESSED_DATA_PATH = "data/zomato_processed.pkl"

# Pipeline
FILTER_TOP_N = int(os.getenv("FILTER_TOP_N", "10"))
OUTPUT_TOP_K = int(os.getenv("OUTPUT_TOP_K", "5"))
```

Create `.env.example`:
```
GROQ_API_KEY=your_groq_api_key_here
LLM_MODEL=llama3-70b-8192
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1024
FILTER_TOP_N=10
OUTPUT_TOP_K=5
```

#### 1.4 — Define Data Models
**`src/models/preferences.py`**:
```python
from dataclasses import dataclass

@dataclass
class UserPreferences:
    location: str        # e.g., "bangalore"
    budget: str          # "low" | "medium" | "high"
    cuisine: str         # e.g., "italian"
    min_rating: float    # e.g., 4.0
    extras: str          # e.g., "family-friendly, quick service"
```

**`src/models/recommendation.py`**:
```python
from dataclasses import dataclass

@dataclass
class Recommendation:
    rank: int
    name: str
    cuisine: str
    rating: float
    estimated_cost: str
    explanation: str     # LLM-generated
```

### Deliverables
- [ ] Full folder structure created
- [ ] All dependencies installed
- [ ] `settings.py` and `.env` configured
- [ ] Data model dataclasses defined

---

## Phase 2: Data Ingestion & Preprocessing

### Goal
Fetch the Zomato dataset from Hugging Face, clean and normalize it, and persist a ready-to-query DataFrame to disk.

### Tasks

#### 2.1 — Dataset Loader (`src/data/loader.py`)

```python
from datasets import load_dataset
import pandas as pd
from config.settings import HF_DATASET_NAME, PROCESSED_DATA_PATH
import os

def load_raw_dataset() -> pd.DataFrame:
    dataset = load_dataset(HF_DATASET_NAME, split="train")
    return dataset.to_pandas()

def load_or_fetch() -> pd.DataFrame:
    if os.path.exists(PROCESSED_DATA_PATH):
        return pd.read_pickle(PROCESSED_DATA_PATH)
    df = load_raw_dataset()
    return df
```

#### 2.2 — Data Preprocessor (`src/data/preprocessor.py`)

Preprocessing steps in order:

| Step | Operation | Detail |
|---|---|---|
| 1 | Drop nulls | Drop rows missing `name`, `location`, `rating` |
| 2 | Drop duplicates | Deduplicate on `name` + `location` |
| 3 | Normalize location | `.str.strip().str.lower()` |
| 4 | Normalize cuisine | `.str.strip().str.lower()` |
| 5 | Cast rating | `pd.to_numeric(errors='coerce')`, fill median |
| 6 | Budget categorization | Map `avg_cost_for_two` → `low / medium / high` |
| 7 | Normalize votes | `pd.to_numeric(errors='coerce')`, fill 0 |
| 8 | Persist cache | `df.to_pickle(PROCESSED_DATA_PATH)` |

**Budget thresholds** (example, adjust to dataset distribution):
```python
def categorize_budget(cost: float) -> str:
    if cost <= 500:   return "low"
    if cost <= 1500:  return "medium"
    return "high"
```

#### 2.3 — Validate Preprocessing
Write a quick sanity-check script (`data/validate.py`):
- Print shape, dtypes, null counts
- Print unique locations and cuisine types
- Print budget distribution

### Deliverables
- [ ] `loader.py` fetches dataset from Hugging Face
- [ ] `preprocessor.py` cleans and normalizes all fields
- [ ] Processed DataFrame cached to `data/zomato_processed.pkl`
- [ ] Validation confirms no nulls in key columns

---

## Phase 3: User Input Handler *(Optional — Legacy CLI Fallback)*

> ⚠ **Note:** With the introduction of Phase 7 (Frontend Web UI), user input is now collected via the web form and submitted to the backend API. This phase is retained as a **legacy CLI fallback** for testing the pipeline without the frontend.

### Goal
Collect, validate, and normalize user preferences into a `UserPreferences` object via the terminal.

### Tasks

#### 3.1 — Input Handler (`src/input/handler.py`)

```python
from src.models.preferences import UserPreferences

VALID_BUDGETS = {"low", "medium", "high"}

def collect_preferences() -> UserPreferences:
    print("\n🍽  Restaurant Recommendation System\n")
    location   = input("Enter location (e.g., Bangalore): ").strip().lower()
    budget     = _prompt_budget()
    cuisine    = input("Preferred cuisine (e.g., Italian): ").strip().lower()
    min_rating = _prompt_rating()
    extras     = input("Any extra preferences (e.g., family-friendly): ").strip()

    return UserPreferences(
        location=location,
        budget=budget,
        cuisine=cuisine,
        min_rating=min_rating,
        extras=extras
    )

def _prompt_budget() -> str:
    while True:
        b = input("Budget [low / medium / high]: ").strip().lower()
        if b in VALID_BUDGETS:
            return b
        print("  ⚠ Invalid. Choose from: low, medium, high")

def _prompt_rating() -> float:
    while True:
        try:
            r = float(input("Minimum rating (0.0 – 5.0): ").strip())
            if 0.0 <= r <= 5.0:
                return r
            print("  ⚠ Rating must be between 0.0 and 5.0")
        except ValueError:
            print("  ⚠ Please enter a numeric value")
```

#### 3.2 — Input Validation Rules

| Field | Validation Rule |
|---|---|
| `location` | Non-empty string |
| `budget` | Must be one of: `low`, `medium`, `high` |
| `cuisine` | Non-empty string (partial match allowed in filter) |
| `min_rating` | Float in range `[0.0, 5.0]` |
| `extras` | Optional, free text |

### Deliverables
- [ ] `handler.py` collects all 5 preference fields
- [ ] Budget and rating validated with re-prompt on invalid input
- [ ] Returns a clean `UserPreferences` dataclass instance
- [ ] *(Primary input path handled by Phase 7 frontend form)*

---

## Phase 4: Filter Engine

### Goal
Query the preprocessed DataFrame using `UserPreferences` and return the top-N restaurant candidates.

### Tasks

#### 4.1 — Filter Engine (`src/filter/engine.py`)

```python
import pandas as pd
from src.models.preferences import UserPreferences
from config.settings import FILTER_TOP_N

def filter_restaurants(df: pd.DataFrame, prefs: UserPreferences) -> pd.DataFrame:
    result = df.copy()

    # Location filter (partial match for flexibility)
    result = result[result["location"].str.contains(prefs.location, na=False)]

    # Budget filter
    result = result[result["budget_category"] == prefs.budget]

    # Cuisine filter (partial match)
    result = result[result["cuisine"].str.contains(prefs.cuisine, na=False)]

    # Minimum rating filter
    result = result[result["rating"] >= prefs.min_rating]

    # Rank by rating DESC, then votes DESC
    result = result.sort_values(
        by=["rating", "votes"],
        ascending=[False, False]
    )

    return result.head(FILTER_TOP_N)
```

#### 4.2 — Fallback Strategy
If fewer than 3 results are returned, apply a progressive relaxation:

| Fallback Level | Relaxation Applied |
|---|---|
| Level 1 | Remove cuisine filter |
| Level 2 | Also remove budget filter |
| Level 3 | Also lower `min_rating` by 0.5 |

```python
def filter_with_fallback(df, prefs) -> pd.DataFrame:
    result = filter_restaurants(df, prefs)
    if len(result) >= 3:
        return result
    # Level 1: drop cuisine
    ...
```

### Deliverables
- [x] `engine.py` applies all four filters correctly
- [x] Results sorted by rating and votes
- [x] Fallback strategy implemented and tested
- [x] Returns at most `FILTER_TOP_N` candidates

---

## Phase 5: Prompt Builder + Groq LLM Integration

### Goal
Construct a high-quality LLM prompt from filtered candidates, call the Groq API, and parse the response into structured `Recommendation` objects.

### Tasks

#### 5.1 — Prompt Builder (`src/prompt/builder.py`)

```python
import pandas as pd
from src.models.preferences import UserPreferences

SYSTEM_PROMPT = """You are an expert restaurant concierge. Given a list of restaurants \
and a user's preferences, rank the top 3–5 restaurants and explain why each is a great \
fit. Be concise, friendly, and specific. Format each recommendation as:

#<rank>. <Restaurant Name>
Explanation: <2–3 sentences>
"""

def build_prompt(candidates: pd.DataFrame, prefs: UserPreferences) -> tuple[str, str]:
    restaurant_list = ""
    for i, (_, row) in enumerate(candidates.iterrows(), start=1):
        restaurant_list += (
            f"{i}. {row['name']} | Cuisine: {row['cuisine']} | "
            f"Rating: {row['rating']} | Cost for two: ₹{row['avg_cost_for_two']} | "
            f"Tags: {row.get('features', 'N/A')}\n"
        )

    user_prompt = f"""User Preferences:
- Location: {prefs.location}
- Budget: {prefs.budget}
- Cuisine: {prefs.cuisine}
- Minimum Rating: {prefs.min_rating}
- Additional: {prefs.extras if prefs.extras else 'None'}

Available Restaurants:
{restaurant_list}
Please rank the top restaurants and provide a short explanation for each."""

    return SYSTEM_PROMPT, user_prompt
```

#### 5.2 — Groq LLM Client (`src/llm/client.py`)

```python
from groq import Groq
from config.settings import GROQ_API_KEY, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS

client = Groq(api_key=GROQ_API_KEY)

def call_groq(system_prompt: str, user_prompt: str) -> str:
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS
    )
    return response.choices[0].message.content
```

#### 5.3 — Response Parser (`src/llm/parser.py`)

```python
import re
import pandas as pd
from src.models.recommendation import Recommendation

def parse_response(raw: str, candidates: pd.DataFrame) -> list[Recommendation]:
    recommendations = []
    blocks = re.split(r"\n(?=#\d+\.)", raw.strip())

    for block in blocks:
        rank_match = re.match(r"#(\d+)\.\s+(.+)", block)
        expl_match = re.search(r"Explanation:\s+(.+)", block, re.DOTALL)

        if not rank_match:
            continue

        rank = int(rank_match.group(1))
        name = rank_match.group(2).strip()
        explanation = expl_match.group(1).strip() if expl_match else ""

        # Look up metadata from candidates DataFrame
        match = candidates[candidates["name"].str.lower() == name.lower()]
        if not match.empty:
            row = match.iloc[0]
            recommendations.append(Recommendation(
                rank=rank,
                name=row["name"],
                cuisine=row["cuisine"],
                rating=float(row["rating"]),
                estimated_cost=f"₹{row['avg_cost_for_two']} for two",
                explanation=explanation
            ))

    return sorted(recommendations, key=lambda r: r.rank)
```

#### 5.4 — Groq Model Selection Guide

| Scenario | Recommended Model |
|---|---|
| Default (best quality) | `llama3-70b-8192` |
| Faster / lower cost | `llama3-8b-8192` |
| Verbose prompts / many candidates | `mixtral-8x7b-32768` |

### Deliverables
- [ ] `builder.py` generates valid system + user prompt pair
- [ ] `client.py` successfully calls Groq API and returns text
- [ ] `parser.py` extracts ranked `Recommendation` objects from LLM response
- [ ] Error handling for API failures (rate limits, invalid key)

---

## Phase 6: Backend API

### Goal
Expose the recommendation pipeline as a **REST API** using FastAPI, so the frontend (Phase 7) can call it via HTTP. FastAPI also serves the frontend static files, making this a single-server deployment.

### New Dependencies
Add to `requirements.txt`:
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9
```

### Tasks

#### 6.1 — Pydantic API Schemas (`src/api/schemas.py`)

```python
from pydantic import BaseModel, Field
from typing import List

class PreferencesRequest(BaseModel):
    location:   str
    budget:     str          # "low" | "medium" | "high"
    cuisine:    str
    min_rating: float = Field(ge=0.0, le=5.0)
    extras:     str = ""

class RecommendationItem(BaseModel):
    rank:           int
    name:           str
    cuisine:        str
    rating:         float
    estimated_cost: str
    explanation:    str

class RecommendResponse(BaseModel):
    recommendations: List[RecommendationItem]
    total_found:     int
```

#### 6.2 — FastAPI App (`src/api/app.py`)

```python
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.api.schemas import PreferencesRequest, RecommendResponse, RecommendationItem
from src.models.preferences import UserPreferences
from src.filter.engine import filter_with_fallback
from src.prompt.builder import build_prompt
from src.llm.client import call_groq
from src.llm.parser import parse_response
from config.settings import OUTPUT_TOP_K
import pandas as pd

app = FastAPI(title="Restaurant Recommender API", version="1.0.0")

# Shared preprocessed DataFrame (loaded at startup)
df: pd.DataFrame = None

@app.on_event("startup")
async def startup_event():
    global df
    from src.data.loader import load_or_fetch
    from src.data.preprocessor import preprocess
    raw = load_or_fetch()
    df = preprocess(raw)

@app.post("/recommend", response_model=RecommendResponse)
async def recommend(prefs_req: PreferencesRequest):
    prefs = UserPreferences(**prefs_req.dict())
    candidates = filter_with_fallback(df, prefs)

    if candidates.empty:
        raise HTTPException(status_code=404, detail="No restaurants found. Try relaxing your filters.")

    system_prompt, user_prompt = build_prompt(candidates, prefs)
    raw_response = call_groq(system_prompt, user_prompt)
    recs = parse_response(raw_response, candidates)

    return RecommendResponse(
        recommendations=[RecommendationItem(**vars(r)) for r in recs[:OUTPUT_TOP_K]],
        total_found=len(candidates)
    )

# Serve frontend static files
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
```

#### 6.3 — Updated Entry Point (`main.py`)

```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, reload=True)
```

#### 6.4 — Error Handling

| Scenario | Handling |
|---|---|
| No dataset found | Re-fetch from Hugging Face on startup |
| No filter results | HTTP 404 with descriptive message |
| Groq API key missing | HTTP 500 with clear error on first call |
| Groq rate limit hit | Retry with exponential backoff (max 3 attempts) |
| LLM response unparseable | HTTP 500; log raw response for debugging |
| Invalid request body | FastAPI auto-validates via Pydantic (HTTP 422) |

### Deliverables
- [ ] `src/api/schemas.py` — Pydantic request/response models
- [ ] `src/api/app.py` — FastAPI app with `/recommend` POST endpoint
- [ ] Dataset loaded once at startup, shared across requests
- [ ] Frontend static files served from `/`
- [ ] `main.py` launches Uvicorn server
- [ ] All error scenarios return proper HTTP status codes

---

## Phase 7: Frontend Web UI

### Goal
Build a **premium, dark-mode web interface** that lets users enter preferences and displays AI-generated restaurant recommendations beautifully. Communicates with the Phase 6 backend via `fetch()`.

### Design Direction
- **Dark glassmorphism** aesthetic — semi-transparent frosted panels over a deep gradient background
- **Animated hero section** with a glowing title and subtitle
- **Preference form** with styled inputs, a budget dropdown, cuisine field, and a star-rating slider
- **Recommendation cards** rendered dynamically with rank badge, cuisine tag, rating stars, cost, and LLM explanation
- **Loading skeleton** animation while awaiting API response
- **Fully responsive** — works on desktop and mobile
- Google Fonts: **Outfit** for headings, **Inter** for body text

### New Files

#### 6.1 — `frontend/index.html`
Main page structure:
- `<head>` — SEO meta tags, Google Fonts, link to `style.css`
- Hero section with headline and tagline
- Preference form (`#recommendation-form`) with fields:
  - Location text input
  - Budget select (Low / Medium / High)
  - Cuisine text input
  - Min Rating range slider (0.0–5.0, live label)
  - Extras textarea
  - Submit button
- Results section (`#results`) — hidden until response arrives
- Loading overlay (`#loading`) — shown during API call
- Links `app.js` at bottom of body

#### 6.2 — `frontend/style.css`
Full design system:

```css
/* Design tokens */
:root {
  --bg-primary:    #0a0a0f;
  --bg-secondary:  #12121a;
  --glass-bg:      rgba(255, 255, 255, 0.05);
  --glass-border:  rgba(255, 255, 255, 0.1);
  --accent:        #f97316;   /* warm orange */
  --accent-glow:   rgba(249, 115, 22, 0.3);
  --text-primary:  #f1f5f9;
  --text-muted:    #94a3b8;
  --card-radius:   16px;
  --transition:    0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
```

Key components:
- `.glass-panel` — backdrop-filter blur card base class
- `.form-group` — labeled input with focus glow effect
- `.btn-primary` — gradient orange CTA with hover lift + glow
- `.restaurant-card` — animated entry, rank badge, star rating row
- `.cuisine-tag` — pill badge per cuisine
- `.skeleton` — shimmer loading placeholder
- `@keyframes fadeSlideUp` — card entrance animation
- `@keyframes shimmer` — loading skeleton animation
- Media queries for mobile (`max-width: 768px`)

#### 6.3 — `frontend/app.js`
Behavior:
1. Listen for form submit → prevent default → show `#loading`
2. Read all form values and build JSON payload
3. `fetch('http://localhost:8000/recommend', { method: 'POST', body: JSON.stringify(payload) })`
4. On success → hide loading → render recommendation cards dynamically
5. On error → show friendly error message inside `#results`
6. Slider input → live-update displayed rating value label
7. Stagger card animation with `animation-delay` per card index

### Deliverables
- [ ] `frontend/index.html` — semantic, accessible, SEO-ready
- [ ] `frontend/style.css` — full dark glassmorphism design system
- [ ] `frontend/app.js` — form handling, API call, dynamic card rendering
- [ ] Loading skeleton shown during API response wait
- [ ] Recommendation cards display all fields (rank, name, cuisine, rating, cost, explanation)
- [ ] Responsive layout for mobile and desktop
- [ ] End-to-end tested in browser with live backend

---

## Testing Plan

| Test | Type | Description |
|---|---|---|
| Dataset loads correctly | Unit | Verify DataFrame shape and column presence |
| Preprocessor normalizes fields | Unit | Check dtypes, null counts, budget mapping |
| Filter returns correct results | Unit | Mock DataFrame; assert filtered output |
| Filter fallback triggers | Unit | Use strict filters that return < 3 results |
| Prompt is well-formed | Unit | Assert system + user prompt contain expected fields |
| Groq API call succeeds | Integration | Live call with a simple prompt |
| Parser extracts recommendations | Unit | Mock LLM response string; assert Recommendation objects |
| End-to-end pipeline runs | E2E | Run `main.py` with predefined inputs |

---

## Milestone Tracker

| Phase | Description | Status |
|---|---|---|
| Phase 1 | Project Setup & Environment | ⬜ Not Started |
| Phase 2 | Data Ingestion & Preprocessing | ⬜ Not Started |
| Phase 3 | User Input Handler *(optional/legacy CLI)* | ⬜ Not Started |
| Phase 4 | Filter Engine | ✅ Completed |
| Phase 5 | Prompt Builder + Groq LLM Integration | ✅ Completed |
| Phase 6 | Backend API (FastAPI) | ✅ Completed |
| Phase 7 | Frontend Web UI | ⬜ Not Started |

---

## Dependencies Graph

```
Phase 1 (Setup)
    │
    ├──▶ Phase 2 (Data)
    │         │
    │         └──▶ Phase 4 (Filter) ──────────────────────────────┐
    │                                                               │
    ├──▶ Phase 3 (optional CLI input) ─────────────────────────────┤
    │                                                               │
    │                                                        Phase 5 (LLM)
    │                                                               │
    │                                                        Phase 6 (Backend API)
    │                                                               │
    └──────────────────────────────────────────────────────▶ Phase 7 (Frontend)
```

---

*Sources: [`Docs/context.md`](file:///c:/Users/kumar/Downloads/Project%20!/Docs/context.md) · [`Docs/architecture.md`](file:///c:/Users/kumar/Downloads/Project%20!/Docs/architecture.md)*
