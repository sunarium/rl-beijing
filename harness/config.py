"""
Configuration models and CLI argument parsing for the LLM agent harness.
"""
from __future__ import annotations

import argparse
import os
from dotenv import load_dotenv

load_dotenv()  # loads .env from cwd or parent dirs


class RunConfig:
    """Flat configuration for a benchmark run, parsed from CLI args."""

    def __init__(
        self,
        models: list[str],
        runs_per_model: int = 5,
        seeds: list[int] | None = None,
        game_url: str = "http://localhost:8000",
        api_key: str = "",
        api_base_url: str | None = None,
        concurrent: int = 3,
        max_turns: int = 200,
        verbose: bool = False,
        transcript: bool = False,
        reasoning_effort: str | None = None,
        output_dir: str = "./harness/results",
    ):
        self.models = models
        self.runs_per_model = runs_per_model
        self.seeds = seeds
        self.game_url = game_url.rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.api_base_url = api_base_url or os.environ.get("OPENAI_BASE_URL", None)
        self.concurrent = concurrent
        self.max_turns = max_turns
        self.verbose = verbose
        self.transcript = transcript
        self.reasoning_effort = reasoning_effort or os.environ.get("REASONING_EFFORT", None)
        self.output_dir = output_dir

    def get_seeds(self) -> list[int]:
        """Return the list of seeds for this benchmark run."""
        if self.seeds is not None:
            return self.seeds
        import random
        return [random.randint(0, 999999) for _ in range(self.runs_per_model)]


def parse_args(argv: list[str] | None = None) -> RunConfig:
    """Parse CLI arguments into a RunConfig."""
    parser = argparse.ArgumentParser(
        description="北京浮生记 — LLM Agent Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m harness.main --model gpt-4o-mini --runs 3\n"
            "  python -m harness.main --model gpt-4o deepseek-chat --runs 5 --concurrent 4\n"
            "  python -m harness.main --model gpt-4o-mini --runs 1 --verbose\n"
        ),
    )
    parser.add_argument(
        "--model", "-m",
        action="append",
        dest="models",
        help="OpenAI-compatible model ID (repeatable, e.g. -m gpt-4o -m deepseek-chat). Falls back to LLM_MODEL env var.",
    )
    parser.add_argument(
        "--runs", "-n",
        type=int,
        default=5,
        dest="runs_per_model",
        help="Number of game runs per model (default: 5)",
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default=None,
        help="Comma-separated seed list, or 'N-M' range (e.g. '0-9' or '42,100,200')",
    )
    parser.add_argument(
        "--game-url",
        default="http://localhost:8000",
        help="Game backend base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="OpenAI API key (falls back to OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--api-base-url",
        default=None,
        help="Custom API base URL for OpenAI-compatible providers (e.g. http://localhost:11434/v1)",
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=3,
        help="Max concurrent game runs (default: 3)",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=200,
        help="Max agent turns per game (default: 200)",
    )
    parser.add_argument(
        "--reasoning-effort", "-r",
        type=str,
        default=None,
        choices=["low", "medium", "high"],
        help="Reasoning effort for o-series/Claude models (low/medium/high). Falls back to REASONING_EFFORT env var.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Print detailed per-turn logs",
    )
    parser.add_argument(
        "--transcript", "-t",
        action="store_true",
        default=False,
        help="Save a full transcript per run (conversation + tool calls) to output dir",
    )
    parser.add_argument(
        "--output", "-o",
        default="./harness/results",
        help="Results output directory (default: ./harness/results)",
    )

    args = parser.parse_args(argv)

    # If --model not given, fall back to LLM_MODEL env var
    if not args.models:
        env_model = os.environ.get("LLM_MODEL")
        if env_model:
            args.models = [env_model]
        else:
            parser.error("at least one --model/-m is required (or set LLM_MODEL in .env)")

    # Parse seeds argument
    seeds = None
    if args.seeds:
        if "-" in args.seeds and "," not in args.seeds:
            lo, hi = args.seeds.split("-", 1)
            seeds = list(range(int(lo), int(hi) + 1))
        else:
            seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]

    return RunConfig(
        models=args.models,
        runs_per_model=args.runs_per_model if seeds is None else len(seeds),
        seeds=seeds,
        game_url=args.game_url,
        api_key=args.api_key,
        api_base_url=args.api_base_url,
        concurrent=args.concurrent,
        max_turns=args.max_turns,
        verbose=args.verbose,
        transcript=args.transcript,
        reasoning_effort=args.reasoning_effort,
        output_dir=args.output,
    )