# CMDB

Учёт ИТ-инфраструктуры: конфигурационные единицы (серверы, ВМ, сети, ПО), связи между ними,
граф зависимостей и анализ влияния.

Требования: [docs/requirements.md](docs/requirements.md)

## Структура

```
backend/            FastAPI + SQLAlchemy 2 (async) + Alembic
  app/
    api/v1/         REST-эндпоинты: ci-types, cis, relations, audit, import/export
    core/           настройки, БД, OIDC-авторизация и роли
    models/         ORM: CIType, CI, RelationType, Relation, AuditEvent
    schemas/        Pydantic DTO
    services/       валидация атрибутов, аудит, обход графа
    seed.py         встроенные типы CI и связей
  alembic/          миграции
  tests/
frontend/           React + TypeScript + Vite + Mantine
  src/
    api/            fetch-клиент (типы генерируются из OpenAPI)
    auth/           OIDC (oidc-client-ts)
    pages/          экраны: список CI, карточка, импорт, история, типы
    components/     CIGraph (Cytoscape.js)
deploy/keycloak/    realm для разработки (роли и тестовые пользователи)
docs/               требования и проектные решения
```

## Запуск через Docker Compose

```bash
docker compose up --build
```

- UI: http://localhost:3000
- API и Swagger: http://localhost:8000/docs
- Keycloak: http://localhost:8080 (admin/admin)

Тестовые пользователи: `admin/admin`, `editor/editor`, `viewer/viewer`.

## Локальная разработка

Бэкенд (нужен `python3.12-venv`):

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
docker compose up -d db keycloak
alembic revision --autogenerate -m init   # только первый раз
alembic upgrade head && python -m app.seed
uvicorn app.main:app --reload
pytest
```

Для работы без Keycloak: `CMDB_AUTH_DISABLED=true` — все запросы выполняются от `dev` с ролью admin.

Фронтенд:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev        # http://localhost:5173, /api проксируется на :8000
```

## Работа ИИ-агента (Claude Code)

Конфигурация агента лежит в репозитории и действует для всех, кто работает с проектом.

### Инструкции

| Файл | Назначение |
|---|---|
| [AGENTS.md](AGENTS.md) | Правила для агента: команды, ключевые архитектурные решения, соглашения, формат коммитов и работа с Jira. `CLAUDE.md` лишь импортирует его |
| [.claude/rules/backend.md](.claude/rules/backend.md) | Правила для кода бэкенда (async, атрибуты, аудит, мягкое удаление, права, граф, API, сид). Path-scoped: подгружаются, только когда агент читает или правит `backend/app/**/*.py`, поэтому не занимают контекст в остальное время |
| [docs/requirements.md](docs/requirements.md) | Требования FR/NFR; номера указываются в коде (`# TODO(FR-6): ...`) |
| [docs/scenarios.md](docs/scenarios.md) | Сценарии приёмки |
| Личные настройки | `~/.claude/CLAUDE.md` и `.claude/settings.local.json` (не в git) |

Локальный `AGENTS.md` приоритетнее личных глобальных инструкций. Вопросы по библиотекам агент
решает через MCP context7, а не по памяти.

### Режим и права

Режим по умолчанию — `default`: `defaultMode` не задан, всё, чего нет в списках ниже, агент
выполняет только после подтверждения. Правила задаёт [.claude/settings.json](.claude/settings.json).

| Тип | Правило |
|---|---|
| Разрешено без вопросов | `ruff check`, `ruff format --check` (в том числе через `.venv/bin/`) |
| Спрашивает | `git push` |
| Запрещено | `rm -rf` и его перестановки флагов (`-fr`, `-r -f`, `-f -r`) |

Подключённые MCP-серверы: `context7` и `jira` (пользовательский уровень), `playwright`
(проектный, [.mcp.json](.mcp.json): headless Chromium; включается в `settings.local.json` через
`enabledMcpjsonServers`).

### Страховки (хуки)

- **`PreToolUse` → [protect-files.sh](.claude/hooks/protect-files.sh)** блокирует правку через
  Edit/Write: `.env` и `.env.*` (кроме `.env.example`), `.git/`, `.venv/`, `node_modules/`,
  `package-lock.json` и существующих миграций Alembic. Новую ревизию создавать можно.
- **`PostToolUse`** после правки `backend/**/*.py` запускает `ruff format` и `ruff check`;
  замечания линтера возвращаются агенту, и он исправляет их сам.

Хуки защищают только инструменты правки файлов. Команды в Bash они не проверяют, поэтому
деструктивные действия ограничены правилами `deny`/`ask` выше.

### Тесты и проверка

- Перед сдачей работы агент прогоняет `pytest` и `ruff check . && ruff format --check .` (backend),
  `npm run build` (frontend). Если проверка невозможна, он сообщает об этом явно.
- Skill [e2e-before-commit](.claude/skills/e2e-before-commit/SKILL.md) перед каждым `git commit`
  запускает Playwright e2e (`frontend/e2e/`) и разрешает коммит только при зелёном прогоне.
  Исключения: коммит затрагивает только `docs/**`, `*.md`, `.claude/**` или `.gitignore`,
  либо пользователь явно сказал «без e2e». Упавшие или не запустившиеся тесты агент не обходит:
  он называет причину и спрашивает, что делать.
- Агенту запрещено ослаблять тесты (`skip`/`fixme`, правка конфига) ради зелёного прогона.

### Коммиты и Jira

- Заголовок: `CMDB-N type: описание` (ключ Jira, затем conventional commit; тип — английский,
  описание — русское). Нет подходящей задачи — сначала завести её.
- Строка `Co-Authored-By` в сообщение не добавляется.
- После коммита и push агент добавляет в задачу комментарий с хешем и полным текстом сообщения;
  при завершении задачи — итоговое резюме.
- `git push` всегда требует подтверждения. Force push в main/master — только с явного согласия.

### Журнал изменений

[docs/memory.md](docs/memory.md) генерируется из истории git скриптом
[scripts/update_memory.py](scripts/update_memory.py); вручную его не правят. Хук
[.githooks/pre-commit](.githooks/pre-commit) перед каждым коммитом обновляет журнал и добавляет его в коммит.

- Включить хуки (один раз после клонирования): `git config core.hooksPath .githooks`.
- Запись о создаваемом коммите появляется в журнале со следующим коммитом.
- Название и статус задач берутся из Jira (источник правды): нужна переменная окружения `JIRA_PERSONAL_TOKEN`
  (и `JIRA_URL`, если адрес отличается от `https://jira.ilabudev.ru`). Без токена или при недоступной Jira
  используется кэш [scripts/memory_tasks.json](scripts/memory_tasks.json), коммит не блокируется.
- Причину изменения пишите в теле сообщения коммита: оно попадает в журнал как есть.
