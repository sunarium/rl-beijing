"""
CLI entry point for the LLM agent benchmark.
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from .config import parse_args, RunConfig
from .agent import run_agent


def run_single(cfg: RunConfig, model: str, seed: int | None) -> dict:
    """Run a single agent game and return the result."""
    transcript_path = None
    if cfg.transcript and seed is not None:
        safe_model = model.replace("/", "_").replace(":", "_")
        transcript_path = os.path.join(
            cfg.output_dir, "transcripts",
            f"{safe_model}_seed{seed}.md",
        )
    return run_agent(
        model=model,
        seed=seed,
        game_url=cfg.game_url,
        api_key=cfg.api_key,
        api_base_url=cfg.api_base_url,
        max_turns=cfg.max_turns,
        verbose=cfg.verbose,
        transcript=cfg.transcript,
        transcript_path=transcript_path,
        reasoning_effort=cfg.reasoning_effort,
    )


def aggregate_results(results: list[dict]) -> dict:
    """Aggregate per-model results into summary stats."""
    if not results:
        return {
            "total_runs": 0,
            "avg_score": 0,
            "median_score": 0,
            "min_score": 0,
            "max_score": 0,
            "win_rate": 0,
            "survival_rate": 0,
            "avg_health": 0,
            "avg_fame": 0,
            "avg_debt": 0,
            "avg_days": 0,
        }

    scores = [r["final_score"] for r in results]
    sorted_scores = sorted(scores)
    n = len(sorted_scores)

    survivors = [r for r in results if r["health"] > 0]
    winners = [r for r in results if r["final_score"] > 0]

    return {
        "total_runs": n,
        "avg_score": sum(scores) / n,
        "median_score": sorted_scores[n // 2] if n % 2 == 1 else (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2,
        "min_score": sorted_scores[0],
        "max_score": sorted_scores[-1],
        "win_rate": len(winners) / n * 100,
        "survival_rate": len(survivors) / n * 100,
        "avg_health": sum(r["health"] for r in results) / n,
        "avg_fame": sum(r["fame"] for r in results) / n,
        "avg_debt": sum(r["debt"] for r in results) / n,
        "avg_days": sum(r["days_used"] for r in results) / n,
        "avg_turns": sum(r["turns"] for r in results) / n,
    }


def print_table(model_stats: dict[str, dict]):
    """Print a formatted comparison table."""
    col_w = 24
    header = (
        f"{'Model'.ljust(col_w)} {'Runs':>5} {'Avg Score':>10} "
        f"{'Win%':>6} {'Surv%':>6} {'Avg Health':>10} {'Avg Debt':>10}"
    )
    print()
    print("=" * len(header))
    print("📊 Benchmark Results")
    print("=" * len(header))
    print(header)
    print("-" * len(header))
    for model, stats in sorted(model_stats.items()):
        score_str = f"{stats['avg_score']:,.0f}"
        print(
            f"{model.ljust(col_w)} {stats['total_runs']:>5} {score_str:>10} "
            f"{stats['win_rate']:>5.1f}% {stats['survival_rate']:>5.1f}% "
            f"{stats['avg_health']:>7.1f}  {stats['avg_debt']:>9,.0f}"
        )
    print("=" * len(header))
    print()


def print_detailed(results: list[dict], model_name: str):
    """Print detailed per-run results for a model."""
    print(f"\n📋 Detailed: {model_name}")
    print(f"{'Run':>4} {'Seed':>8} {'Score':>10} {'Cash':>8} {'Bank':>8} {'Debt':>8} {'Health':>6} {'Days':>4} {'Cause':>12}")
    print("-" * 74)
    for i, r in enumerate(results, 1):
        print(
            f"{i:>4} {str(r['seed'] or '?'):>8} {r['final_score']:>10,} "
            f"{r['cash']:>8,} {r['bank']:>8,} {r['debt']:>8,} "
            f"{r['health']:>6} {r['days_used']:>4} {r['cause']:>12}"
        )
    print()


def save_results(all_results: dict[str, list[dict]], model_stats: dict[str, dict], output_dir: str):
    """Save benchmark results to a JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"benchmark_{timestamp}.json")
    data = {
        "timestamp": timestamp,
        "summary": model_stats,
        "runs": {model: res for model, res in all_results.items()},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 Results saved to {path}")
    return path


def main():
    cfg = parse_args()
    seeds = cfg.get_seeds()

    print(f"🚀 Starting Benchmark")
    print(f"   Models: {', '.join(cfg.models)}")
    print(f"   Runs per model: {cfg.runs_per_model}")
    print(f"   Seeds: {seeds[:10]}{'...' if len(seeds) > 10 else ''}")
    print(f"   Concurrent: {cfg.concurrent}")
    print(f"   Game URL: {cfg.game_url}")
    print(f"   API Base: {cfg.api_base_url or 'https://api.openai.com/v1'}")
    print()

    all_results: dict[str, list[dict]] = {}
    model_stats: dict[str, dict] = {}

    for model in cfg.models:
        print(f"▶ Running model: {model}")
        run_results: list[dict] = []
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=cfg.concurrent) as executor:
            futures = {}
            for run_idx, seed in enumerate(seeds):
                future = executor.submit(run_single, cfg, model, seed)
                futures[future] = (run_idx, seed)

            for future in as_completed(futures):
                run_idx, seed = futures[future]
                try:
                    result = future.result()
                    run_results.append(result)
                    if cfg.verbose:
                        print(f"  ✓ Run {run_idx + 1}/{cfg.runs_per_model} (seed={seed}): score={result['final_score']:,}  cause={result['cause']}")
                except Exception as e:
                    print(f"  ✗ Run {run_idx + 1}/{cfg.runs_per_model} (seed={seed}) FAILED: {e}")
                    run_results.append({
                        "model": model,
                        "seed": seed,
                        "final_score": -999999,
                        "cash": 0, "bank": 0, "debt": 0,
                        "health": 0, "fame": 0,
                        "days_used": 0, "cause": "error",
                        "turns": 0, "score_submitted": False,
                        "error": str(e),
                    })

        elapsed = time.time() - start_time
        stats = aggregate_results(run_results)
        all_results[model] = run_results
        model_stats[model] = stats

        print(f"  ⏱  {elapsed:.0f}s total | avg score: {stats['avg_score']:,.0f} | win rate: {stats['win_rate']:.1f}%")

    # Print summary
    print_table(model_stats)

    # Print detailed per model
    for model in cfg.models:
        print_detailed(all_results[model], model)

    # Save results
    saved_path = save_results(all_results, model_stats, cfg.output_dir)
    print(f"✅ Benchmark complete. Results: {saved_path}")


if __name__ == "__main__":
    main()