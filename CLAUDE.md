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
3. **Validate all webhook signatures**: CryptoPay → HMAC-SHA256 (`bot/utils/cryptopay.py`); a future card provider must verify its own signature before granting anything. Reject unsigned requests.
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
- Write or update tests for changed logic: `pip install -r tests/requirements.txt && pytest` (SQLite + fake Marzban, see `tests/conftest.py`).

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

- **Trial**: granted once per **real** `telegram_id` (`> 0`); can be switched off and its length changed in `/admin` → Настройки (`app_config.trial_enabled()` / `trial_days()` — not `settings.trial_days`). Field: `User.trial_used`. Email-only web accounts (synthetic negative ids) can't activate it — `/api/trial` returns 403 — otherwise every new email was a new free trial (ADR-021).
- **Referral bonus**: +N days per every M paying referrals (default 30 / 2, editable — `app_config.referral_bonus_days()` / `referral_milestone()`). Tracked via `User.extra_days_granted`.
- **Pre-checkout**: `pre_checkout_query` must always be answered within 10 seconds.
- **Marzban username**: every new device gets a readable `{nick}_{type}{n}_{telegram_id}` — e.g. `ivan_iphone_123456789`, a second iPhone `ivan_iphone2_123456789`, web-only accounts end in `_w{-telegram_id}` — from `bot.handlers.devices.new_device_mz_username` (nick = @username, else transliterated first name, else email local part; type from `_MZ_TYPE`; ≤32 chars, `[a-z0-9_]`). The id at the end makes it globally unique even if the @username is later taken by someone else; `n` never repeats any of the user's devices, including deleted ones (ADR-021, ADR-022). The Marzban `note` is human-readable too (`device_mz_note`: «@ivan · iPhone / iPad · слот 1 · tg 123 · бот»). Existing devices keep their old names (`tg_{id}_d{n}`, `{type}_tg_{username}`, legacy `tg_{telegram_id}`, guest `web_{public_id[:8]}`) — never rename them, their keys would break.

- **Device names (2026-08-30)**: `Device.name` is NOT a user-facing name — it's the internal platform-type key (`ios`/`android`/`macos`/`windows`/`linux`/`appletv`/`androidtv`), used for icon lookup and the default VLESS remark. The actual user-given name lives in `Device.custom_name` (migration `0013_device_custom_name`, nullable — devices created via the bot's own `/устройства` flow, `bot/handlers/devices.py`, don't set it and fall back to the type-based label same as before). `PATCH /api/devices/{id}` renames a device at any time; `POST /api/devices` accepts an optional `name` at creation. Both `GET /api/devices` and `GET /api/devices/{id}/link` return `custom_name`, and when set, it's used (via `bot.utils.branding.set_vless_remark_text`) as the VLESS remark instead of the generic type label — so a custom name shows up in Happ/v2rayNG too, not just the website's device list. The website's add-device flow (`landing/account.html`) is two-step: pick a specific platform (now split into Телефон/Планшет/Компьютер/Телевизор categories, several of which map to the same underlying type — e.g. iPhone and iPad both create an `ios` device), then name it on a second screen pre-filled with that platform's label.

