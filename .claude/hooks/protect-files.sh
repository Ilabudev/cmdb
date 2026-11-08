#!/usr/bin/env bash
# PreToolUse: блокирует правку защищённых файлов (exit 2 — отказ, причина в stderr).
f=$(jq -r '.tool_input.file_path // empty')
[ -z "$f" ] && exit 0
rel=${f#"$CLAUDE_PROJECT_DIR"/}

deny() { echo "Заблокировано хуком protect-files: $rel — $1" >&2; exit 2; }

case "$rel" in
  .env.example|*/.env.example) ;;  # шаблон можно править
  .env|.env.*|*/.env|*/.env.*) deny "секреты (.env)" ;;
  .git/*) deny "служебный каталог git" ;;
  */.venv/*|.venv/*|*/node_modules/*) deny "зависимости" ;;
  */package-lock.json|package-lock.json) deny "lock-файл (меняется через npm)" ;;
  backend/alembic/versions/*.py)
    # новую ревизию создавать можно, существующие — нет (применённые миграции не редактируются)
    [ -e "$f" ] && deny "существующая миграция Alembic; нужна новая ревизия"
    ;;
esac
exit 0
