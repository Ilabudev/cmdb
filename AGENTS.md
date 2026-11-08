# CMDB

Учёт ИТ-инфраструктуры: CI, связи, граф зависимостей, анализ влияния.
Требования с нумерацией FR/NFR — [docs/requirements.md](docs/requirements.md); ссылайся на номера
в коде (`# TODO(FR-6): ...`) и при обсуждении задач. 
Сценарии приемки в [docs/scenarios.md](docs/scenarios.md);
Структура и запуск — [README.md](README.md).

## Команды

```bash
# backend/ (из активированного .venv)
pytest                                   # тесты
ruff check . && ruff format --check .    # линтер
alembic revision --autogenerate -m "..." # новая миграция
alembic upgrade head && python -m app.seed
uvicorn app.main:app --reload            # CMDB_AUTH_DISABLED=true — без Keycloak

# frontend/
npm run dev | npm run build | npm run gen:api   # gen:api — типы из OpenAPI бэкенда
```

## Ключевые решения — не нарушать

- **Направление связи:** `source → target` = «source зависит от target».
  `downstream` — от чего зависит CI, `upstream` — что зависит от CI (анализ влияния).
- **ИС:** CI типа `information_system`. Каждый CI (кроме ИС) входит ровно в одну ИС через `member_of`
  (частичный уникальный индекс), создаётся только внутри ИС, переноса между ИС нет; ИС с живыми CI
  не удаляется. Инфраструктура — в служебных ИС (`kind=infrastructure`).
- **Сетевые правила:** связь `network_flow` (`vm → vm`), одна на пару ВМ, правила в `attributes.rules[]`
  (`protocol`, `port`, `description`, `source`). Ключ правила — (`protocol`, `port`). Пустой `rules[]` недопустим.
- **Шаблоны:** `relation_templates` + неизменяемые версии; применение по явному списку CI, ссылка на
  шаблон — в самом правиле (`template_id`, `template_version`); шаблон с ссылками не удаляется.
- **Импорт:** два вида (ВМ, сетевые взаимодействия), файл = одна ИС, построчно (подтранзакция на строку),
  общий `import_id`, dry-run по умолчанию, ключ — DNS-имя (`name` ВМ).

## Соглашения

- Правила для кода бэкенда (async, атрибуты, аудит, мягкое удаление, права, граф, API, сид) —
  в [.claude/rules/backend.md](.claude/rules/backend.md); подгружаются при работе с `backend/app/**/*.py`.
- Применённые миграции не редактировать — только новая ревизия.
- Фронтенд: данные через TanStack Query, HTTP только через `src/api/client.ts`.
- Вопросы по библиотекам и фреймворкам (API, настройка, миграция версий) — через MCP context7,
  а не по памяти.

## Коммиты и Jira

- Заголовок каждого коммита начинается с ключа задачи Jira (проект CMDB), затем conventional commit:
  `CMDB-3 chore: начальный каркас проекта`. Тип (`feat`, `fix`, `chore`…) — английский, описание — русское.
- Не добавлять в сообщение коммита строку `Co-Authored-By` (в том числе про Claude).
- Нет подходящей задачи — сначала завести её, не коммитить без ключа.
- После каждого коммита (и push) добавить в ту же задачу комментарий (`jira_add_comment`) с хешем
  коммита и полным текстом сообщения.
- При завершении задачи в комментарий к задаче Jira класть итоговое резюме по выполнению

## Текущее состояние

- Первая миграция Alembic ещё не создана (`alembic/versions/` пуст); в неё войдут `cis.itsm_key`,
  `relations.attributes`, `relation_types.attribute_schema`, `is_editors`, шаблоны, `audit_events.import_id`.
- Код модели ещё не приведён к требованиям v0.2 (тип ИС, `network_flow`, перечень УЗ, шаблоны, импорт).
- Импорт/экспорт (`api/v1/transfer.py`) — только контракт, отвечает 501.
- Страницы фронтенда — заглушки.
- Принятые решения — раздел 8 требований и [docs/scenarios.md](docs/scenarios.md); открытые вопросы — раздел 9.
