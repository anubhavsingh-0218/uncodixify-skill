#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def package_root() -> Path:
    return Path(__file__).resolve().parent.parent


def extract_frontmatter(text: str) -> tuple[str | None, str | None]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "missing YAML frontmatter delimited by ---"
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[1:index]), None
    return None, "missing closing frontmatter delimiter ---"


def parse_frontmatter(raw: str) -> tuple[dict[str, str] | None, str | None]:
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            return None, f"invalid YAML: missing ':' in line {line!r}"
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("\"'")
    return data, None


def validate_skill(path: Path) -> list[str]:
    raw, err = extract_frontmatter(path.read_text(encoding="utf-8"))
    if err:
        return [err]
    parsed, parse_err = parse_frontmatter(raw or "")
    if parse_err:
        return [parse_err]
    assert parsed is not None

    errors: list[str] = []
    allowed = {"name", "description"}
    missing = sorted(allowed - set(parsed))
    extra = sorted(set(parsed) - allowed)
    if missing:
        errors.append(f"missing required frontmatter key(s): {', '.join(missing)}")
    if extra:
        errors.append(f"unexpected frontmatter key(s): {', '.join(extra)}")
    if parsed.get("name") and not re.fullmatch(r"[a-z0-9-]+", parsed["name"]):
        errors.append("name must use lowercase letters, digits, and hyphens only")
    if parsed.get("description") and not parsed["description"].startswith("Use when"):
        errors.append("description should start with 'Use when'")
    return errors


def validate_evals(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid JSON in {path.name}: {exc}"]

    if not isinstance(payload, dict):
        return ["evals/evals.json must contain a top-level object"]
    if not isinstance(payload.get("skill_name"), str) or not payload["skill_name"].strip():
        errors.append("evals/evals.json must define a non-empty skill_name")
    evals = payload.get("evals")
    if not isinstance(evals, list) or not evals:
        errors.append("evals/evals.json must define a non-empty evals array")
        return errors

    supported = {
        "output_file_exists",
        "output_text_contains",
        "output_text_not_contains",
        "output_text_matches_regex",
        "output_text_not_matches_regex",
    }
    for index, item in enumerate(evals, start=1):
        if not isinstance(item, dict):
            errors.append(f"eval {index} must be an object")
            continue
        for key in ("id", "prompt", "expected_output"):
            value = item.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"eval {index} is missing non-empty {key!r}")
        files = item.get("files", [])
        if not isinstance(files, list):
            errors.append(f"eval {index} files must be an array when present")
        assertions = item.get("assertions", [])
        if not isinstance(assertions, list):
            errors.append(f"eval {index} assertions must be an array when present")
            continue
        for a_index, assertion in enumerate(assertions, start=1):
            if not isinstance(assertion, dict):
                errors.append(f"eval {index} assertion {a_index} must be an object")
                continue
            for key in ("id", "type", "description"):
                value = assertion.get(key)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"eval {index} assertion {a_index} is missing non-empty {key!r}")
            assertion_type = assertion.get("type")
            if assertion_type not in supported:
                errors.append(f"eval {index} assertion {a_index} has unsupported type {assertion_type!r}")
                continue
            path_glob = assertion.get("path_glob")
            if not isinstance(path_glob, str) or not path_glob.strip():
                errors.append(f"eval {index} assertion {a_index} must define non-empty 'path_glob'")
            if assertion_type in {"output_text_contains", "output_text_not_contains"}:
                text = assertion.get("text")
                if not isinstance(text, str) or not text:
                    errors.append(f"eval {index} assertion {a_index} must define non-empty 'text'")
            if assertion_type in {"output_text_matches_regex", "output_text_not_matches_regex"}:
                pattern = assertion.get("pattern")
                if not isinstance(pattern, str) or not pattern:
                    errors.append(f"eval {index} assertion {a_index} must define non-empty 'pattern'")
                else:
                    try:
                        re.compile(pattern)
                    except re.error as exc:
                        errors.append(f"eval {index} assertion {a_index} has invalid regex: {exc}")
    return errors


def main() -> int:
    root = package_root()
    errors: list[str] = []
    errors.extend(validate_skill(root / "SKILL.md"))
    errors.extend(validate_evals(root / "evals" / "evals.json"))
    if not (root / "workspace" / ".gitignore").exists():
        errors.append("missing workspace/.gitignore")

    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
