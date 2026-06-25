# Architecture: AI-Powered Restaurant Recommendation System

> Derived from [`Docs/context.md`](file:///c:/Users/kumar/Downloads/Project%20!/Docs/context.md)

---

## 1. High-Level Architecture Overview

The system follows a **layered pipeline architecture** that separates concerns across five distinct layers: Data, Input, Processing, AI Reasoning, and Presentation.

```
┌─────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                        │
│          (CLI / Web App / Jupyter Notebook)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │  User Preferences
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      INPUT HANDLER                           │
│   Validates & normalizes: location, budget, cuisine,         │
│   minimum rating, additional preferences                     │
└──────────────────────────┬──────────────────────────────────┘
                           │  Structured Query
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      FILTER ENGINE                           │
│   Queries preprocessed restaurant DataFrame                  │
│   Returns top-N matching candidates                          │
└──────────┬────────────────────────────────────┬─────────────┘
           │ Candidate List                      │
           ▼                                     ▼
┌──────────────────────┐            ┌────────────────────────┐
│    DATA STORE        │            │    PROMPT BUILDER       │
│  (Preprocessed       │──────────▶│  Formats candidates     │
│   Zomato Dataset)    │            │  into LLM-ready prompt  │
└──────────────────────┘            └───────────┬────────────┘
                                                │  Prompt
                                                ▼
                                   ┌────────────────────────┐
                                   │     LLM INTERFACE       │
                                   │  (Groq API — ultra-fast │
                                   │   inference engine)     │
                                   └───────────┬────────────┘
                                               │  Ranked + Explained
                                               ▼
                                   ┌────────────────────────┐
                                   │    OUTPUT RENDERER      │
                                   │  Formats & displays     │
                                   │  final recommendations  │
                                   └────────────────────────┘
```

---

## 2. Component Architecture

### 2.1 Data Ingestion Layer

**Responsibility**: Load, clean, and persist the Zomato dataset for fast querying.

| Sub-Component | Description |
|---|---|
| `DatasetLoader` | Fetches dataset from Hugging Face using the `datasets` library |
| `DataPreprocessor` | Cleans nulls, normalizes budget categories, standardizes cuisine names |
| `DataStore` | In-memory Pandas DataFrame (or SQLite for persistence) |

**Data Flow**:
```
Hugging Face API
      │
      ▼
datasets.load_dataset("ManikaSaini/zomato-restaurant-recommendation")
      │
      ▼
DataPreprocessor
  ├── Drop nulls / duplicates
  ├── Normalize cost → [low | medium | high]
  ├── Standardize cuisine strings (lowercase, strip)
  ├── Cast rating to float
  └── Index by location for fast lookup
      │
      ▼
In-Memory DataFrame (df_restaurants)
```

**Key Fields After Preprocessing**:
| Field | Type | Notes |
|---|---|---|
| `name` | string | Restaurant name |
| `location` | string | City / area (normalized) |
| `cuisine` | string | Comma-separated list |
| `budget_category` | enum | `low` / `medium` / `high` |
| `avg_cost_for_two` | float | Raw cost value |
| `rating` | float | 0.0 – 5.0 |
| `votes` | int | Review count (proxy for popularity) |
| `features` | string | e.g., family-friendly, delivery |

---

### 2.2 Input Handler

**Responsibility**: Collect, validate, and normalize user preferences.

```
User Input (raw)
      │
      ▼
InputHandler.collect()
  ├── Prompt for: location, budget, cuisine, min_rating, extras
  ├── Validate types & acceptable ranges
  ├── Normalize strings (lowercase, strip whitespace)
  └── Return: UserPreferences dataclass
```

**`UserPreferences` Schema**:
```python
@dataclass
class UserPreferences:
    location: str           # e.g., "bangalore"
    budget: str             # "low" | "medium" | "high"
    cuisine: str            # e.g., "italian"
    min_rating: float       # e.g., 4.0
    extras: str             # e.g., "family-friendly, quick service"
```

---

### 2.3 Filter Engine

**Responsibility**: Query the DataStore using `UserPreferences` and return a ranked candidate list.

**Filtering Logic**:
```
df_restaurants
  │
  ├── Filter: location == user.location
  ├── Filter: budget_category == user.budget
  ├── Filter: cuisine contains user.cuisine
  ├── Filter: rating >= user.min_rating
  └── Sort by: rating DESC, votes DESC
        │
        ▼
  Top-N Candidates (default: 10)
```

**Output**: A list of `RestaurantCandidate` objects passed to the Prompt Builder.

---

### 2.4 Prompt Builder

**Responsibility**: Construct a well-engineered LLM prompt from the filtered candidates and user preferences.

**Prompt Structure**:
```
[System Prompt]
You are an expert restaurant concierge. Given a list of restaurants and a
user's preferences, rank the top 3–5 restaurants and explain why each is
a great fit. Be concise, friendly, and specific.

[User Prompt]
User Preferences:
- Location: {location}
- Budget: {budget}
- Cuisine: {cuisine}
- Minimum Rating: {min_rating}
- Additional: {extras}

Available Restaurants:
1. {name} | Cuisine: {cuisine} | Rating: {rating} | Cost for two: ₹{cost} | Tags: {features}
2. ...
N. ...

Please rank the top restaurants and provide a short explanation for each.
```

**Design Decisions**:
- System prompt establishes the LLM persona (expert concierge)
- Structured restaurant list enables the LLM to reason systematically
- User preferences are explicitly repeated to anchor ranking logic
- Explanation is enforced by the prompt to avoid bare rankings

---

### 2.5 LLM Interface

**Responsibility**: Communicate with the chosen LLM API and return structured recommendations.

```
Prompt (string)
      │
      ▼
LLMClient.call(prompt)
  ├── Provider: Groq API
  ├── Sets parameters: temperature=0.7, max_tokens=1024
  ├── Sends API request via groq Python SDK
  └── Returns: raw LLM response (string)
      │
      ▼
ResponseParser
  ├── Extracts ranked restaurant list
  ├── Extracts per-restaurant explanations
  └── Returns: List[Recommendation]
```

**`Recommendation` Schema**:
```python
@dataclass
class Recommendation:
    rank: int
    name: str
    cuisine: str
    rating: float
    estimated_cost: str
    explanation: str        # LLM-generated
```

**LLM Provider: Groq**

Groq is used for its **ultra-low latency inference** powered by the Language Processing Unit (LPU). It exposes an OpenAI-compatible chat completions API.

| Model | Context Window | Best For |
|---|---|---|
| `llama3-70b-8192` | 8,192 tokens | High-quality recommendations (default) |
| `llama3-8b-8192` | 8,192 tokens | Faster, lightweight inference |
| `mixtral-8x7b-32768` | 32,768 tokens | Long-context or verbose prompts |
| `gemma2-9b-it` | 8,192 tokens | Instruction-tuned, efficient option |

**Groq SDK Usage**:
```python
from groq import Groq

client = Groq(api_key=GROQ_API_KEY)

response = client.chat.completions.create(
    model="llama3-70b-8192",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt}
    ],
    temperature=0.7,
    max_tokens=1024
)
result = response.choices[0].message.content
```

---

### 2.6 Output Renderer

**Responsibility**: Display the final recommendations in a human-friendly format.

**CLI Output Example**:
```
╔══════════════════════════════════════════════╗
║     🍽  Top Restaurant Recommendations        ║
╚══════════════════════════════════════════════╝

#1 — The Spice Route
   Cuisine  : North Indian, Mughlai
   Rating   : ⭐ 4.6 / 5.0
   Cost     : ₹1,200 for two (Medium)
   Why?     : A perfect match for your preference for North Indian cuisine
              in Bangalore. Highly rated for ambience and quick service.

#2 — Trattoria Bella
   ...
```

---

## 3. Data Flow Diagram (End-to-End)

```
[User]
  │
  │ Enters preferences
  ▼
[Input Handler] ──────────────────────────────────────────────┐
  │ UserPreferences object                                     │
  ▼                                                           │
[Filter Engine] ◀── [DataStore (Zomato DataFrame)]            │
  │ Top-N RestaurantCandidates                                 │
  ▼                                                           │
[Prompt Builder] ◀──────────────────────────────────────────── ┘
  │ Engineered Prompt String
  ▼
[LLM Interface] ──▶ [Groq API (llama3-70b-8192)]
  │ Raw LLM Response
  ▼
[Response Parser]
  │ List[Recommendation]
  ▼
[Output Renderer]
  │
  ▼
[User] sees top ranked restaurants with AI explanations
```

---

## 4. Module / File Structure

```
project/
│
├── data/
│   └── zomato_processed.pkl        # Cached preprocessed dataset
│
├── src/
│   ├── data/
│   │   ├── loader.py               # DatasetLoader: fetch from Hugging Face
│   │   └── preprocessor.py         # DataPreprocessor: clean & normalize
│   │
│   ├── input/
│   │   └── handler.py              # InputHandler: collect & validate user input
│   │
│   ├── filter/
│   │   └── engine.py               # FilterEngine: query DataFrame
│   │
│   ├── prompt/
│   │   └── builder.py              # PromptBuilder: construct LLM prompt
│   │
│   ├── llm/
│   │   ├── client.py               # LLMClient: provider-agnostic API caller
│   │   └── parser.py               # ResponseParser: extract structured output
│   │
│   ├── output/
│   │   └── renderer.py             # OutputRenderer: display recommendations
│   │
│   └── models/
│       ├── preferences.py          # UserPreferences dataclass
│       └── recommendation.py       # Recommendation dataclass
│
├── config/
│   └── settings.py                 # LLM provider, API keys, top-N config
│
├── main.py                         # Application entry point
├── requirements.txt
└── README.md
```

---

## 5. Configuration

| Config Key | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `groq` | Fixed: Groq API |
| `GROQ_API_KEY` | *(from env)* | Groq API key — set via `.env` or environment variable |
| `LLM_MODEL` | `llama3-70b-8192` | Groq model name (`llama3-70b-8192`, `mixtral-8x7b-32768`, etc.) |
| `LLM_TEMPERATURE` | `0.7` | Controls creativity vs determinism |
| `LLM_MAX_TOKENS` | `1024` | Max response length |
| `FILTER_TOP_N` | `10` | Number of candidates sent to LLM |
| `OUTPUT_TOP_K` | `5` | Number of final recommendations shown |
| `HF_DATASET_NAME` | `ManikaSaini/zomato-restaurant-recommendation` | Hugging Face dataset ID |

---

## 6. Key Design Decisions

| Decision | Rationale |
|---|---|
| Layered pipeline | Clean separation of concerns; each stage is independently testable and replaceable |
| Filter before LLM | Reduces token cost; LLM only reasons over pre-qualified candidates |
| Groq as LLM provider | Ultra-low latency LPU inference; OpenAI-compatible API makes integration straightforward |
| `llama3-70b-8192` as default model | Strong reasoning and instruction-following quality; 8K context is sufficient for filtered candidate prompts |
| Prompt persona engineering | "Expert concierge" persona improves explanation quality and tone |
| Dataclass models | Typed, structured data prevents downstream parsing errors |
| Cached preprocessed dataset | Avoids re-fetching and re-cleaning on every run |

---

## 7. Scalability & Extension Points

| Extension | How to Add |
|---|---|
| Web UI (Flask / Streamlit) | Replace `InputHandler` + `OutputRenderer` with web endpoints |
| Vector similarity search | Embed restaurant descriptions; use FAISS for semantic filtering |
| Multi-turn conversation | Wrap the pipeline in a chat loop with conversation history |
| Persistent user profiles | Store `UserPreferences` in a database for personalization over time |
| Feedback loop | Capture user thumbs-up/down to fine-tune future prompt ranking |

---

*Source: [`Docs/context.md`](file:///c:/Users/kumar/Downloads/Project%20!/Docs/context.md)*
