# STAR VPN

> Telegram-нативный VPN-сервис на **VLESS + Reality** (Marzban/Xray-core).
> Бот, сайт, Mini App и админка — это **один и тот же backend-процесс**,
> а не куча раздельных сервисов. Ниже — как это на самом деле устроено и
> где что лежит.

**Zero Logs** · **Telegram-бот + сайт** · **RU-first** · **Один процесс, не микросервисы**

| Документ | Зачем |
|---|---|
| [`ABOUT_PROJECT.md`](./ABOUT_PROJECT.md) | Полная бизнес-спецификация продукта |
| [`CLAUDE.md`](./CLAUDE.md) | Стиль кода, бизнес-правила, чего нельзя ломать |
| [`AGENTS/new_agent.md`](./AGENTS/new_agent.md) | **Ты агент/ИИ и тебя подключили к проекту? Начни отсюда** |

---

## Главная идея: всё крутится в одном процессе

```
 ┌─────────────────────────────┐
 │ bot/main.py (один процесс) │
 │ │
 Telegram ──polling──▶ │ aiogram-бот + FastAPI │ ◀── nginx (443) ── браузер
 │ (uvicorn:8080) │
 └───────────────┬──────────────┘
 │ читает файлы с диска
 ┌────────────────────┼────────────────────┐
 ▼ ▼ ▼
 landing/*.html admin/index.html webapp/app.html
 (сайт, отдаётся (админка, (Mini App,
 как есть) отдаётся как есть) собранный React)
```

`bot/main.py` запускает **одновременно** (`asyncio.gather`) aiogram-бота
(long polling к Telegram) и uvicorn-сервер FastAPI-приложения из
`bot/api.py` — в одном event loop, одним процессом, одним контейнером
(`bot/Dockerfile`). Отдельного сервера для сайта или API нет: FastAPI сам
читает `.html`-файлы с диска и отдаёт их как есть (`bot/api.py`, функция
`_serve_html`), без шаблонизатора и без билд-степа. Это касается сайта
(`landing/`) и админки (`admin/`) — это обычный HTML/CSS/vanilla JS,
который правится прямо в файле и сразу летит в браузер после рестарта бота.

Mini App (`webapp/`) — исключение: это React-приложение, которое **нужно
собрать** (`npm run build:app`) перед тем, как изменения попадут на сайт —
подробнее в разделе про Mini App ниже.

PostgreSQL и сам бэкенд — единственные компоненты в `docker-compose.yml`.
Marzban (VPN-ядро) разворачивается отдельно, не через compose этого репо.

---

## Карта репозитория

| Путь | Что это | Как деплоится |
|---|---|---|
| `bot/` | Весь backend: aiogram-хендлеры, FastAPI (`api.py`), ORM-модели, бизнес-логика | Docker-контейнер `bot` из `bot/Dockerfile`, рестарт = мгновенно применяет правки |
| `bot/api.py` | FastAPI-приложение: REST API (`/api/*`), админ-API (`/web/*`), раздача HTML-страниц сайта/админки/Mini App | — |
| `bot/handlers/` | aiogram-роутеры бота, один файл — одна фича (payment, devices, referral, gift, admin...) | — |
| `bot/models/` | SQLAlchemy 2.0 async ORM-модели | — |
| `bot/utils/` | Marzban-клиент, Robokassa/ЮMoney/CryptoPay, settings_store (тумблеры оплаты), sub_page (страница подписки в боте) | — |
| `landing/` | **Сайт** — статичные `.html`-файлы, без сборки. Правишь файл → коммит → на сервере `git pull` + рестарт бота | Отдаётся FastAPI напрямую как есть |
| `landing/wiki/` | Статьи базы знаний (Wiki) | — |
| `admin/index.html` | Веб-админка (один файл, ванильный JS, ходит в `/web/*` эндпоинты) | Отдаётся FastAPI напрямую как есть |
| `webapp/` | Telegram Mini App — React 18 + Vite 5 + Tailwind. Исходники в `webapp/src/` | **Требует сборки**, см. ниже |
| `webapp/app.html` | Собранный однофайловый бандл Mini App — именно этот файл реально открывается по `/app` | Коммитится в git, генерируется через `npm run build:app` |
| `alembic/` | Миграции БД (PostgreSQL) | `alembic upgrade head` |
| `infra/` | `docker-compose.yml`, `nginx.conf`, `xray_config.json` (Zero Logs), `deploy.sh` | Конфиги для продакшн-сервера |
| `AGENTS/` | Правила, роли и архитектурная документация для агентов (людей и ИИ), работающих над проектом | См. [`AGENTS/new_agent.md`](./AGENTS/new_agent.md) |
| `.env.example` | Шаблон переменных окружения | Скопировать в `.env`, никогда не коммитить `.env` |

---

## Как редактировать сайт (landing/, admin/)

Это обычные HTML-файлы с инлайновыми `<style>` и `<script>` — открывай,
правь, коммить. Никакого `npm run build` для сайта не нужно.

Маршруты в `bot/api.py` (`serve_landing`, `/tariffs`, `/wiki/{slug}`,
`/account`, `/login`, `/connect`, `/support`, `/get-vpn`, `/privacy`,
`/terms`, `/admin`) читают файл с диска при каждом запросе — значит на
сервере после `git pull` достаточно **рестартнуть бота**, пересборка не
нужна:

