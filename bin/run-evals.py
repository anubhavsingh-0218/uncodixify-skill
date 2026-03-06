#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONFIG_NAMES = ("with_skill", "without_skill")


def package_root() -> Path:
    return Path(__file__).resolve().parent.parent


@dataclass
class EvalCase:
    eval_id: str
    prompt: str
    expected_output: str
    files: list[str]
    assertions: list[dict[str, Any]]


def load_evals(root: Path) -> tuple[str, list[EvalCase]]:
    payload = json.loads((root / "evals" / "evals.json").read_text(encoding="utf-8"))
    return payload["skill_name"], [
        EvalCase(
            eval_id=item["id"],
            prompt=item["prompt"],
            expected_output=item["expected_output"],
            files=item.get("files", []),
            assertions=item.get("assertions", []),
        )
        for item in payload["evals"]
    ]


def slugify(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value).strip("-")


def next_iteration_dir(workspace_dir: Path) -> Path:
    existing = [int(p.name.removeprefix("iteration-")) for p in workspace_dir.iterdir() if p.is_dir() and p.name.startswith("iteration-") and p.name.removeprefix("iteration-").isdigit()]
    return workspace_dir / f"iteration-{max(existing, default=0) + 1}"


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def copy_eval_files(root: Path, eval_case: EvalCase, target_dir: Path) -> list[str]:
    copied: list[str] = []
    for relative_file in eval_case.files:
      source = root / relative_file
      destination = target_dir / Path(relative_file).name
      destination.parent.mkdir(parents=True, exist_ok=True)
      shutil.copy2(source, destination)
      copied.append(str(destination))
    return copied


def build_prompt(root: Path, eval_case: EvalCase, config_name: str, outputs_dir: Path, copied_inputs: list[str]) -> str:
    return "\n".join(
        [
            "Execute this task:",
            f"- Package path: {root}",
            f"- Skill path: {root if config_name == 'with_skill' else 'NONE (baseline run)'}",
            f"- Task: {eval_case.prompt}",
            f"- Expected output: {eval_case.expected_output}",
            f"- Input files: {', '.join(copied_inputs) if copied_inputs else 'None'}",
            f"- Save outputs to: {outputs_dir}",
            "",
            "After the run completes:",
            f"- Save produced artifacts under {outputs_dir}",
            "- Record token and duration data in timing.json",
            "- Grade assertions and write results to grading.json",
            "",
        ]
    )


def create_iteration(root: Path, force_name: str | None = None) -> Path:
    skill_name, evals = load_evals(root)
    workspace_dir = root / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    iteration_dir = workspace_dir / force_name if force_name else next_iteration_dir(workspace_dir)
    iteration_dir.mkdir(parents=True, exist_ok=False)

    write_json(iteration_dir / "benchmark.json", {"skill_name": skill_name, "iteration": iteration_dir.name, "run_summary": {}})
    for eval_case in evals:
        eval_dir = iteration_dir / f"eval-{slugify(eval_case.eval_id)}"
        for config_name in CONFIG_NAMES:
            run_dir = eval_dir / config_name
            outputs_dir = run_dir / "outputs"
            inputs_dir = run_dir / "inputs"
            outputs_dir.mkdir(parents=True, exist_ok=True)
            inputs_dir.mkdir(parents=True, exist_ok=True)
            copied_inputs = copy_eval_files(root, eval_case, inputs_dir)
            write_json(run_dir / "timing.json", {"total_tokens": None, "duration_ms": None})
            write_json(run_dir / "grading.json", {"assertion_results": [], "summary": {"passed": 0, "failed": 0, "total": len(eval_case.assertions), "pass_rate": None}})
            (run_dir / "prompt.txt").write_text(build_prompt(root, eval_case, config_name, outputs_dir, copied_inputs), encoding="utf-8")
        write_json(eval_dir / "meta.json", {"id": eval_case.eval_id, "prompt": eval_case.prompt, "expected_output": eval_case.expected_output, "files": eval_case.files, "assertions": eval_case.assertions})
    return iteration_dir


def summarize_metric(values: list[float]) -> dict[str, float]:
    return {"mean": statistics.fmean(values), "stddev": statistics.stdev(values) if len(values) > 1 else 0.0}


def aggregate_iteration(iteration_dir: Path) -> dict[str, Any]:
    per_config = {name: {"pass_rate": [], "time_seconds": [], "tokens": []} for name in CONFIG_NAMES}
    for eval_dir in sorted(path for path in iteration_dir.iterdir() if path.is_dir() and path.name.startswith("eval-")):
        for config_name in CONFIG_NAMES:
            run_dir = eval_dir / config_name
            timing = json.loads((run_dir / "timing.json").read_text(encoding="utf-8"))
            grading = json.loads((run_dir / "grading.json").read_text(encoding="utf-8"))
            if isinstance(grading.get("summary", {}).get("pass_rate"), (int, float)):
                per_config[config_name]["pass_rate"].append(float(grading["summary"]["pass_rate"]))
            if isinstance(timing.get("duration_ms"), (int, float)):
                per_config[config_name]["time_seconds"].append(float(timing["duration_ms"]) / 1000.0)
            if isinstance(timing.get("total_tokens"), (int, float)):
                per_config[config_name]["tokens"].append(float(timing["total_tokens"]))

    run_summary: dict[str, Any] = {}
    for config_name, metrics in per_config.items():
        run_summary[config_name] = {metric: summarize_metric(values) for metric, values in metrics.items() if values}

    delta: dict[str, float] = {}
    for metric in ("pass_rate", "time_seconds", "tokens"):
        left = run_summary.get("with_skill", {}).get(metric)
        right = run_summary.get("without_skill", {}).get(metric)
        if left and right:
            delta[metric] = round(left["mean"] - right["mean"], 4)
    benchmark = {"iteration": iteration_dir.name, "run_summary": {"with_skill": run_summary.get("with_skill", {}), "without_skill": run_summary.get("without_skill", {}), "delta": delta}}
    write_json(iteration_dir / "benchmark.json", benchmark)
    return benchmark


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize and aggregate uncodixify eval workspaces.")
    parser.add_argument("--iteration", help="Explicit iteration name to create.")
    parser.add_argument("--aggregate-only", action="store_true")
    parser.add_argument("--iteration-dir", help="Existing iteration directory to aggregate.")
    args = parser.parse_args()

    root = package_root()
    if args.aggregate_only:
        if not args.iteration_dir:
            raise SystemExit("--iteration-dir is required with --aggregate-only")
        benchmark = aggregate_iteration(Path(args.iteration_dir).resolve())
        print(json.dumps(benchmark, indent=2))
        return 0

    iteration_dir = create_iteration(root, args.iteration)
    benchmark = aggregate_iteration(iteration_dir)
    print(iteration_dir)
    print(json.dumps(benchmark, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
