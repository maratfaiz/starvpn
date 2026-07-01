# CLAUDE.md — STAR VPN Project Rules

> This file defines conventions for AI-assisted development.
> Read this before making any changes to the codebase.

---

## Project Overview

STAR VPN is a Telegram-native VPN service (Bot + Mini App) built on Marzban/Xray-core.
See `ABOUT_PROJECT.md` for the full product specification.

---

## Tech Stack (fixed — do not change without discussion)

| Layer       | Technology                                   |
|-------------|----------------------------------------------|
| Bot         | Python 3.11+, aiogram 3.x, asyncio           |
| DB          | PostgreSQL 16 + SQLAlchemy 2.0 (async)       |
| Migrations  | Alembic                                      |
| VPN core    | Marzban latest + Xray-core                   |
| Protocol    | VLESS + Reality (TLS borrowing)              |
| Frontend    | React 18 + Vite 5 + TailwindCSS 3           |
| TMA SDK     | @tma.js/sdk v2                               |
| Containers  | Docker Compose                               |

---

## Coding Standards

### Python
- Follow **PEP 8**. Max line length: **100** characters.
- All functions that touch I/O must be `async`.
- Type-annotate every function signature.
- Use f-strings, not `.format()` or `%`.
- Never use `print()` in production code — use `logging`.
- Imports order: stdlib → third-party → local. Use `isort`.

### JavaScript / React
- Functional components only. No class components.
- Props must be documented with a short JSDoc comment if non-obvious.
- Use `import.meta.env.VITE_*` for runtime config — never hardcode URLs.
- All user-facing strings must support both Russian and English (i18n-ready).

### SQL / ORM
- Use `AsyncSession` exclusively. No sync sessions.
- Migrations via Alembic — never alter tables manually.
- Index every foreign key and frequently queried column.

---

## Security Rules (non-negotiable)

1. **Zero Logs**: `xray_config.json` must always have `"access": "none"`, `"error": "none"`, `"loglevel": "none"`.
2. **No secrets in code**: all credentials go in `.env`. Never commit `.env`.
3. **Validate all webhook signatures**: Robokassa → MD5 HMAC; Prodamus → SHA-256 HMAC. Reject unsigned requests with HTTP 403.
4. **Telegram initData**: always validate on the backend before trusting user identity.
5. Do not log user IPs, connection metadata, or traffic content anywhere.

---

## Workflow

### Before writing code
1. Understand the task — re-read `ABOUT_PROJECT.md` if needed.
2. Plan in English, one sentence per step.
3. If touching DB schema → write Alembic migration first.

### While writing code
- One logical change per commit.
- Commit message format: `type(scope): short description`
  - Types: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`
  - Example: `feat(bot): add 24h trial activation on /start`

### After writing code
- Run linter: `ruff check bot/` and `eslint webapp/src/`
- Run type checker: `mypy bot/`
- Write or update tests for changed logic.

---

## Project Structure

```
project_root/
├─ bot/
│  ├─ main.py              # Entry point, bot init
│  ├─ config.py            # Pydantic settings (reads .env)
│  ├─ handlers/            # aiogram routers (one file per feature)
│  ├─ models/              # SQLAlchemy ORM models
│  ├─ middlewares/         # aiogram middlewares (DB session, auth)
│  └─ utils/               # Marzban client, DB setup, helpers
├─ webapp/
│  ├─ src/
│  │  ├─ App.jsx           # Root, TMA init
│  │  ├─ components/       # Dashboard, Payment, etc.
│  │  └─ index.css         # Tailwind + glassmorphism utilities
│  ├─ index.html
│  ├─ vite.config.js
│  └─ tailwind.config.js
├─ infra/
│  ├─ docker-compose.yml   # All services
│  ├─ xray_config.json     # VLESS+Reality, Zero Logs
│  └─ deploy.sh            # One-command server setup
├─ .env.example            # Template — copy to .env
└─ CLAUDE.md               # This file
```

---

## Key Business Rules (encode in code, not just comments)

- **Trial**: granted once per `telegram_id`. Field: `User.trial_used`.
- **Referral bonus**: +30 days per every 2 paying referrals. Tracked via `User.extra_days_granted`.
- **Pre-checkout**: `pre_checkout_query` must always be answered within 10 seconds.
- **Marzban username**: always `tg_{telegram_id}` — never change this format.