```bash
cd /opt/starvpn
git pull
cd infra && docker compose up -d --build
```

> Если менял корневой `.env` — не забудь `cp ../.env .env` в папке
> `infra/` перед пересборкой. `docker-compose.yml` подставляет
> `${POSTGRES_PASSWORD}` и подобные переменные из `.env`, лежащего **в
> той же папке, что и сам compose-файл**, а не из корневого `.env`
> (тот подключается к контейнеру `bot` отдельно, через `env_file`).
> Подробнее — [`AGENTS/roles/devops.md`](./AGENTS/roles/devops.md).

Общий визуальный язык всех страниц: CSS-переменные `--gold #FFB800`,
`--bg #060606`, `--text #EBE0CC`, шрифты Space Grotesk (заголовки) / Inter
(текст) / JetBrains Mono (цифры, код). Иконки — только инлайновые SVG,
без эмодзи (см. `git log` — это чинилось отдельным проходом по всем
страницам).

---

## Как редактировать Mini App (webapp/)

Это единственная часть сайта, которая **не** правится напрямую в
production-файле — исходники в `webapp/src/`, а прод отдаёт уже собранный
`webapp/app.html`.

```bash
cd webapp
npm install # один раз
npm run dev # локальная разработка, http://localhost:5173
npm run build:app # сборка → webapp/dist/index.html → копия в webapp/app.html
```

После `build:app` нужно закоммитить и запушить **обновившийся
`webapp/app.html`** — именно он открывается на сервере по `/app`, а не
`webapp/src/`. `webapp/dist/` в git не попадает (см. `.gitignore`), это
чисто промежуточный артефакт сборки.

---

## База данных

PostgreSQL 16 + SQLAlchemy 2.0 (async), миграции через Alembic
(`alembic/versions/`). На новом окружении `Base.metadata.create_all()`
в `bot/utils/database.py` создаёт схему сама при первом старте — Alembic
нужен только когда меняешь схему уже существующей боевой базы:

```bash
alembic revision -m "описание" # создать миграцию
alembic upgrade head # применить
```

---

## Запуск локально

```bash
cp .env.example .env # заполнить токены/пароли
docker compose -f infra/docker-compose.yml up -d db
python -m bot.main # бот + API на :8080 в одном процессе
```

Сайт: `http://localhost:8080/`, админка: `http://localhost:8080/admin`,
Mini App: `http://localhost:8080/app` (нужен собранный `webapp/app.html`).

## Деплой на боевой сервер

Полный setup с нуля — `infra/deploy.sh` (ставит Docker, генерирует
Xray Reality-ключи, поднимает `docker compose`). `infra/nginx.conf` —
шаблон реверс-прокси HTTPS → `127.0.0.1:8080`.

---

## Для агентов (людей и ИИ)

Если тебя подключили к этому репозиторию как агента (Claude, ChatGPT,
любую ИИ-модель) — **сначала загляни в `AGENTS/`**, там правила входа,
роли и архитектурная документация:

```
STAR VPN
│
├── README.md                    ← ты здесь
│
├── AGENTS/
│   ├── new_agent.md              ← обязательно к прочтению первым
│   ├── Newbie.md                 ← подробная инструкция для первого входа
│   ├── Agents_history.md         ← лог: кто что делал, передача контекста
│   │
│   ├── roles/                    ← инструкция под каждую роль
│   │   ├── designer.md
│   │   ├── frontend.md
│   │   ├── backend.md
│   │   ├── bot.md
│   │   ├── database.md
│   │   ├── devops.md
│   │   └── qa.md
│   │
│   ├── architecture/              ← как всё устроено
│   │   ├── overview.md
│   │   ├── database.md
│   │   └── api.md
│   │
│   └── decisions/
│       └── ADR.md                ← почему сделано именно так, а не иначе
│
├── bot/                          backend + Telegram-бот (один процесс)
├── landing/                      сайт (статичный HTML/CSS/JS)
├── admin/                        веб-админка (статичный HTML/CSS/JS)
├── webapp/                       Telegram Mini App (React, нужна сборка)
├── alembic/                      миграции БД
└── infra/                        Docker Compose, nginx, deploy.sh
```

**TL;DR для нетерпеливых:** прочитай `AGENTS/new_agent.md` → определи
свою роль в `AGENTS/Newbie.md` → сделай задачу → оставь запись в
`AGENTS/Agents_history.md`. Без последнего шага задача не считается
завершённой.

---

## Прочее

- **Zero Logs** — `infra/xray_config.json` всегда должен иметь
 `"access": "none", "error": "none", "loglevel": "none"`. Это не опция,
 а требование из `CLAUDE.md`.
- Payment webhooks (Robokassa/ЮMoney/CryptoPay) проверяют подпись — см.
 `bot/utils/robokassa.py`, `bot/utils/yoomoney.py`, `bot/utils/cryptopay.py`.
- Криптоплатежи скрыты из UI по умолчанию (`bot/utils/settings_store.py`,
 `crypto: False`), но не удалены из кода — админ может включить обратно
 через `/admin` → Настройки.
