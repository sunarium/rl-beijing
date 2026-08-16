# 北京浮生记 (Beijing Fushengji)

A web-based remake of the classic Chinese MFC game "北京浮生记" — a 40-day Beijing street trading simulator, with an LLM agent benchmark harness.

## Project Structure

```
├── backend/          # FastAPI game engine (Python)
├── frontend/         # Vite + React + TypeScript UI
├── harness/          # LLM agent benchmark harness
├── beijing_fushengji_spec/  # Gherkin feature specs + API contract
├── pyproject.toml    # Python project config (uv-managed)
└── .venv/            # Python virtual environment (auto-created by uv sync)
```

## Quick Start

### 1. Install Dependencies

```bash
# Python deps (backend + harness) — uv auto-creates .venv from pyproject.toml
uv sync

# Frontend deps
cd frontend && npm install && cd ..
```

### 2. Start Backend

```bash
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend runs on `http://localhost:8000`. Health check: `curl http://localhost:8000/health`.

### 3. Start Frontend

In a separate terminal:

```bash
cd frontend && npm run dev
```

Frontend runs on `http://localhost:5173/`.

### 4. Run LLM Agent Benchmark

```bash
# 1. Set up your API key
cp harness/.env.example harness/.env
# Edit harness/.env with your OPENAI_API_KEY

# 2. Single agent run (verbose)
uv run python -m harness.main --model gpt-4o-mini --runs 1 --verbose

# 3. Multi-model benchmark
uv run python -m harness.main --model gpt-4o-mini gpt-4o --runs 5 --concurrent 3

# 4. Deterministic replay (same seeds = same game RNG)
uv run python -m harness.main --model gpt-4o-mini --runs 10 --seeds 0-9

# 5. Custom API base (local models via Ollama/vLLM)
uv run python -m harness.main --model deepseek-chat --runs 3 \
  --api-base-url http://localhost:11434/v1
```

Results are saved to `harness/results/benchmark_YYYYMMDD_HHMMSS.json`.

### Alternative: Activate venv directly

```bash
source .venv/bin/activate  # then run python directly
python -m harness.main --model gpt-4o-mini --runs 5
```

## How It Works

**Game premise:** You're a migrant worker in 1990s Beijing with 40 days to make your fortune trading on the black market. Start with 2,000 yuan cash and 5,000 yuan debt.

**Agent harness:** Creates a game automatically, gives the LLM 11 semantic tools (buy/sell/travel by Chinese names, bank, repay debt, heal, etc.), runs the agent loop until game over, then auto-submits the score.

**Key rules:**
- Only `travel()` consumes days — all other actions are instant
- Each day triggers: new prices → 10% debt interest → random events → health check → theft
- Health < 85 with >3 days left → forced hospitalization (lose 1-2 days)
- Debt > 100,000 → daily beatings (-30 health)
- Score = cash + bank - debt. Maximize it!

See `beijing_fushengji_spec/` for the complete Gherkin specification and API contract.