- **Website account (личный кабинет)**: implemented. Login is standard email + password (`POST /api/account/register` creates the account, hashes the password with bcrypt, and emails a 6-digit verification code; `POST /api/account/verify-email` checks the code and sets `User.email_verified`; `POST /api/account/login` authenticates with email+password thereafter; `POST /api/account/forgot-password` + `/reset-password` reset it with the same kind of emailed code and close the user's other web sessions). Verification codes are stored only as a `sha256` hash (`EmailVerificationCode`), with a 45s resend cooldown and a 5-attempt lockout — see `bot/utils/webauth.py`. The old passwordless magic-link flow (`MagicLinkToken`, `GET /account/verify?token=`) was removed (ADR-006 in `AGENTS/decisions/ADR.md`) — don't reintroduce it. `User.telegram_id` stayed `NOT NULL` (not made nullable, unlike the earlier plan) — a web-only account instead gets a synthetic **negative** `telegram_id` (real Telegram IDs are always positive, so there's no collision risk) allocated by `bot.utils.webauth._get_or_create_user_by_email`. This means Device/Payment/GiftNotification/referrals — everything already keyed by `users.telegram_id` — work for web accounts with zero schema/FK changes. Check `user.telegram_id > 0` to know whether a real Telegram account is linked. `/api/me`, `/api/devices*`, `/api/referral`, `/api/card/plans`, `/api/invoice/card`, `/api/crypto/plans`, `/api/invoice/crypto` all accept **either** `X-Telegram-Init-Data` (Mini App) **or** the `star_session` cookie (web account) via the shared `_resolve_tg_id()` helper in `bot/api.py` — don't add a parallel `/api/account/*` copy of these, extend the shared resolver instead. Schema changes go through Alembic (`alembic/versions/`) — see `0001_baseline.py` / `0002_website_account.py`; `Base.metadata.create_all()` in `bot/utils/database.py` still runs at startup and is fine for brand-new tables/columns, but an *existing* deployed `users` table needs the migration actually applied (`alembic stamp 0001_baseline && alembic upgrade head` once) since `create_all()` never alters existing tables.

- **Website login via Telegram**: implemented as real OIDC (OpenID Connect) against `oauth.telegram.org`, not the classic script-embed Login Widget and not the bot deep-link. `GET /api/telegram-oauth/start` builds a PKCE pair, stores `state.code_verifier` in a short-lived httponly cookie (`tg_oauth_pkce`, scoped to `/api/telegram-oauth`, 10 min), and redirects to Telegram's authorize endpoint; `GET /api/telegram-oauth/callback` exchanges the returned `code` for an `id_token`, verifies its signature against Telegram's JWKS (`bot/utils/telegram_oauth.py`), and gets-or-creates the `User` by the **real positive** `telegram_id` from the token (`webauth.get_or_create_user_by_telegram_id`) before issuing the normal `star_session` cookie. Requires `TELEGRAM_OAUTH_CLIENT_ID` (the bot's numeric ID) / `TELEGRAM_OAUTH_CLIENT_SECRET` in `.env` (BotFather → bot → Bot Settings → Login Widget) with `{SITE_URL}/api/telegram-oauth/callback` in its Redirect URIs and `{SITE_URL}` in its Trusted Origins. Every failure redirects to `/login?tg_error=<code>` (never a bare error page), and `/admin` → Настройки shows the exact URLs to register plus the last login error (`telegram_oauth.last_error`). `aud` is checked manually (it may be numeric) and the Telegram ID comes only from the `id` claim — `sub` is an opaque OIDC id, never use it as `telegram_id`. Don't reintroduce the old `telegram-widget.js` script-embed approach or a raw bot-link "login" button — this is the working flow now.

- **Admin panel auth (`/admin`)**: per-account login/password, not a single shared secret. `AdminAccount` has `rank` ∈ {`admin`, `worker`}; only `admin` has a personal `invite_key` it can hand out (`worker` cannot invite anyone). `ADMIN_WEB_KEY` in `.env` still exists but is now the **master key** used only once, to register the very first `admin` account (`POST /web/register`) — every account after that registers via some existing `admin`'s personal invite_key. Sessions are still a bearer token in `Authorization` (not a cookie), kept in an in-memory dict warmed from the `admin_sessions` table at process start (`bot/utils/admin_auth.py`, ADR-009) — this is what let ~26 existing `_web_auth()` call sites in `bot/api.py` stay synchronous and unchanged. Don't add a second parallel admin-login mechanism — extend `admin_auth.py`.
  **Roles (ADR-020):** a `worker` sees only the sections of its `AdminRole` (`sections` = comma-separated keys from `admin_auth.SECTIONS`) plus `dash`/`profile`; `admin` rank sees everything plus `staff` (team management). Every new `/web/*` endpoint must call `_web_auth(authorization, "<section>")` with the right section — the sidebar only hides things, the server is what enforces it. Deactivated accounts (`is_active=False`) are rejected at login and by `check_session`.

- **Uploaded images (ADR-020)**: stored in the DB (`MediaFile`), served at `/media/{id}`, referenced as `media:<id>` (bot images) or `/media/<id>` (wiki/banner HTML). Only PNG/JPEG/GIF/WebP, sniffed from bytes by `bot.utils.media.save_image` — never allow SVG. Bot screens with an image go through `bot.utils.bot_media.send_screen` (photo + caption, falls back to text); a key must be in `bot_texts.IMAGE_KEYS` to accept an image.

- **Banner (ADR-020)**: icons and colour styles live only in `bot/utils/banner.py` — the site and admin read them from `/api/ad-banner` / `/web/ad-banner`, don't add JS copies. `version` (= `updated_at`) drives the visitor's "closed" state, so the view/click counters must not bump `updated_at`. `link_url` must pass `banner.valid_link` (https:// or a site path).

- **Editable settings (2026-10-08, ADR-022)**: `/admin` → Настройки edits prices (⭐ / $ / ₽ per plan), trial on/off + length, devices per account, referral bonus, payment toggles and the Telegram-login Client Secret — `bot/utils/app_config.py`, stored in `app_settings` as `cfg.*`, cached in-process (`load_cache` at startup, reloaded by `save`). Prices are applied in place to `STARS_PLANS` / `CRYPTO_PLANS` / `CARD_PLANS`, so always read prices from those dicts (never copy a number); `/tariffs` fills its prices from `/api/site/prices`. Device limit: `app_config.max_devices()` (the old `MAX_DEVICES` constant is gone). Telegram OIDC: Client ID defaults to the bot's numeric ID from the token, the secret comes from the admin (main-admin only, never returned to the browser) or `.env`. Don't add read-only/static blocks to this page — if something is shown there, it should be editable.

- **Support tickets (2026-10-08)**: the admin shows tickets as letters (From/To/Subject + reply form) with the delivery channel computed by `bot/api.py::_ticket_delivery` — Telegram (bot message), email (needs SMTP), or manual (@username without an account — the bot can't write first). The reply endpoint reports whether it was actually delivered.

- **Payment methods (2026-10-08, ADR-022; supersedes the card part of ADR-015)**: crypto (CryptoPay) and Telegram Stars are ON. **Robokassa is fully removed** — client, signature check, `/card/webhook`, the bot card flow (`card_payment.py`), the guest checkout (`/api/guest/*`, it only served Robokassa), config/`.env` lines and every mention in copy; don't bring it back. "Оплата картой" stays as a method slot for the coming card provider (the owner plans RollyPay — but user-facing copy says only «Оплата картой», never the provider name): RUB prices and the custom-term formula live in `bot/utils/card.py` (`CARD_PLANS`, `custom_plan_price`), `card_ready()` is `False` until a provider is implemented there, and `settings_store.is_provider_enabled("card")` is `False` while it is — so the bot hides the card button, `/api/card/plans` returns `[]`, `/api/invoice/card` answers 503, the admin toggle can't be switched on, and the site shows the card as unavailable/«скоро». To connect a provider: implement payment-link creation + webhook verification in `card.py`, make `card_ready()` check its keys, fill `/api/invoice/card` (pending `Payment(payment_method="card")`) and add a webhook route that marks paid atomically before `_grant_subscription`. The earlier second RUB-rail provider removed in ADR-015 must still never be reintroduced by any name. Old `Payment.payment_method` values are just data — the admin falls back to a plain chip. Crypto (@CryptoBot) always needs a Telegram app to pay; Stars are bot-only (no `/api/invoice/stars`). `profile.py::pay_choice_text()` and `/get-vpn` handle "no method enabled".

- **`/get-vpn` requires registration (2026-08-30, ADR-013)**: 3-step flow — Тариф → Аккаунт → Оплата; the payment step is locked until `GET /api/me` confirms a session. Plans come from the public `/api/site/plans?days=N` (a `custom` plan appears only while card is available — i.e. not until a card provider exists). Before bouncing to `/login` or `/api/telegram-oauth/start`, the chosen plan is saved to `localStorage['star_vpn_pending_purchase']`; `account.html::boot()`'s `resumePendingPurchase()` resumes it on the "Продление" tab. The guest checkout and `card-success.html`'s guest polling are gone (ADR-022); `card-success.html`/`card-fail.html` stay as return pages for the future card provider (`accountState()` sends web-only accounts to `/account`).

- **Gifts are link-only (2026-10-08, ADR-022)**: there is no "gift to @username" anymore — every gift is a one-time link `{SITE_URL}/gift/{code}` (`bot/utils/gifts.py`). Bot: plan → Stars or crypto → anonymity → message → pay (payload `giftlink:{payment_id}`) → the giver gets the link with a share button. Site `/account` → Подарить: pay (crypto now, card once connected) via `POST /api/gift/invoice` → link shown immediately + «Мои подарки» (`GET /api/gift/mine`). The recipient claims on `landing/gift-reveal.html` (`POST /api/gift/link/{code}/claim`) or in the bot via `/start gift_{code}` — both call `gifts.claim_gift`, which marks the gift claimed atomically and grants days in one commit. Until claimed, `Payment.telegram_id` (NOT NULL + FK) points to the giver (ADR-011); paying never grants days (`crypto_payment` / `_handle_link_gift_payment` only mark paid and send the link). `/admin` → Подарки (section `gifts`) lists all gifts and creates free links from «STAR VPN» (`payment_method="admin"`, amount 0, held on `TELEGRAM_ADMIN_ID`'s user) — excluded from revenue and the payments table. Legacy `gift:{plan}:{recipient}:…` invoices still pay out directly to their recipient. The Mini App gift sheet is still a mock (`webapp/src`, `mockApi.js`) — not wired to the API.

- **Wiki lives in the DB (2026-09-25, ADR-017)**: there are no static article files anymore — `landing/wiki/` only holds templates (`_article.html` for an article page, `index.html` for `/wiki` with a `__WIKI_GROUPS__` marker). Every article is a `WikiArticle` row (`content_html`, `custom_css`, `short_title`, `sort_order`; migration `0014_wiki_rich_content` converted old markdown bodies and dropped `body`) and is edited in `/admin` → Wiki (WYSIWYG in an iframe with the site's CSS + HTML mode + preview). The 11 original articles are seeded **once** from `bot/data/wiki_seed.json` on startup (`bot.utils.wiki_page.seed_wiki_articles`, guarded by `app_settings.wiki_seeded`) — deleting them in the admin is permanent, don't re-add a "restore on start". Other pages link to `/wiki/install-ios` etc.; those links 404 if the owner deletes the article, which is accepted. Interactive widgets (FAQ/case accordions, FAQ search, client tabs, source picker) are generic JS in `_article.html` that activates on matching markup. The editor is Notion-like («/» menu, image upload/resize, tables, toggles); its blocks are plain HTML styled in `_article.html` (`figure.wimg[data-align]` with an inline `width:%`, `details.toggle`, `table`) — editor-only markers (`w-sel`, `w-ph`, `details[open]`) are stripped by `wikiCleanHtml()` before saving.

- **Bot editor (2026-09-25, ADR-018)**: `/admin` → Бот. Every user-facing text/button of the main bot screens goes through `bot.utils.bot_texts.t("key", **placeholders)`; reply-keyboard handlers use `MenuText("btn.x")` (matches the current label **and** the default, so old keyboards keep working). Defaults in `TEXTS` must stay byte-identical to what the bot says without overrides. Overrides (`BotText`) and custom blocks (`BotBlock`: text + buttons → block / screen / URL, optional main-menu button and `/command`) are cached in-process (`load_cache` at startup, reloaded on every admin save) — works because bot and API share one process, same as `admin_auth`. When adding a new bot text, add it to `TEXTS` **and** to a screen in `SCREENS`, otherwise the admin can't see it. Devices, gift, card/crypto flows are intentionally "code" nodes — not editable.

- **Site header (2026-09-25)**: one shared header for every public page — `landing/_nav.html` (markup + CSS + JS, including the account dropdown and the «С чего начать» dialog). Pages contain only `<!--SITE_NAV-->`; `bot.utils.branding.brand_html` injects the partial, so a page must be served via `_serve_html`/`brand_html` to get it. Don't add a nav copy back into a page; any element with `data-start` opens the start dialog. Account-menu links go to `/account#<tab>` and `account.html` switches tabs on `hashchange`.

- **Audit rules (2026-09-25, ADR-019)** — invariants that were broken before and must stay fixed:
  - Subscription links are signed: `/sub/{marzban_username}/{sig}` (`bot.utils.branding.subscription_url` / `check_sub_signature`). Marzban usernames are guessable (`ios_tg_<@username>`), so the unsigned `/sub/{username}` route returns 404 unless `SUB_ALLOW_UNSIGNED=true`. Always build links via `subscription_url()`.
  - Never send a VLESS link to a third party — QR codes are rendered locally (`bot.utils.qr.qr_data_uri` / `make_qr_photo`), not via api.qrserver.com.
  - Any grant of days (payment, gift, trial, admin grant, referral bonus) goes through `bot.handlers.payment._grant_subscription`: it adds days on top of the current expiry and re-activates Marzban users (the scheduler disables them on expiry). Don't set `subscription_expires_at` by hand.
  - Ban/unban act on **all** of the user's Marzban users via `bot.utils.vpn_access.set_vpn_enabled` (devices + legacy account). Creating a device uses `marzban.provision_user` (re-activates an existing, previously deleted device user instead of returning a disabled one).
  - `User.referral_count` = number of **paying** referrals; only `_credit_referral` increments it (card, crypto and Stars payments all call it). `/start ref<id>` only sets `referrer_id` (migration `0016` recomputed old inflated values).
  - Payment webhooks mark the payment paid atomically (`UPDATE … WHERE status='pending'`) before granting — retries/duplicates must not grant twice. Same for gift-link claims.
  - Granting days also sets the Marzban expiry of every device to exactly the new `subscription_expires_at` (`marzban.set_expire`) — never "+N days" per device, and new devices get `provision_user(..., expire_at=user.subscription_expires_at)`.
  - `_grant_subscription` commits once, at the end: webhooks/claims mark the payment paid *before* calling it, in the same transaction, and re-raise on failure so the provider retries (`/crypto/webhook` → 503). Don't add a commit between the paid-mark and the grant.
  - Stars prices live only in `bot/utils/plans.py` (`STARS_PLANS`); `pre_checkout` validates the payload (plan, ban, gift recipient, Stars toggle) — never answer it unconditionally.
  - Gift metadata (message, anonymity, sender) is stored on a pending `Payment` (`is_gift`, `gift_*`) at invoice time for every method — no in-memory dicts.
  - Every invoice endpoint calls `_ensure_can_pay(session, tg_id, provider)` (user exists, not banned, provider enabled).
  - Expiry notices go to Telegram, or by email for web-only accounts; the scheduler's last run is stored in `app_settings` (`scheduler.last_tick`).
  - `UserSyncMiddleware` keeps `User.username` current and releases a username from stale holders — Marzban names, admin search and gift sender names rely on it.
  - Pages are authored with `@starisvpnbot` / `@hashprojects`; `bot.utils.branding.brand_html` swaps them for `BOT_USERNAME` / `SUPPORT_USERNAME` when serving — keep new pages on the same placeholders and serve them via `_serve_html`.

