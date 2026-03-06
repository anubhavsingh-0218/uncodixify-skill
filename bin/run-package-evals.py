#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


def package_root() -> Path:
    return Path(__file__).resolve().parent.parent


def run_command(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def latest_iteration_dir(workspace_dir: Path) -> Path:
    iterations = sorted(path for path in workspace_dir.iterdir() if path.is_dir() and path.name.startswith("iteration-"))
    if not iterations:
        raise RuntimeError("No iteration directories found.")
    return iterations[-1]


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def init_iteration(root: Path, iteration: str | None, reuse_latest: bool) -> Path:
    if reuse_latest:
        return latest_iteration_dir(root / "workspace")
    command = [sys.executable, str(root / "bin" / "run-evals.py")]
    if iteration:
        command.extend(["--iteration", iteration])
    result = run_command(command, root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    first_line = result.stdout.splitlines()[0].strip()
    return Path(first_line).resolve()


def process_run(root: Path, run_dir: Path, source_file: Path, with_skill: bool) -> None:
    outputs_dir = run_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    target_file = outputs_dir / source_file.name
    shutil.copy2(source_file, target_file)
    started = time.perf_counter()

    autofix_stdout = ""
    autofix_stderr = ""
    if with_skill:
        autofix = run_command(["npx", "tsx", str(root / "toolchain" / "autofix-uncodixify.ts"), str(target_file)], root)
        autofix_stdout = autofix.stdout
        autofix_stderr = autofix.stderr
        if autofix.returncode != 0:
            raise RuntimeError(autofix.stderr or autofix.stdout)

    validate = run_command([str(root / "bin" / "run-uncodixify.sh"), str(target_file)], root)
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    write_json(run_dir / "timing.json", {"total_tokens": 0, "duration_ms": elapsed_ms})
    (run_dir / "execution.log").write_text(
        "\n".join(
            [
                f"source: {source_file}",
                f"target: {target_file}",
                f"mode: {'with_skill' if with_skill else 'without_skill'}",
                "",
                "[autofix stdout]",
                autofix_stdout.rstrip(),
                "",
                "[autofix stderr]",
                autofix_stderr.rstrip(),
                "",
                "[validator stdout]",
                validate.stdout.rstrip(),
                "",
                "[validator stderr]",
                validate.stderr.rstrip(),
                "",
                f"validator_exit_code: {validate.returncode}",
            ]
        ).strip()
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run uncodixify eval iterations end to end.")
    parser.add_argument("--iteration")
    parser.add_argument("--reuse-latest", action="store_true")
    args = parser.parse_args()

    root = package_root()
    iteration_dir = init_iteration(root, args.iteration, args.reuse_latest)
    for eval_dir in sorted(path for path in iteration_dir.iterdir() if path.is_dir() and path.name.startswith("eval-")):
        meta = json.loads((eval_dir / "meta.json").read_text(encoding="utf-8"))
        source_file = root / meta["files"][0]
        process_run(root, eval_dir / "without_skill", source_file, with_skill=False)
        process_run(root, eval_dir / "with_skill", source_file, with_skill=True)

    grade = run_command([sys.executable, str(root / "bin" / "grade-evals.py"), "--iteration-dir", str(iteration_dir)], root)
    if grade.returncode != 0:
        raise RuntimeError(grade.stderr or grade.stdout)
    print(iteration_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
