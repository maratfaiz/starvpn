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

- **Device names (2026-08-30)**: `Device.name` is NOT a user-facing name — it's the internal platform-type key (`ios`/`android`/`macos`/`windows`/`linux`/`appletv`/`androidtv`), used for icon lookup and the default VLESS remark. The actual user-given name lives in `Device.custom_name` (migration `0013_device_custom_name`, nullable — devices created via the bot's own `/устройства` flow, `bot/handlers/devices.py`, don't set it and fall back to the type-based label same as before). `PATCH /api/devices/{id}` renames a device at any time; `POST /api/devices` accepts an optional `name` at creation. Both `GET /api/devices` and `GET /api/devices/{id}/link` return `custom_name`, and when set, it's used (via `bot.utils.branding.set_vless_remark_text`) as the VLESS remark instead of the generic type label — so a custom name shows up in Happ/v2rayNG too, not just the website's device list. The website's add-device flow (`landing/account.html`) is two-step: pick a specific platform (now split into Телефон/Планшет/Компьютер/Телевизор categories, several of which map to the same underlying type — e.g. iPhone and iPad both create an `ios` device), then name it on a second screen pre-filled with that platform's label.

- **Website account (личный кабинет)**: implemented. Login is standard email + password (`POST /api/account/register` creates the account, hashes the password with bcrypt, and emails a 6-digit verification code; `POST /api/account/verify-email` checks the code and sets `User.email_verified`; `POST /api/account/login` authenticates with email+password thereafter). Verification codes are stored only as a `sha256` hash (`EmailVerificationCode`), with a 45s resend cooldown and a 5-attempt lockout — see `bot/utils/webauth.py`. The old passwordless magic-link flow (`MagicLinkToken`, `GET /account/verify?token=`) was removed (ADR-006 in `AGENTS/decisions/ADR.md`) — don't reintroduce it. `User.telegram_id` stayed `NOT NULL` (not made nullable, unlike the earlier plan) — a web-only account instead gets a synthetic **negative** `telegram_id` (real Telegram IDs are always positive, so there's no collision risk) allocated by `bot.utils.webauth._get_or_create_user_by_email`. This means Device/Payment/GiftNotification/referrals — everything already keyed by `users.telegram_id` — work for web accounts with zero schema/FK changes. Check `user.telegram_id > 0` to know whether a real Telegram account is linked. `/api/me`, `/api/devices*`, `/api/referral`, `/api/card/plans`, `/api/invoice/card`, `/api/crypto/plans`, `/api/invoice/crypto` all accept **either** `X-Telegram-Init-Data` (Mini App) **or** the `star_session` cookie (web account) via the shared `_resolve_tg_id()` helper in `bot/api.py` — don't add a parallel `/api/account/*` copy of these, extend the shared resolver instead. Schema changes go through Alembic (`alembic/versions/`) — see `0001_baseline.py` / `0002_website_account.py`; `Base.metadata.create_all()` in `bot/utils/database.py` still runs at startup and is fine for brand-new tables/columns, but an *existing* deployed `users` table needs the migration actually applied (`alembic stamp 0001_baseline && alembic upgrade head` once) since `create_all()` never alters existing tables.

