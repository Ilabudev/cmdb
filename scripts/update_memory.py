#!/usr/bin/env python3
"""Пересобирает автоматическую часть docs/memory.md из истории git.

Всё между маркерами AUTO_START и AUTO_END заменяется целиком; текст до и после
маркеров не трогается. Скрипт идемпотентен: без новых коммитов файл не меняется.
Задачи из memory_tasks.json без коммитов выводятся в конце, в блоке «Задачи без коммитов».
Источник правды по названию и статусу задач — Jira: при запуске скрипт запрашивает задачи
проекта через REST API и обновляет кэш scripts/memory_tasks.json (ключ -> {title, status}).
Токен — в переменной окружения JIRA_PERSONAL_TOKEN, адрес — JIRA_URL. Нет токена или Jira
недоступна — используется кэш, скрипт не падает. Флаг --no-jira отключает запрос.
"""

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY = ROOT / "docs" / "memory.md"
TASKS = ROOT / "scripts" / "memory_tasks.json"

JIRA_URL = os.environ.get("JIRA_URL", "https://jira.ilabudev.ru").rstrip("/")
JIRA_PROJECT = "CMDB"
JIRA_TIMEOUT = 5  # секунд; хук не должен заметно задерживать коммит

AUTO_START = "<!-- auto:start — генерируется scripts/update_memory.py, не править вручную -->"
AUTO_END = "<!-- auto:end -->"

# Разделители вывода git log: поля — 0x1f, записи — 0x1e.
FORMAT = "%ad%x1f%s%x1f%b%x1e"
SUBJECT_RE = re.compile(r"^(?P<key>[A-Z][A-Z0-9_]*-\d+)\s+(?P<rest>.*)$")
TYPE_RE = re.compile(r"^(?P<type>[a-z]+)(\([^)]*\))?!?:\s*(?P<text>.*)$")
TRAILER_RE = re.compile(r"^(Co-Authored-By|Signed-off-by):", re.IGNORECASE)
NO_TASK = "Без задачи"
NO_COMMITS = "Задачи без коммитов"


def git_log() -> list[dict]:
    """Коммиты текущей ветки от старых к новым."""
    out = subprocess.run(
        ["git", "log", "--reverse", f"--format={FORMAT}", "--date=short"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    commits = []
    for record in out.split("\x1e"):
        record = record.strip("\n")
        if not record.strip():
            continue
        date, subject, body = record.split("\x1f", 2)
        match = SUBJECT_RE.match(subject)
        key = match["key"] if match else NO_TASK
        rest = match["rest"] if match else subject
        type_match = TYPE_RE.match(rest)
        text = type_match["text"] if type_match else rest
        commits.append(
            {
                "date": date,
                "key": key,
                "text": text,
                # Тело коммита без трейлеров; строки склеиваем в одно предложение.
                "body": " ".join(
                    " ".join(line.split())
                    for line in body.splitlines()
                    if not TRAILER_RE.match(line)
                ).strip(),
            }
        )
    return commits


def load_tasks() -> dict[str, dict[str, str]]:
    try:
        return json.loads(TASKS.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def fetch_jira_tasks() -> dict[str, dict[str, str]] | None:
    """Задачи проекта из Jira; None, если токена нет или Jira недоступна."""
    token = os.environ.get("JIRA_PERSONAL_TOKEN")
    if not token:
        print(
            "предупреждение: JIRA_PERSONAL_TOKEN не задан, статусы взяты из кэша", file=sys.stderr
        )
        return None
    tasks: dict[str, dict[str, str]] = {}
    start = 0
    try:
        while True:
            query = urllib.parse.urlencode(
                {
                    "jql": f"project = {JIRA_PROJECT}",
                    "fields": "summary,status",
                    "startAt": start,
                    "maxResults": 100,
                }
            )
            request = urllib.request.Request(
                f"{JIRA_URL}/rest/api/2/search?{query}",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=JIRA_TIMEOUT) as response:
                data = json.load(response)
            for issue in data["issues"]:
                fields = issue["fields"]
                tasks[issue["key"]] = {
                    "title": fields["summary"],
                    "status": fields["status"]["name"],
                }
            start += len(data["issues"])
            if not data["issues"] or start >= data["total"]:
                return tasks
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
        # Токен в сообщение не попадает: печатаем только тип и текст ошибки.
        print(f"предупреждение: Jira недоступна ({exc}), статусы взяты из кэша", file=sys.stderr)
        return None


def save_tasks(tasks: dict[str, dict[str, str]]) -> None:
    ordered = {k: tasks[k] for k in sorted(tasks, key=issue_number)}
    new = json.dumps(ordered, ensure_ascii=False, indent=2) + "\n"
    if not TASKS.exists() or TASKS.read_text(encoding="utf-8") != new:
        TASKS.write_text(new, encoding="utf-8")
        print(f"{TASKS.relative_to(ROOT)} обновлён из Jira")


def issue_number(key: str) -> int:
    return int(key.rsplit("-", 1)[1]) if key != NO_TASK else -1


def render(commits: list[dict], tasks: dict[str, dict[str, str]]) -> str:
    by_date: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for c in commits:
        by_date[c["date"]][c["key"]].append(c)

    lines = []
    for date in sorted(by_date, reverse=True):
        lines += [f"## {date}", ""]
        # Внутри даты: новые задачи выше, «Без задачи» — в конце.
        keys = sorted(by_date[date], key=lambda k: (k == NO_TASK, -issue_number(k)))
        for key in keys:
            task = tasks.get(key, {})
            if key == NO_TASK:
                lines += [f"### {NO_TASK}", ""]
            else:
                title = task.get("title")
                lines += [f"### {key} — {title}" if title else f"### {key}"]
                if "status" in task:
                    lines += [f"Статус: {task['status']}", ""]
                else:
                    print(f"предупреждение: нет задачи {key} в {TASKS.name}", file=sys.stderr)
                    lines.append("")
            # Внутри задачи: новые коммиты выше.
            for c in reversed(by_date[date][key]):
                entry = f"- {c['text']}"
                if c["body"]:
                    entry += f". {c['body']}"
                lines.append(entry)
            lines.append("")

    # Задачи из memory_tasks.json, по которым ещё нет коммитов.
    with_commits = {c["key"] for c in commits}
    pending = sorted((k for k in tasks if k not in with_commits), key=issue_number, reverse=True)
    if pending:
        lines += [f"## {NO_COMMITS}", ""]
        for key in pending:
            task = tasks[key]
            lines += [
                f"### {key} — {task.get('title', '')}".rstrip(" —"),
                f"Статус: {task.get('status', '—')}",
                "",
            ]
    return "\n".join(lines).rstrip("\n")


def main() -> int:
    text = MEMORY.read_text(encoding="utf-8")
    if AUTO_START not in text or AUTO_END not in text:
        print(f"ошибка: в {MEMORY} нет маркеров auto:start / auto:end", file=sys.stderr)
        return 1
    head, rest = text.split(AUTO_START, 1)
    _, tail = rest.split(AUTO_END, 1)
    tasks = load_tasks()
    if "--no-jira" not in sys.argv:
        fresh = fetch_jira_tasks()
        if fresh:
            tasks = fresh
            save_tasks(tasks)
    body = render(git_log(), tasks)
    new = f"{head}{AUTO_START}\n\n{body}\n\n{AUTO_END}{tail}"
    if new != text:
        MEMORY.write_text(new, encoding="utf-8")
        print(f"{MEMORY.relative_to(ROOT)} обновлён")
    return 0


if __name__ == "__main__":
    sys.exit(main())
