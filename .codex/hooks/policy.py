#!/usr/bin/env python3
"""Защита файлов проекта для хуков Codex."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def changed_paths(command: str) -> list[Path]:
    paths = []
    for line in command.splitlines():
        match = re.match(r"\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$", line)
        if match:
            candidate = Path(match.group(1).strip())
            paths.append(candidate if candidate.is_absolute() else ROOT / candidate)
    return paths


def protected(path: Path) -> str | None:
    path = path.resolve()
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        return None
    parts = rel.parts
    if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
        return "секреты .env"
    if any(part in {".git", ".venv", "node_modules"} for part in parts):
        return "служебные файлы или зависимости"
    if path.name == "package-lock.json":
        return "lock-файл меняется через npm"
    if len(parts) == 4 and parts[:3] == ("backend", "alembic", "versions") and path.suffix == ".py" and path.exists():
        return "существующая миграция Alembic; нужна новая ревизия"
    return None


def main() -> int:
    event = json.load(sys.stdin)
    if event.get("tool_name") != "apply_patch":
        return 0
    paths = changed_paths(event.get("tool_input", {}).get("command", ""))
    if "PreToolUse" in event.get("hook_event_name", ""):
        for path in paths:
            reason = protected(path)
            if reason:
                print(f"Заблокировано: {path.relative_to(ROOT)} — {reason}", file=sys.stderr)
                return 2
        return 0
    if "PostToolUse" not in event.get("hook_event_name", ""):
        return 0
    ruff = ROOT / "backend/.venv/bin/ruff"
    if not ruff.exists():
        return 0
    for path in paths:
        if path.is_file() and path.suffix == ".py" and path.is_relative_to(ROOT / "backend"):
            for args in ([str(ruff), "format", "-q", str(path)], [str(ruff), "check", str(path)]):
                result = subprocess.run(args, cwd=ROOT / "backend", capture_output=True, text=True, check=False)
                if result.returncode:
                    print(result.stdout + result.stderr, file=sys.stderr)
                    return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