- **Website login via Telegram**: implemented as real OIDC (OpenID Connect) against `oauth.telegram.org`, not the classic script-embed Login Widget and not the bot deep-link. `GET /api/telegram-oauth/start` builds a PKCE pair, stores `state.code_verifier` in a short-lived httponly cookie (`tg_oauth_pkce`, scoped to `/api/telegram-oauth`, 10 min), and redirects to Telegram's authorize endpoint; `GET /api/telegram-oauth/callback` exchanges the returned `code` for an `id_token`, verifies its signature against Telegram's JWKS (`bot/utils/telegram_oauth.py`), and gets-or-creates the `User` by the **real positive** `telegram_id` from the token (`webauth.get_or_create_user_by_telegram_id`) before issuing the normal `star_session` cookie. Requires `TELEGRAM_OAUTH_CLIENT_ID` (the bot's numeric ID) / `TELEGRAM_OAUTH_CLIENT_SECRET` in `.env` (BotFather → bot → Bot Settings → Login Widget) with `{SITE_URL}/api/telegram-oauth/callback` in its Redirect URIs and `{SITE_URL}` in its Trusted Origins. Every failure redirects to `/login?tg_error=<code>` (never a bare error page), and `/admin` → Настройки shows the exact URLs to register plus the last login error (`telegram_oauth.last_error`). `aud` is checked manually (it may be numeric) and the Telegram ID comes only from the `id` claim — `sub` is an opaque OIDC id, never use it as `telegram_id`. Don't reintroduce the old `telegram-widget.js` script-embed approach or a raw bot-link "login" button — this is the working flow now.

- **Admin panel auth (`/admin`)**: per-account login/password, not a single shared secret. `AdminAccount` has `rank` ∈ {`admin`, `worker`}; only `admin` has a personal `invite_key` it can hand out (`worker` cannot invite anyone). `ADMIN_WEB_KEY` in `.env` still exists but is now the **master key** used only once, to register the very first `admin` account (`POST /web/register`) — every account after that registers via some existing `admin`'s personal invite_key. Sessions are still a bearer token in `Authorization` (not a cookie), kept in an in-memory dict warmed from the `admin_sessions` table at process start (`bot/utils/admin_auth.py`, ADR-009) — this is what let ~26 existing `_web_auth()` call sites in `bot/api.py` stay synchronous and unchanged. Don't add a second parallel admin-login mechanism — extend `admin_auth.py`.

- **Payment methods (2026-08-30, ADR-015)**: card (Robokassa), crypto (CryptoPay) and Telegram Stars are ON. The second RUB-rail provider that used to sit next to card is **fully removed from the codebase** — not toggled off, deleted: its handler file, its `bot/utils/` client module, its two API endpoints (`plans`/`invoice`) and its webhook route, its `PROVIDER_KEYS`/`_DEFAULT_ENABLED` entry, its config fields and `.env.example` lines, its admin-panel toggle row and payment-method chip, its button in `bot/handlers/profile.py`'s pay-choice keyboard, its branch in `/api/gift/invoice` and `/api/guest/checkout` — all gone, not hidden. `bot/utils/settings_store.py` `_DEFAULT_ENABLED` now only has three keys: `card`, `crypto`, `stars` (all `True`). Do NOT reintroduce this provider by any name, in code or in copy anywhere on the site — this was an explicit, emphatic user instruction ("убери отовсюду ЛЮБОЕ упоминание"), not just a toggle flip; if a second RUB rail is ever wanted again it needs to be built from scratch (webhook signature verification, Quickpay-equivalent URL builder, admin toggle, guest-checkout branch — all of it), not resurrected from git history. A `Payment.payment_method` column can still historically contain that old provider's string in rows predating this removal — that's just data, the admin payments table (`admin/index.html`) falls back to a plain `—` chip for any method it doesn't recognize, so old rows still render fine. Because "zero providers enabled" turned out to be a real state at one point, `bot/handlers/profile.py::pay_choice_text()` and `landing/get-vpn.html`'s payment step both explicitly handle it. Crypto payment (via @CryptoBot) always requires Telegram regardless of how the account was created — that's a CryptoPay constraint, not ours; card is the only truly Telegram-independent method. Telegram Stars (XTR) is bot-only by nature — there's no `/api/invoice/stars`, it can't exist as a site checkout option since Stars payments only render inside the Telegram client, not a website form; the `payment` wiki article's comparison table (now in the DB, see Wiki below) reflects this with a `—` in the "На сайте" column. Site-based invoice creation (`/api/invoice/card`, `/api/invoice/crypto`, mirrored by `/api/card/plans`/`/api/crypto/plans`) only supports the 3 fixed plan tiers — no custom-day pricing (that only exists in the guest-checkout path, see below).

- **`/get-vpn` requires registration (2026-08-30, ADR-013)**: resolves the previously-open question in `AGENTS/architecture/purchase-flow.md`. The page is now a 3-step flow — Тариф → Аккаунт → Оплата — where the payment step is behind `.locked`/`pointer-events:none` until `GET /api/me` confirms a session; it no longer uses `/api/guest/*` at all (that guest-checkout backend, `GuestOrder`, and `card-success.html`'s `pollGuestOrder` still exist and work, just aren't linked from this page anymore — don't assume they're dead code). Custom-duration purchases (the `?days=N` slider from `tariffs.html`) were dropped in this redesign since the authenticated invoice endpoints don't support arbitrary day counts. Before bouncing to `/login` or `/api/telegram-oauth/start`, the chosen plan key is saved to `localStorage['star_vpn_pending_purchase']`; since both auth flows hard-redirect to `/account` (left untouched — auth code), `account.html::boot()`'s `resumePendingPurchase()` picks that key up and switches to the "Продление" tab with the plan pre-selected, rather than routing back to `/get-vpn`. `card-success.html` was `telegramState()`-only (assumed every purchaser has Telegram) — renamed to `accountState()` and now checks `/api/me` for `telegram_id <= 0` to show "open your account" instead of "return to the Telegram bot" for web-only accounts; this affects every non-bot purchase, not just this new page.

- **Gift by link (2026-08-30, ADR-011; card-only since ADR-015)**: the website gift flow (`/account` → "Подарить", `POST /api/gift/invoice`, card only — the second provider it originally also supported was removed in ADR-015) has a second delivery mode alongside the original "know the recipient's @username" one — leave `recipient` blank and it creates a shareable `{SITE_URL}/gift/{code}` link instead (`landing/gift-reveal.html`, tracked via `Payment.gift_link_code`/`Payment.gift_claimed`). The recipient is unknown at payment time, so `Payment.telegram_id` (NOT NULL + FK) is temporarily set to the sender's own ID as a placeholder — `handle_card_webhook` skips `_grant_subscription` entirely when `gift_link_code` is set, and `POST /api/gift/link/{code}/claim` (auth required via `_resolve_tg_id`) is what actually grants the subscription and rewrites `telegram_id` to the claimant. Stars/crypto gifting in `bot/handlers/gift.py` does **not** have link delivery — only the site's card gift path does.

- **Wiki lives in the DB (2026-09-25, ADR-017)**: there are no static article files anymore — `landing/wiki/` only holds templates (`_article.html` for an article page, `index.html` for `/wiki` with a `__WIKI_GROUPS__` marker). Every article is a `WikiArticle` row (`content_html`, `custom_css`, `short_title`, `sort_order`; migration `0014_wiki_rich_content` converted old markdown bodies and dropped `body`) and is edited in `/admin` → Wiki (WYSIWYG in an iframe with the site's CSS + HTML mode + preview). The 11 original articles are seeded **once** from `bot/data/wiki_seed.json` on startup (`bot.utils.wiki_page.seed_wiki_articles`, guarded by `app_settings.wiki_seeded`) — deleting them in the admin is permanent, don't re-add a "restore on start". Other pages link to `/wiki/install-ios` etc.; those links 404 if the owner deletes the article, which is accepted. Interactive widgets (FAQ/case accordions, FAQ search, client tabs, source picker) are generic JS in `_article.html` that activates on matching markup.

- **Bot editor (2026-09-25, ADR-018)**: `/admin` → Бот. Every user-facing text/button of the main bot screens goes through `bot.utils.bot_texts.t("key", **placeholders)`; reply-keyboard handlers use `MenuText("btn.x")` (matches the current label **and** the default, so old keyboards keep working). Defaults in `TEXTS` must stay byte-identical to what the bot says without overrides. Overrides (`BotText`) and custom blocks (`BotBlock`: text + buttons → block / screen / URL, optional main-menu button and `/command`) are cached in-process (`load_cache` at startup, reloaded on every admin save) — works because bot and API share one process, same as `admin_auth`. When adding a new bot text, add it to `TEXTS` **and** to a screen in `SCREENS`, otherwise the admin can't see it. Devices, gift, card/crypto flows are intentionally "code" nodes — not editable.

- **Audit rules (2026-09-25, ADR-019)** — invariants that were broken before and must stay fixed:
  - Subscription links are signed: `/sub/{marzban_username}/{sig}` (`bot.utils.branding.subscription_url` / `check_sub_signature`). Marzban usernames are guessable (`ios_tg_<@username>`), so the unsigned `/sub/{username}` route returns 404 unless `SUB_ALLOW_UNSIGNED=true`. Always build links via `subscription_url()`.
  - Never send a VLESS link to a third party — QR codes are rendered locally (`bot.utils.qr.qr_data_uri` / `make_qr_photo`), not via api.qrserver.com.
  - Any grant of days (payment, gift, trial, admin grant, referral bonus) goes through `bot.handlers.payment._grant_subscription`: it adds days on top of the current expiry and re-activates Marzban users (the scheduler disables them on expiry). Don't set `subscription_expires_at` by hand.
  - Ban/unban act on **all** of the user's Marzban users via `bot.utils.vpn_access.set_vpn_enabled` (devices + legacy account). Creating a device uses `marzban.provision_user` (re-activates an existing, previously deleted device user instead of returning a disabled one).
  - `User.referral_count` = number of **paying** referrals; only `_credit_referral` increments it (card, crypto and Stars payments all call it). `/start ref<id>` only sets `referrer_id` (migration `0016` recomputed old inflated values).
  - Payment webhooks mark the payment paid atomically (`UPDATE … WHERE status='pending'`) before granting — retries/duplicates must not grant twice. Same for gift-link claims.
  - Pages are authored with `@starisvpnbot` / `@hashprojects`; `bot.utils.branding.brand_html` swaps them for `BOT_USERNAME` / `SUPPORT_USERNAME` when serving — keep new pages on the same placeholders and serve them via `_serve_html`.

