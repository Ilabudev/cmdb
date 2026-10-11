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
