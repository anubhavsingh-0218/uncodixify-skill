#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def package_root() -> Path:
    return Path(__file__).resolve().parent.parent


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def matching_files(outputs_dir: Path, path_glob: str) -> list[Path]:
    return sorted(path for path in outputs_dir.glob(path_glob) if path.is_file())


def read_text_candidates(paths: list[Path]) -> list[tuple[Path, str]]:
    result: list[tuple[Path, str]] = []
    for path in paths:
        try:
            result.append((path, path.read_text(encoding="utf-8", errors="ignore")))
        except OSError:
            continue
    return result


def evaluate_assertion(assertion: dict[str, Any], outputs_dir: Path) -> dict[str, Any]:
    assertion_type = assertion["type"]
    path_glob = assertion["path_glob"]
    matches = matching_files(outputs_dir, path_glob)
    relative_matches = [str(path.relative_to(outputs_dir)) for path in matches]
    result = {"id": assertion["id"], "text": assertion["description"], "passed": False, "evidence": ""}

    if assertion_type == "output_file_exists":
        result["passed"] = bool(matches)
        result["evidence"] = f"Matched files: {', '.join(relative_matches)}" if matches else f"No files matched glob {path_glob!r}"
        return result
    if not matches:
        result["evidence"] = f"No files matched glob {path_glob!r}"
        return result
    text_candidates = read_text_candidates(matches)
    if not text_candidates:
        result["evidence"] = f"Matched files exist but none could be read as text for glob {path_glob!r}"
        return result

    if assertion_type == "output_text_contains":
        needle = assertion["text"]
        hit = next((str(path.relative_to(outputs_dir)) for path, content in text_candidates if needle in content), None)
        result["passed"] = hit is not None
        result["evidence"] = f"Found text in {hit}" if hit else f"Did not find required text {needle!r} in {', '.join(relative_matches)}"
        return result

    if assertion_type == "output_text_not_contains":
        needle = assertion["text"]
        violating = [str(path.relative_to(outputs_dir)) for path, content in text_candidates if needle in content]
        result["passed"] = not violating
        result["evidence"] = f"Text {needle!r} absent from all matched files" if result["passed"] else f"Found forbidden text {needle!r} in {', '.join(violating)}"
        return result

    regex = re.compile(assertion["pattern"])
    if assertion_type == "output_text_matches_regex":
        hit = next((str(path.relative_to(outputs_dir)) for path, content in text_candidates if regex.search(content)), None)
        result["passed"] = hit is not None
        result["evidence"] = f"Regex matched in {hit}" if hit else f"Regex {assertion['pattern']!r} did not match any of {', '.join(relative_matches)}"
        return result

    if assertion_type == "output_text_not_matches_regex":
        violating = [str(path.relative_to(outputs_dir)) for path, content in text_candidates if regex.search(content)]
        result["passed"] = not violating
        result["evidence"] = f"Regex {assertion['pattern']!r} absent from all matched files" if result["passed"] else f"Regex {assertion['pattern']!r} matched in {', '.join(violating)}"
        return result

    result["evidence"] = f"Unsupported assertion type {assertion_type!r}"
    return result


def grade_run(run_dir: Path, assertions: list[dict[str, Any]]) -> None:
    results = [evaluate_assertion(assertion, run_dir / "outputs") for assertion in assertions]
    passed = sum(1 for result in results if result["passed"])
    total = len(results)
    write_json(run_dir / "grading.json", {"assertion_results": results, "summary": {"passed": passed, "failed": total - passed, "total": total, "pass_rate": round(passed / total, 4) if total else None}})


def main() -> int:
    parser = argparse.ArgumentParser(description="Grade mechanical assertions for uncodixify eval runs.")
    parser.add_argument("--iteration-dir", required=True)
    args = parser.parse_args()

    root = package_root()
    iteration_dir = Path(args.iteration_dir).resolve()
    for eval_dir in sorted(path for path in iteration_dir.iterdir() if path.is_dir() and path.name.startswith("eval-")):
        meta = read_json(eval_dir / "meta.json")
        assertions = meta.get("assertions", [])
        for config_name in ("with_skill", "without_skill"):
            grade_run(eval_dir / config_name, assertions)
    subprocess.run([sys.executable, str(root / "bin" / "run-evals.py"), "--aggregate-only", "--iteration-dir", str(iteration_dir)], check=True)
    print(f"Graded {iteration_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
