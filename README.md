# STAR VPN

Telegram-нативный VPN-сервис на VLESS + Reality (Marzban/Xray-core). Бот, сайт,
Mini App и админка — это **один и тот же backend-процесс**, а не куча
раздельных сервисов. Ниже — как это на самом деле устроено и где что лежит.

Полная бизнес-спецификация — в [`ABOUT_PROJECT.md`](./ABOUT_PROJECT.md).
Правила для разработки (стиль кода, бизнес-правила, чего нельзя ломать) — в
[`CLAUDE.md`](./CLAUDE.md).

---

## Главная идея: всё крутится в одном процессе

```
                         ┌─────────────────────────────┐
                         │   bot/main.py (один процесс) │
                         │                              │
   Telegram ──polling──▶ │  aiogram-бот   +   FastAPI   │ ◀── nginx (443) ── браузер
                         │                (uvicorn:8080) │
                         └───────────────┬──────────────┘
                                         │ читает файлы с диска
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
              landing/*.html       admin/index.html      webapp/app.html
              (сайт, отдаётся        (админка,             (Mini App,
               как есть)            отдаётся как есть)     собранный React)
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
ssh root@<сервер> "cd /opt/starvpn && git pull && systemctl restart starvpn-api starvpn-bot"
# или, если это docker compose:
ssh root@<сервер> "cd /opt/starvpn && git pull && docker compose -f infra/docker-compose.yml restart bot"
```

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
npm install          # один раз
npm run dev           # локальная разработка, http://localhost:5173
npm run build:app     # сборка → webapp/dist/index.html → копия в webapp/app.html
```

После `build:app` нужно закоммитить и запушить **обновившийся
`webapp/app.html`** — именно он открывается по `/app` при запуске без
Docker. `webapp/dist/` в git не попадает (см. `.gitignore`), это чисто
промежуточный артефакт сборки.

Забыть пересборку больше нельзя: CI (`.github/workflows/ci.yml`) собирает
бандл заново и падает, если он разошёлся с закоммиченным `app.html`. А в
production `bot/Dockerfile` собирает Mini App сам (multi-stage), поэтому
образ всегда содержит актуальную версию.

---

## База данных

PostgreSQL 16 + SQLAlchemy 2.0 (async), миграции через Alembic
(`alembic/versions/`). На новом окружении `Base.metadata.create_all()`
в `bot/utils/database.py` создаёт схему сама при первом старте — Alembic
нужен только когда меняешь схему уже существующей боевой базы:

```bash
alembic revision -m "описание"   # создать миграцию
alembic upgrade head              # применить
```

---

## Проверки перед коммитом

```bash
ruff check .                       # линтер Python
pytest                             # тесты
cd webapp && npm run lint          # линтер Mini App
```

То же самое гоняется в CI на каждый push и pull request. Что именно
настроено, какие правила осознанно выключены и какой остался долг по
типам — в `docs/CODE_QUALITY.md`.

---

## Запуск локально

```bash
cp .env.example .env       # заполнить токены/пароли
docker compose -f infra/docker-compose.yml up -d db
python -m bot.main          # бот + API на :8080 в одном процессе
```

Сайт: `http://localhost:8080/`, админка: `http://localhost:8080/admin`,
Mini App: `http://localhost:8080/app` (нужен собранный `webapp/app.html`).

## Деплой на боевой сервер

Полный setup с нуля — `infra/deploy.sh` (ставит Docker, генерирует
Xray Reality-ключи, поднимает `docker compose`). `infra/nginx.conf` —
шаблон реверс-прокси HTTPS → `127.0.0.1:8080`.

**Доступ к серверу по SSH с мака** (вместо браузерной консоли FirstVDS) —
`docs/SERVER_ACCESS.md`. Автоматическая настройка ключа и алиаса `starvpn`:

```bash
bash scripts/mac-setup-ssh.sh    # запускать на маке
ssh starvpn                       # после этого — вход одной командой
```

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
