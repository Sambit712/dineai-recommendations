# AI-Powered Restaurant Recommendation System

An intelligent restaurant recommendation service powered by **Groq LLM** (`llama3-70b-8192`) and the **Zomato dataset** from Hugging Face.

## Features

- 🔍 Filters restaurants by location, budget, cuisine, and rating
- 🤖 Uses Groq's ultra-fast LLM inference to rank and explain recommendations
- 🍽  Displays top picks in a clean, styled terminal UI

## Requirements

- Python 3.10+
- A free [Groq API key](https://console.groq.com/keys)

## Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd <project-folder>

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
# Then edit .env and add your GROQ_API_KEY

# 5. Run the app
python main.py
```

## Project Structure

```
project/
├── data/               # Auto-generated dataset cache (git-ignored)
├── src/
│   ├── data/           # Dataset loading & preprocessing (Phase 2)
│   ├── input/          # User preference collection (Phase 3)
│   ├── filter/         # Restaurant filtering engine (Phase 4)
│   ├── prompt/         # LLM prompt builder (Phase 5)
│   ├── llm/            # Groq API client & response parser (Phase 5)
│   ├── output/         # Terminal output renderer (Phase 6)
│   └── models/         # Shared dataclasses
├── config/             # Settings & environment config
├── Docs/               # Project documentation
├── main.py             # Application entry point
└── requirements.txt
```

## Dataset

[ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) — auto-downloaded on first run.

## Documentation

| Document | Description |
|---|---|
| [context.md](Docs/context.md) | Project context and objectives |
| [architecture.md](Docs/architecture.md) | System architecture |
| [implementation-plan.md](Docs/implementation-plan.md) | Phase-wise implementation plan |
| [edge-cases.md](Docs/edge-cases.md) | Edge cases and corner scenarios |
