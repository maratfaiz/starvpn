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
- **Marzban username**: always `tg_{telegram_id}` for Telegram-identified users — never change this format. Guest/web-only accounts use `web_{id}` instead (established exception, not a violation of this rule).

- **Website account (личный кабинет)**: implemented. Login is standard email + password (`POST /api/account/register` creates the account, hashes the password with bcrypt, and emails a 6-digit verification code; `POST /api/account/verify-email` checks the code and sets `User.email_verified`; `POST /api/account/login` authenticates with email+password thereafter). Verification codes are stored only as a `sha256` hash (`EmailVerificationCode`), with a 45s resend cooldown and a 5-attempt lockout — see `bot/utils/webauth.py`. The old passwordless magic-link flow (`MagicLinkToken`, `GET /account/verify?token=`) was removed (ADR-006 in `AGENTS/decisions/ADR.md`) — don't reintroduce it. `User.telegram_id` stayed `NOT NULL` (not made nullable, unlike the earlier plan) — a web-only account instead gets a synthetic **negative** `telegram_id` (real Telegram IDs are always positive, so there's no collision risk) allocated by `bot.utils.webauth._get_or_create_user_by_email`. This means Device/Payment/GiftNotification/referrals — everything already keyed by `users.telegram_id` — work for web accounts with zero schema/FK changes. Check `user.telegram_id > 0` to know whether a real Telegram account is linked. `/api/me`, `/api/devices*`, `/api/referral`, `/api/card/plans`, `/api/invoice/card`, `/api/yoomoney/plans`, `/api/invoice/yoomoney` all accept **either** `X-Telegram-Init-Data` (Mini App) **or** the `star_session` cookie (web account) via the shared `_resolve_tg_id()` helper in `bot/api.py` — don't add a parallel `/api/account/*` copy of these, extend the shared resolver instead. Schema changes go through Alembic (`alembic/versions/`) — see `0001_baseline.py` / `0002_website_account.py`; `Base.metadata.create_all()` in `bot/utils/database.py` still runs at startup and is fine for brand-new tables/columns, but an *existing* deployed `users` table needs the migration actually applied (`alembic stamp 0001_baseline && alembic upgrade head` once) since `create_all()` never alters existing tables.

- **Website login via Telegram**: implemented as real OIDC (OpenID Connect) against `oauth.telegram.org`, not the classic script-embed Login Widget and not the bot deep-link. `GET /api/telegram-oauth/start` builds a PKCE pair, stores `state.code_verifier` in a short-lived httponly cookie (`tg_oauth_pkce`, scoped to `/api/telegram-oauth`, 10 min), and redirects to Telegram's authorize endpoint; `GET /api/telegram-oauth/callback` exchanges the returned `code` for an `id_token`, verifies its signature against Telegram's JWKS (`bot/utils/telegram_oauth.py`), and gets-or-creates the `User` by the **real positive** `telegram_id` from the token (`webauth.get_or_create_user_by_telegram_id`) before issuing the normal `star_session` cookie. Requires `TELEGRAM_OAUTH_CLIENT_ID`/`TELEGRAM_OAUTH_CLIENT_SECRET` in `.env` (from BotFather's bot → Login Widget settings) and that exact bot's Login Widget must have `{SITE_URL}/api/telegram-oauth/callback` registered as a Redirect URI and `{SITE_URL}` as a Trusted Origin — a login attempt fails until both are registered there. Don't reintroduce the old `telegram-widget.js` script-embed approach or a raw bot-link "login" button — this is the working flow now.

- **Admin panel auth (`/admin`)**: per-account login/password, not a single shared secret. `AdminAccount` has `rank` ∈ {`admin`, `worker`}; only `admin` has a personal `invite_key` it can hand out (`worker` cannot invite anyone). `ADMIN_WEB_KEY` in `.env` still exists but is now the **master key** used only once, to register the very first `admin` account (`POST /web/register`) — every account after that registers via some existing `admin`'s personal invite_key. Sessions are still a bearer token in `Authorization` (not a cookie), kept in an in-memory dict warmed from the `admin_sessions` table at process start (`bot/utils/admin_auth.py`, ADR-009) — this is what let ~26 existing `_web_auth()` call sites in `bot/api.py` stay synchronous and unchanged. Don't add a second parallel admin-login mechanism — extend `admin_auth.py`.

- **Payment methods (2026-08-30, ADR-012)**: ALL payment methods are toggled off right now — card (Robokassa), ЮMoney, crypto (CryptoPay), and Telegram Stars, all `False` in `bot/utils/settings_store.py` `_DEFAULT_ENABLED`. The only way to get a subscription at the moment is the free 2-day trial. This is a toggle, not a code deletion — flip any of them back on from `/admin` → Настройки, no deploy needed. Don't remove `card_payment.py`/`crypto_payment.py`/`yoomoney_payment.py`/the Stars invoice code because they "look unused". Because "zero providers enabled" turned out to be a real state and not just a hypothetical, `bot/handlers/profile.py::pay_choice_text()` and `landing/get-vpn.html`'s `loadProviders()` both explicitly handle it (clear "payment unavailable" messaging instead of a confusing empty picker or a button that fails silently) — keep that handling if you touch either.

- **Gift by link (2026-08-30, ADR-011)**: the website gift flow (`/account` → "Подарить", `POST /api/gift/invoice`, card/YooMoney only) has a second delivery mode alongside the original "know the recipient's @username" one — leave `recipient` blank and it creates a shareable `{SITE_URL}/gift/{code}` link instead (`landing/gift-reveal.html`, tracked via `Payment.gift_link_code`/`Payment.gift_claimed`). The recipient is unknown at payment time, so `Payment.telegram_id` (NOT NULL + FK) is temporarily set to the sender's own ID as a placeholder — `handle_card_webhook`/`handle_yoomoney_webhook` skip `_grant_subscription` entirely when `gift_link_code` is set, and `POST /api/gift/link/{code}/claim` (auth required via `_resolve_tg_id`) is what actually grants the subscription and rewrites `telegram_id` to the claimant. Stars/crypto gifting in `bot/handlers/gift.py` does **not** have link delivery — only the site's card/YooMoney gift path does.
