"""
FastAPI веб-API для Telegram Mini App STAR VPN.
Запускается в том же event loop что и бот (uvicorn.Server).
Порт: 8080
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException

from bot.config import settings
from bot.models.device import Device, MAX_DEVICES
from bot.models.gift_notification import GiftNotification
from bot.models.payment import Payment
from bot.models.user import User
from bot.utils.database import AsyncSessionLocal
from bot.utils.marzban import marzban

logger = logging.getLogger(__name__)

app = FastAPI(title="STAR VPN API", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ─── Static files ────────────────────────────────────────────────────────────

_APP_HTML     = Path(__file__).parent.parent / "webapp" / "app.html"
_LANDING_DIR  = Path(__file__).parent.parent / "landing"
_ADMIN_HTML   = Path(__file__).parent.parent / "admin" / "index.html"
_NOT_FOUND_HTML = _LANDING_DIR / "404.html"


def _serve_html(path: Path) -> HTMLResponse:
    if path.exists():
        return HTMLResponse(content=path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Not found</h1>", status_code=404)


@app.exception_handler(StarletteHTTPException)
async def _not_found_page_handler(request: Request, exc: StarletteHTTPException):
    """Отдаёт брендированную 404-страницу для обычных (не API) запросов.
    /api/* и /web/* — это JSON-клиенты (сайт/бот/Mini App), им нужен
    предсказуемый JSON-ответ, а не HTML — их 404 не трогаем."""
    if exc.status_code == 404 and not request.url.path.startswith(("/api/", "/web/")):
        if _NOT_FOUND_HTML.exists():
            return HTMLResponse(content=_NOT_FOUND_HTML.read_text(encoding="utf-8"), status_code=404)
    return await http_exception_handler(request, exc)


@app.get("/app", response_class=HTMLResponse, include_in_schema=False)
async def serve_miniapp():
    return _serve_html(_APP_HTML)


@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
@app.get("/admin/", response_class=HTMLResponse, include_in_schema=False)
async def serve_admin():
    return _serve_html(_ADMIN_HTML)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_landing():
    return _serve_html(_LANDING_DIR / "index.html")


@app.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
@app.get("/privacy.html", response_class=HTMLResponse, include_in_schema=False)
async def serve_privacy():
    return _serve_html(_LANDING_DIR / "privacy.html")


@app.get("/get-vpn", response_class=HTMLResponse, include_in_schema=False)
@app.get("/get-vpn.html", response_class=HTMLResponse, include_in_schema=False)
async def serve_get_vpn():
    """Покупка VPN-ключа без Telegram — для тех, кто не может открыть бота без VPN."""
    return _serve_html(_LANDING_DIR / "get-vpn.html")


@app.get("/terms", response_class=HTMLResponse, include_in_schema=False)
@app.get("/terms.html", response_class=HTMLResponse, include_in_schema=False)
async def serve_terms():
    return _serve_html(_LANDING_DIR / "terms.html")


@app.get("/connect", include_in_schema=False)
@app.get("/connect.html", include_in_schema=False)
async def serve_connect():
    """Старый единый гайд по подключению — теперь 4 отдельные статьи Wiki."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/wiki", status_code=301)


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
@app.get("/login.html", response_class=HTMLResponse, include_in_schema=False)
async def serve_login():
    return _serve_html(_LANDING_DIR / "login.html")


@app.get("/account", response_class=HTMLResponse, include_in_schema=False)
@app.get("/account.html", response_class=HTMLResponse, include_in_schema=False)
async def serve_account():
    return _serve_html(_LANDING_DIR / "account.html")


@app.get("/support", response_class=HTMLResponse, include_in_schema=False)
@app.get("/support.html", response_class=HTMLResponse, include_in_schema=False)
async def serve_support():
    return _serve_html(_LANDING_DIR / "support.html")


@app.get("/tariffs", response_class=HTMLResponse, include_in_schema=False)
@app.get("/tariffs.html", response_class=HTMLResponse, include_in_schema=False)
async def serve_tariffs():
    return _serve_html(_LANDING_DIR / "tariffs.html")


_WIKI_SLUGS = {
    "vless-reality", "zero-logs", "payment", "trial", "referrals", "troubleshooting", "faq",
    "install-ios", "install-android", "install-windows", "install-macos",
}


@app.get("/wiki", response_class=HTMLResponse, include_in_schema=False)
@app.get("/wiki.html", response_class=HTMLResponse, include_in_schema=False)
async def serve_wiki_index():
    return _serve_html(_LANDING_DIR / "wiki" / "index.html")


@app.get("/wiki/{slug}", response_class=HTMLResponse, include_in_schema=False)
@app.get("/wiki/{slug}.html", response_class=HTMLResponse, include_in_schema=False)
async def serve_wiki_article(slug: str):
    slug = slug.removesuffix(".html")
    if slug in _WIKI_SLUGS:
        return _serve_html(_LANDING_DIR / "wiki" / f"{slug}.html")

    # Не одна из 7 базовых статей — ищем среди созданных из админ-панели.
    from bot.models.wiki_article import WikiArticle
    from bot.utils.wiki_page import render_wiki_article_page

    async with AsyncSessionLocal() as session:
        r = await session.execute(
            select(WikiArticle).where(WikiArticle.slug == slug, WikiArticle.is_published.is_(True))
        )
        article: WikiArticle | None = r.scalar_one_or_none()
        if not article:
            return HTMLResponse(content="<h1>Not found</h1>", status_code=404)
        article.views = (article.views or 0) + 1
        await session.commit()

    return HTMLResponse(render_wiki_article_page(
        slug=article.slug, title=article.title, lede=article.lede,
        body=article.body, section=article.section,
    ))


# ─── GET /sub/{username} — подписка для VPN-клиентов (Happ, v2rayNG, ...) ────
#
# В отличие от одиночной vless://-ссылки, которую бот шлёт как текст/QR,
# подписка — это URL, который сам клиент периодически перечитывает. Это даёт
# три вещи бесплатно: (1) стабильное имя "STAR VPN" вместо marzban_username,
# (2) нативный бар "трафик/осталось" в клиенте (заголовок Subscription-
# Userinfo — тот же механизм, что использует сам Marzban), и (3) когда
# подписка истекла — на месте сервера в списке клиента виден сам текст
# "Подписка закончилась — продли в @бот", а не просто обрыв соединения.

@app.get("/sub/{username}", include_in_schema=False)
async def serve_subscription(username: str, request: Request):
    from bot.utils.branding import set_vless_remark, set_vless_remark_text
    from bot.utils.sub_page import is_vpn_client, render_subscription_page

    try:
        mz = await marzban.get_user(username)
    except Exception as e:
        logger.warning("Subscription: marzban get_user failed for %s: %s", username, e)
        raise HTTPException(status_code=404, detail="Not found")

    link = marzban.extract_vless_link(mz) or ""
    is_active = mz.get("status") == "active"
    expire = int(mz.get("expire") or 0)

    if is_active and link:
        link = set_vless_remark(link)
    elif link:
        expired_text = f"⚠️ Подписка закончилась — продли в @{settings.bot_username}"
        link = set_vless_remark_text(link, expired_text)

    user_agent = request.headers.get("user-agent", "")
    if not is_vpn_client(user_agent):
        days_left = max(0, (expire - int(datetime.utcnow().timestamp())) // 86400) if expire else None
        sub_url = f"{settings.webapp_url.rstrip('/')}/sub/{username}"
        html_page = render_subscription_page(
            sub_url=sub_url,
            display_name="STAR VPN",
            is_active=is_active,
            days_left=days_left,
            bot_username=settings.bot_username,
        )
        return HTMLResponse(html_page)

    body = base64.b64encode(link.encode()).decode() if link else ""

    used = int(mz.get("used_traffic") or 0)
    total = int(mz.get("data_limit") or 0)

    headers = {
        "Profile-Title": "base64:" + base64.b64encode("STAR VPN".encode()).decode(),
        "Profile-Update-Interval": "12",
        "Subscription-Userinfo": f"upload=0; download={used}; total={total}; expire={expire}",
    }
    return PlainTextResponse(body, headers=headers)


@app.get("/logo.png", include_in_schema=False)
async def serve_logo():
    from fastapi.responses import FileResponse
    p = _LANDING_DIR / "logo.png"
    if p.exists():
        return FileResponse(str(p), media_type="image/png")
    return HTMLResponse(content="", status_code=404)


@app.get("/logo-title.png", include_in_schema=False)
async def serve_logo_title():
    from fastapi.responses import FileResponse
    p = _LANDING_DIR / "logo-title.png"
    if p.exists():
        return FileResponse(str(p), media_type="image/png")
    return HTMLResponse(content="", status_code=404)


@app.get("/logo-star-transparent.png", include_in_schema=False)
async def serve_logo_star_transparent():
    """Вордмарк на прозрачном фоне для экрана загрузки (landing/index.html)."""
    from fastapi.responses import FileResponse
    p = _LANDING_DIR / "logo-star-transparent.png"
    if p.exists():
        return FileResponse(str(p), media_type="image/png")
    return HTMLResponse(content="", status_code=404)


@app.get("/world-dots.js", include_in_schema=False)
async def serve_world_dots():
    """Данные для карты серверов на главной (landing/index.html)."""
    from fastapi.responses import FileResponse
    p = _LANDING_DIR / "world-dots.js"
    if p.exists():
        return FileResponse(str(p), media_type="application/javascript")
    return HTMLResponse(content="", status_code=404)


@app.get("/favicon.svg", include_in_schema=False)
async def serve_favicon_svg():
    from fastapi.responses import FileResponse
    p = _LANDING_DIR / "favicon.svg"
    if p.exists():
        return FileResponse(str(p), media_type="image/svg+xml")
    return HTMLResponse(content="", status_code=404)


@app.get("/favicon.ico", include_in_schema=False)
async def serve_favicon_ico():
    from fastapi.responses import FileResponse
    p = _LANDING_DIR / "favicon.ico"
    if p.exists():
        return FileResponse(str(p), media_type="image/x-icon")
    return HTMLResponse(content="", status_code=404)


@app.get("/favicon.png", include_in_schema=False)
async def serve_favicon_png():
    from fastapi.responses import FileResponse
    p = _LANDING_DIR / "favicon.png"
    if p.exists():
        return FileResponse(str(p), media_type="image/png")
    return HTMLResponse(content="", status_code=404)


@app.get("/apple-touch-icon.png", include_in_schema=False)
async def serve_apple_touch_icon():
    from fastapi.responses import FileResponse
    p = _LANDING_DIR / "apple-touch-icon.png"
    if p.exists():
        return FileResponse(str(p), media_type="image/png")
    return HTMLResponse(content="", status_code=404)


# ─── Auth ─────────────────────────────────────────────────────────────────────

def _parse_tg_id(init_data: str) -> int:
    """Верифицирует Telegram initData HMAC и возвращает telegram_id."""
    parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", "")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    # Telegram docs: secret = HMAC_SHA256(key="WebAppData", msg=bot_token)
    secret = hmac.new(key=b"WebAppData", msg=settings.telegram_api_token.encode(), digestmod=hashlib.sha256).digest()
    expected = hmac.new(key=secret, msg=data_check_string.encode(), digestmod=hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, received_hash):
        raise HTTPException(status_code=403, detail="Invalid Telegram signature")

    user_obj = json.loads(parsed.get("user", "{}"))
    tg_id = user_obj.get("id")
    if not tg_id:
        raise HTTPException(status_code=403, detail="No user id in initData")
    return int(tg_id)


def _tg_id(x_telegram_init_data: str | None) -> int:
    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail="Missing X-Telegram-Init-Data")
    try:
        return _parse_tg_id(x_telegram_init_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Bad initData: {e}")


async def _resolve_tg_id(request: Request, x_telegram_init_data: str | None, session) -> int:
    """
    Разрешает identity либо из Telegram Mini App (X-Telegram-Init-Data),
    либо из cookie-сессии личного кабинета (/login) — единая точка входа,
    чтобы /api/devices, /api/referral и оплата работали одинаково для
    обоих способов подключения.
    """
    if x_telegram_init_data:
        return _parse_tg_id(x_telegram_init_data)

    from bot.utils.webauth import get_session_user, SESSION_COOKIE_NAME
    user = await get_session_user(request.cookies.get(SESSION_COOKIE_NAME), session)
    if user:
        return user.telegram_id
    raise HTTPException(status_code=401, detail="Not authenticated")


async def _resolve_tg_id_optional(request: Request, x_telegram_init_data: str | None, session) -> int | None:
    """Как _resolve_tg_id, но не требует авторизации — для форм, доступных анонимно."""
    try:
        return await _resolve_tg_id(request, x_telegram_init_data, session)
    except HTTPException:
        return None


# ─── Личный кабинет: регистрация и вход по email + паролю ────────────────────

@app.post("/api/account/register")
async def account_register(request: Request):
    """Регистрация веб-аккаунта: email + пароль, затем подтверждение почты
    одноразовым кодом (см. /api/account/verify-email)."""
    from bot.utils.webauth import is_valid_email, is_valid_password, register_user, create_verification_code
    from bot.utils.mailer import send_verification_code_email
    from sqlalchemy import select as _select

    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not is_valid_email(email):
        raise HTTPException(400, "Некорректный email")
    if not is_valid_password(password):
        raise HTTPException(400, "Пароль должен быть от 8 до 128 символов")

    async with AsyncSessionLocal() as session:
        existing = (await session.execute(_select(User).where(User.email == email))).scalar_one_or_none()
        if existing and existing.email_verified:
            raise HTTPException(409, "Этот email уже зарегистрирован. Попробуйте войти.")

        user = await register_user(email, password, session)
        try:
            raw_code = await create_verification_code(user.email, session)
        except ValueError:
            # Код недавно уже отправляли — не шлём повторно, просто ведём
            # пользователя на экран ввода кода.
            return {"ok": True}

    try:
        await send_verification_code_email(email, raw_code)
    except Exception as e:
        logger.error("account_register: failed to send email to %s: %s", email, e)
        raise HTTPException(502, "Не удалось отправить письмо. Попробуйте позже.")

    return {"ok": True}


@app.post("/api/account/resend-code")
async def account_resend_code(request: Request):
    from bot.utils.webauth import is_valid_email, create_verification_code
    from bot.utils.mailer import send_verification_code_email

    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    if not is_valid_email(email):
        raise HTTPException(400, "Некорректный email")

    async with AsyncSessionLocal() as session:
        try:
            raw_code = await create_verification_code(email, session)
        except ValueError:
            raise HTTPException(429, "Код уже отправлен — подождите немного перед повторной отправкой.")

    try:
        await send_verification_code_email(email, raw_code)
    except Exception as e:
        logger.error("account_resend_code: failed to send email to %s: %s", email, e)
        raise HTTPException(502, "Не удалось отправить письмо. Попробуйте позже.")

    return {"ok": True}


@app.post("/api/account/verify-email")
async def account_verify_email(request: Request):
    """Подтверждает код из письма, отмечает почту подтверждённой и сразу
    открывает веб-сессию (регистрация → сразу залогинен)."""
    from bot.utils.webauth import (
        is_valid_email, check_verification_code, create_web_session,
        SESSION_COOKIE_NAME, SESSION_TTL,
    )
    from sqlalchemy import select as _select

    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    code = (body.get("code") or "").strip()
    if not is_valid_email(email) or not code:
        raise HTTPException(400, "Некорректные данные")

    async with AsyncSessionLocal() as session:
        ok = await check_verification_code(email, code, session)
        if not ok:
            raise HTTPException(400, "Неверный или устаревший код")

        user = (await session.execute(_select(User).where(User.email == email))).scalar_one_or_none()
        if not user:
            raise HTTPException(404, "Аккаунт не найден")

        user.email_verified = True
        await session.commit()
        session_token = await create_web_session(user, session)

    resp = JSONResponse({"ok": True})
    resp.set_cookie(
        SESSION_COOKIE_NAME, session_token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True, secure=True, samesite="lax", path="/",
    )
    return resp


@app.post("/api/account/login")
async def account_login(request: Request):
    """Вход по email + паролю. Не подтверждена почта — 403 с
    detail="email_not_verified", чтобы фронтенд перевёл на экран ввода кода."""
    from bot.utils.webauth import is_valid_email, verify_password, create_web_session, SESSION_COOKIE_NAME, SESSION_TTL
    from sqlalchemy import select as _select

    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not is_valid_email(email) or not password:
        raise HTTPException(400, "Введите email и пароль")

    async with AsyncSessionLocal() as session:
        user = (await session.execute(_select(User).where(User.email == email))).scalar_one_or_none()
        if not user or not user.password_hash or not await verify_password(password, user.password_hash):
            raise HTTPException(401, "Неверный email или пароль")
        if not user.email_verified:
            raise HTTPException(403, "email_not_verified")

        session_token = await create_web_session(user, session)

    resp = JSONResponse({"ok": True})
    resp.set_cookie(
        SESSION_COOKIE_NAME, session_token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True, secure=True, samesite="lax", path="/",
    )
    return resp


@app.post("/api/account/logout")
async def account_logout(request: Request):
    from bot.utils.webauth import delete_web_session, SESSION_COOKIE_NAME

    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        async with AsyncSessionLocal() as session:
            await delete_web_session(token, session)

    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return resp


# ─── Вход через Telegram (OIDC, oauth.telegram.org) ──────────────────────────
# Не Mini App и не classic Login Widget — полноценный OAuth2/OIDC authorization
# code flow с PKCE. Настраивается в BotFather у бота (Login Widget), там же
# нужно зарегистрировать redirect_uri (см. telegram_oauth.redirect_uri()).

_TG_OAUTH_COOKIE = "tg_oauth_pkce"
_TG_OAUTH_COOKIE_PATH = "/api/telegram-oauth"


@app.get("/api/telegram-oauth/start", include_in_schema=False)
async def telegram_oauth_start():
    from bot.utils.telegram_oauth import build_authorize_url, generate_pkce_pair

    if not settings.telegram_oauth_client_id or not settings.telegram_oauth_client_secret:
        return HTMLResponse("Вход через Telegram временно недоступен", status_code=503)

    state = secrets.token_urlsafe(24)
    verifier, challenge = generate_pkce_pair()

    resp = RedirectResponse(build_authorize_url(state, challenge), status_code=302)
    resp.set_cookie(
        _TG_OAUTH_COOKIE, f"{state}.{verifier}",
        max_age=600, httponly=True, secure=True, samesite="lax", path=_TG_OAUTH_COOKIE_PATH,
    )
    return resp


@app.get("/api/telegram-oauth/callback", include_in_schema=False)
async def telegram_oauth_callback(
    request: Request, code: str | None = None, state: str | None = None, error: str | None = None
):
    from bot.utils.telegram_oauth import exchange_code, verify_id_token
    from bot.utils.webauth import (
        SESSION_COOKIE_NAME, SESSION_TTL, create_web_session, get_or_create_user_by_telegram_id,
    )

    def _fail():
        resp = RedirectResponse(f"{settings.site_url}/login?tg_error=1", status_code=302)
        resp.delete_cookie(_TG_OAUTH_COOKIE, path=_TG_OAUTH_COOKIE_PATH)
        return resp

    if error or not code or not state:
        return _fail()

    saved_state, _, verifier = (request.cookies.get(_TG_OAUTH_COOKIE) or "").partition(".")
    if not verifier or not hmac.compare_digest(saved_state, state):
        return _fail()

    try:
        tokens = await exchange_code(code, verifier)
        claims = verify_id_token(tokens["id_token"])
        tg_id = int(claims.get("id") or claims["sub"])
    except Exception as e:
        logger.warning("Ошибка входа через Telegram OAuth: %s", e)
        return _fail()

    username = claims.get("preferred_username")
    full_name = claims.get("name") or " ".join(
        filter(None, [claims.get("given_name"), claims.get("family_name")])
    ) or None

    async with AsyncSessionLocal() as session:
        user = await get_or_create_user_by_telegram_id(tg_id, username, full_name, session)
        session_token = await create_web_session(user, session)

    resp = RedirectResponse(f"{settings.site_url}/account", status_code=302)
    resp.delete_cookie(_TG_OAUTH_COOKIE, path=_TG_OAUTH_COOKIE_PATH)
    resp.set_cookie(
        SESSION_COOKIE_NAME, session_token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True, secure=True, samesite="lax", path="/",
    )
    return resp


# ─── Поддержка (тикеты) — форма на /support не требует входа ─────────────────

_SUPPORT_TOPICS = {"connect", "payment", "account", "other"}


@app.post("/api/support")
async def create_support_ticket(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    from bot.models.support_ticket import SupportTicket

    body = await request.json()
    topic = (body.get("topic") or "other").strip()
    if topic not in _SUPPORT_TOPICS:
        topic = "other"
    contact = (body.get("contact") or "").strip()[:320]
    message = (body.get("message") or "").strip()[:4000]
    platform = (body.get("platform") or "").strip()[:32] or None

    async with AsyncSessionLocal() as session:
        # Если пользователь уже вошёл (Mini App или сессия личного кабинета) —
        # привязываем тикет к аккаунту автоматически, но поле contact в форме
        # остаётся обязательным для всех: это то, куда реально можно ответить.
        tg_id = await _resolve_tg_id_optional(request, x_telegram_init_data, session)
        if not contact and tg_id is None:
            raise HTTPException(400, "Укажите email или @username для связи")
        if len(message) < 10:
            raise HTTPException(400, "Опишите проблему подробнее (от 10 символов)")

        ticket = SupportTicket(
            user_id=tg_id, contact=contact or None, topic=topic,
            message=message, platform=platform,
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)

    return {"ok": True, "id": f"S-{ticket.id:06d}"}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _fmt_online(online_at: int | None, now_ts: int) -> str:
    if not online_at:
        return "никогда"
    diff = now_ts - online_at
    if diff < 60:
        return "только что"
    if diff < 3600:
        return f"{diff // 60} мин. назад"
    if diff < 86400:
        return f"{diff // 3600} ч. назад"
    return f"{diff // 86400} дн. назад"


from bot.utils.branding import set_vless_remark as _set_vless_remark


async def _get_active_devices(tg_id: int, session) -> list[Device]:
    r = await session.execute(
        select(Device)
        .where(Device.telegram_id == tg_id, Device.is_active.is_(True))
        .order_by(Device.slot)
    )
    return list(r.scalars().all())


def _free_slot(devices: list[Device]) -> int | None:
    used = {d.slot for d in devices}
    for s in range(1, MAX_DEVICES + 1):
        if s not in used:
            return s
    return None


DEVICE_TYPES_API = {"ios", "android", "macos", "windows", "linux", "androidtv", "appletv"}


def _mz_username_for_type(
    type_key: str,
    telegram_id: int,
    username: str | None,
    existing: list[str],
) -> str:
    ident = username.lower() if username else (
        f"web{-telegram_id}" if telegram_id < 0 else str(telegram_id)
    )
    base = f"{type_key}_tg_{ident}"
    if base not in existing:
        return base
    for i in range(2, 10):
        candidate = f"{type_key}{i}_tg_{ident}"
        if candidate not in existing:
            return candidate
    return f"{type_key}_tg_{ident}_x"


# ─── GET /api/me ──────────────────────────────────────────────────────────────

@app.get("/api/me")
async def get_me(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    async with AsyncSessionLocal() as session:
        tg_id = await _resolve_tg_id(request, x_telegram_init_data, session)
        r = await session.execute(select(User).where(User.telegram_id == tg_id))
        user: User | None = r.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found — send /start to bot first")

        devs = await _get_active_devices(tg_id, session)
        device_count = len(devs)

    traffic_gb = 0.0
    try:
        if user.marzban_username:
            mz = await marzban.get_user(user.marzban_username)
            traffic_gb = round((mz.get("used_traffic") or 0) / 1_073_741_824, 2)
    except Exception:
        pass

    now = datetime.utcnow()
    exp = user.subscription_expires_at
    return {
        "telegram_id": tg_id,
        "telegram_linked": tg_id > 0,
        "email": user.email or "",
        "is_banned": bool(user.is_banned),
        "ban_reason": user.ban_reason or "",
        "full_name": user.full_name or "",
        "username": user.username or "",
        "subscription_expires_at": exp.isoformat() if exp else None,
        "subscription_active": bool(exp and exp > now),
        "trial_used": bool(user.trial_used),
        "trial_days": settings.trial_days,
        "total_stars_paid": int(user.total_stars_paid or 0),
        "referral_count": int(user.referral_count or 0),
        "extra_days_granted": int(user.extra_days_granted or 0),
        "traffic_gb": traffic_gb,
        "device_count": device_count,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "support_url": f"https://t.me/{settings.support_username.lstrip('@')}",
        "bot_username": settings.bot_username,
        "max_devices": MAX_DEVICES,
        "server_host": settings.server_host,
        "server_country": settings.server_country,
        "server_city": settings.server_city,
        "server_flag": settings.server_flag,
        "server_port": settings.server_port,
        "server_sni": settings.server_sni,
        "server_protocol": "VLESS + Reality",
        "server_tls": "TLS 1.3",
    }


# ─── GET /api/devices ─────────────────────────────────────────────────────────

@app.get("/api/devices")
async def get_devices(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    now_ts = int(datetime.utcnow().timestamp())
    result = []

    async with AsyncSessionLocal() as session:
        tg_id = await _resolve_tg_id(request, x_telegram_init_data, session)
        devs = await _get_active_devices(tg_id, session)
        deactivated_any = False

        for d in devs:
            traffic_gb = 0.0
            online = False
            last_online = "никогда"
            status_label = "неизвестно"

            try:
                mz = await marzban.get_user(d.marzban_username)
                traffic_gb = round((mz.get("used_traffic") or 0) / 1_073_741_824, 2)
                oa = mz.get("online_at")
                online = bool(oa and (now_ts - oa) < 300)
                last_online = _fmt_online(oa, now_ts)
                status_map = {
                    "active": "Активен", "disabled": "Отключён",
                    "expired": "Истёк",  "limited": "Лимит",
                }
                status_label = status_map.get(mz.get("status", ""), "—")

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Пользователь удалён из Marzban — деактивируем устройство в БД
                    logger.info("Device %s not found in Marzban, deactivating", d.marzban_username)
                    d.is_active = False
                    deactivated_any = True
                    continue  # не включаем в результат
                logger.warning("Marzban get_user %s: %s", d.marzban_username, e)
                status_label = "нет связи"

            except Exception as e:
                logger.warning("Marzban get_user %s: %s", d.marzban_username, e)
                status_label = "нет связи"

            result.append({
                "id": d.id,
                "slot": d.slot,
                "name": d.name,
                "custom_name": d.custom_name,
                "traffic_gb": traffic_gb,
                "online": online,
                "last_online": last_online,
                "status_label": status_label,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            })

        if deactivated_any:
            await session.commit()

    return result


# ─── POST /api/devices ────────────────────────────────────────────────────────

@app.post("/api/devices")
async def create_device(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    body = await request.json()
    type_key = (body.get("type") or "").strip().lower()
    custom_name = (body.get("name") or "").strip()[:64] or None
    if not type_key or type_key not in DEVICE_TYPES_API:
        raise HTTPException(400, f"Invalid device type. Must be one of: {', '.join(DEVICE_TYPES_API)}")

    async with AsyncSessionLocal() as session:
        tg_id = await _resolve_tg_id(request, x_telegram_init_data, session)
        r = await session.execute(select(User).where(User.telegram_id == tg_id))
        user: User | None = r.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found")

        now = datetime.utcnow()
        if not (user.subscription_expires_at and user.subscription_expires_at > now):
            raise HTTPException(403, "No active subscription")

        devs = await _get_active_devices(tg_id, session)
        slot = _free_slot(devs)
        if not slot:
            raise HTTPException(403, f"Maximum {MAX_DEVICES} devices allowed")

        days_left = max(1, (user.subscription_expires_at - now).days)
        existing_mz = [d.marzban_username for d in devs]
        mz_username = _mz_username_for_type(type_key, tg_id, user.username, existing_mz)

        link = ""
        try:
            mz_user = await marzban.create_user(
                telegram_id=tg_id,
                days=days_left,
                note=f"device|type:{type_key}|slot:{slot}|tg:{tg_id}|webapp",
                ip_limit=1,
                username=mz_username,
            )
            link = marzban.extract_vless_link(mz_user) or ""
        except Exception as e:
            logger.warning("create_user failed (%s), trying get_or_create: %s", mz_username, e)
            try:
                mz_user = await marzban.get_or_create_user(mz_username, tg_id, days_left)
                link = marzban.extract_vless_link(mz_user) or ""
            except Exception as e2:
                logger.error("get_or_create_user also failed for %s: %s", mz_username, e2)
                raise HTTPException(500, "VPN server error. Try again later.")

        if link:
            if custom_name:
                from bot.utils.branding import set_vless_remark_text
                link = set_vless_remark_text(link, custom_name)
            else:
                link = _set_vless_remark(link, type_key)

        dev = Device(
            telegram_id=tg_id,
            slot=slot,
            name=type_key,
            custom_name=custom_name,
            marzban_username=mz_username,
        )
        session.add(dev)
        await session.commit()
        await session.refresh(dev)

    qr_url = (
        f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(link)}"
        if link else ""
    )
    from bot.utils.branding import subscription_url
    return {
        "id": dev.id,
        "slot": slot,
        "type": type_key,
        "name": type_key,
        "custom_name": custom_name,
        "link": link,
        "qr_url": qr_url,
        "sub_url": subscription_url(mz_username),
    }


# ─── GET /api/devices/{id}/link ───────────────────────────────────────────────

@app.get("/api/devices/{device_id}/link")
async def get_device_link(device_id: int, request: Request, x_telegram_init_data: str | None = Header(default=None)):
    async with AsyncSessionLocal() as session:
        tg_id = await _resolve_tg_id(request, x_telegram_init_data, session)
        r = await session.execute(select(Device).where(Device.id == device_id))
        dev: Device | None = r.scalar_one_or_none()

    if not dev or dev.telegram_id != tg_id:
        raise HTTPException(404, "Device not found")

    try:
        mz_user = await marzban.get_user(dev.marzban_username)
        link = marzban.extract_vless_link(mz_user) or ""
        if link:
            if dev.custom_name:
                from bot.utils.branding import set_vless_remark_text
                link = set_vless_remark_text(link, dev.custom_name)
            else:
                link = _set_vless_remark(link, dev.name)
    except Exception as e:
        raise HTTPException(500, str(e))

    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(link)}" if link else ""
    from bot.utils.branding import subscription_url
    return {
        "link": link, "qr_url": qr_url, "name": dev.name, "custom_name": dev.custom_name,
        "sub_url": subscription_url(dev.marzban_username),
    }


# ─── PATCH /api/devices/{id} — переименовать устройство ──────────────────────

@app.patch("/api/devices/{device_id}")
async def rename_device(device_id: int, request: Request, x_telegram_init_data: str | None = Header(default=None)):
    body = await request.json()
    custom_name = (body.get("name") or "").strip()[:64]
    if not custom_name:
        raise HTTPException(400, "Укажите имя устройства")

    async with AsyncSessionLocal() as session:
        tg_id = await _resolve_tg_id(request, x_telegram_init_data, session)
        r = await session.execute(select(Device).where(Device.id == device_id))
        dev: Device | None = r.scalar_one_or_none()
        if not dev or dev.telegram_id != tg_id:
            raise HTTPException(404, "Device not found")

        dev.custom_name = custom_name
        await session.commit()

    return {"ok": True, "custom_name": custom_name}


# ─── DELETE /api/devices/{id} ─────────────────────────────────────────────────

@app.delete("/api/devices/{device_id}")
async def delete_device(device_id: int, request: Request, x_telegram_init_data: str | None = Header(default=None)):
    async with AsyncSessionLocal() as session:
        tg_id = await _resolve_tg_id(request, x_telegram_init_data, session)
        r = await session.execute(select(Device).where(Device.id == device_id))
        dev: Device | None = r.scalar_one_or_none()
        if not dev or dev.telegram_id != tg_id:
            raise HTTPException(404, "Device not found")
        dev.is_active = False
        try:
            await marzban.disable_user(dev.marzban_username)
        except Exception as e:
            logger.warning("Marzban disable failed: %s", e)
        await session.commit()
    return {"ok": True}


# ─── GET /api/referral ────────────────────────────────────────────────────────

@app.get("/api/referral")
async def get_referral(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    async with AsyncSessionLocal() as session:
        tg_id = await _resolve_tg_id(request, x_telegram_init_data, session)
        r = await session.execute(select(User).where(User.telegram_id == tg_id))
        user: User | None = r.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found")

        refs_r = await session.execute(
            select(User).where(User.referrer_id == tg_id).order_by(User.created_at.desc()).limit(20)
        )
        referrals = refs_r.scalars().all()

    from bot.handlers.payment import REFERRAL_DAYS_BONUS, REFERRAL_MILESTONE_SIZE, REFERRAL_ACHIEVEMENTS

    paying = int(user.referral_count or 0)

    return {
        "extra_days_granted": int(user.extra_days_granted or 0),
        "link": f"https://t.me/{settings.bot_username}?start=ref{tg_id}",
        "referral_count": paying,
        "days_bonus": REFERRAL_DAYS_BONUS,
        "milestone_size": REFERRAL_MILESTONE_SIZE,
        "achievements": [
            {
                "key": a["key"],
                "icon": a["icon"],
                "title": a["title"],
                "threshold": a["threshold"],
                "bonus_days": a["bonus_days"],
                "unlocked": paying >= a["threshold"],
            }
            for a in REFERRAL_ACHIEVEMENTS
        ],
        "referrals": [
            {
                "name": r.full_name or r.username or "Пользователь",
                "date": r.created_at.strftime("%d.%m.%Y") if r.created_at else "",
                "paid": bool(r.referral_bonus_counted),
            }
            for r in referrals
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN API — только для telegram_admin_id
# ═══════════════════════════════════════════════════════════════════════════════

def _require_admin(tg_id: int) -> None:
    if tg_id != settings.telegram_admin_id:
        raise HTTPException(403, "Admin only")


async def _tg_send(chat_id: int, text: str) -> None:
    """Отправить сообщение через Telegram Bot API напрямую."""
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"https://api.telegram.org/bot{settings.telegram_api_token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        )


# ─── GET /api/admin/check ────────────────────────────────────────────────────
@app.get("/api/admin/check")
async def admin_check(x_telegram_init_data: str | None = Header(default=None)):
    tg_id = _tg_id(x_telegram_init_data)
    return {"is_admin": tg_id == settings.telegram_admin_id}


# ─── GET /api/admin/stats ────────────────────────────────────────────────────
@app.get("/api/admin/stats")
async def admin_stats(x_telegram_init_data: str | None = Header(default=None)):
    tg_id = _tg_id(x_telegram_init_data)
    _require_admin(tg_id)

    now = datetime.utcnow()
    async with AsyncSessionLocal() as session:
        total = (await session.execute(select(func.count()).select_from(User))).scalar_one()
        active = (await session.execute(
            select(func.count()).where(User.subscription_expires_at > now)
        )).scalar_one()
        trial = (await session.execute(
            select(func.count()).where(User.trial_used.is_(True))
        )).scalar_one()
        banned = (await session.execute(
            select(func.count()).where(User.is_banned.is_(True))
        )).scalar_one()
        stars_sum = (await session.execute(
            select(func.sum(Payment.amount)).where(Payment.status == "paid")
        )).scalar_one()
        pays_count = (await session.execute(
            select(func.count(Payment.id)).where(Payment.status == "paid")
        )).scalar_one()
        referral_days_sum = (await session.execute(
            select(func.sum(User.extra_days_granted))
        )).scalar_one()

    # Онлайн из Marzban
    online_count = 0
    try:
        all_mz = await marzban.get_all_users()
        now_ts = now.timestamp()
        online_count = sum(1 for u in all_mz if u.get("online_at") and (now_ts - u["online_at"]) < 300)
    except Exception:
        online_count = -1

    return {
        "total_users": total,
        "active_subscriptions": active,
        "trial_used": trial,
        "banned": banned,
        "online_now": online_count,
        "total_stars": int(stars_sum or 0),
        "total_payments": pays_count,
        "referral_days_total": int(referral_days_sum or 0),
    }


# ─── GET /api/admin/user ─────────────────────────────────────────────────────
@app.get("/api/admin/user")
async def admin_get_user(
    q: str,
    x_telegram_init_data: str | None = Header(default=None),
):
    tg_id = _tg_id(x_telegram_init_data)
    _require_admin(tg_id)

    async with AsyncSessionLocal() as session:
        q = q.strip().lstrip("@")
        if q.lstrip("-").isdigit():
            r = await session.execute(select(User).where(User.telegram_id == int(q)))
        else:
            r = await session.execute(select(User).where(User.username == q))
        user: User | None = r.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "Пользователь не найден")

        devs = await _get_active_devices(user.telegram_id, session)

    now = datetime.utcnow()
    exp = user.subscription_expires_at
    days_left = max(0, (exp - now).days) if exp and exp > now else 0

    return {
        "telegram_id": user.telegram_id,
        "username": user.username or "",
        "full_name": user.full_name or "",
        "is_banned": bool(user.is_banned),
        "ban_reason": user.ban_reason or "",
        "trial_used": bool(user.trial_used),
        "subscription_expires_at": exp.isoformat() if exp else None,
        "subscription_active": bool(exp and exp > now),
        "days_left": days_left,
        "total_stars_paid": int(user.total_stars_paid or 0),
        "referral_count": int(user.referral_count or 0),
        "extra_days_granted": int(user.extra_days_granted or 0),
        "marzban_username": user.marzban_username or "",
        "device_count": len(devs),
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


# ─── GET /api/admin/users ────────────────────────────────────────────────────
@app.get("/api/admin/users")
async def admin_list_users(
    limit: int = 20,
    offset: int = 0,
    q: str = "",
    x_telegram_init_data: str | None = Header(default=None),
):
    tg_id = _tg_id(x_telegram_init_data)
    _require_admin(tg_id)
    now = datetime.utcnow()

    async with AsyncSessionLocal() as session:
        query = select(User)
        if q:
            q = q.strip().lstrip("@")
            if q.lstrip("-").isdigit():
                query = query.where(User.telegram_id == int(q))
            else:
                query = query.where(or_(
                    User.username.ilike(f"%{q}%"),
                    User.full_name.ilike(f"%{q}%"),
                ))
        query = query.order_by(User.created_at.desc()).limit(limit).offset(offset)
        users = (await session.execute(query)).scalars().all()

        total_q = select(func.count(User.telegram_id))
        if q:
            if q.lstrip("-").isdigit():
                total_q = total_q.where(User.telegram_id == int(q))
            else:
                total_q = total_q.where(or_(
                    User.username.ilike(f"%{q}%"),
                    User.full_name.ilike(f"%{q}%"),
                ))
        total = (await session.execute(total_q)).scalar_one()

    return {
        "total": total,
        "users": [
            {
                "telegram_id": u.telegram_id,
                "username": u.username or "",
                "full_name": u.full_name or "",
                "is_banned": bool(u.is_banned),
                "subscription_active": bool(u.subscription_expires_at and u.subscription_expires_at > now),
                "subscription_expires_at": u.subscription_expires_at.isoformat() if u.subscription_expires_at else None,
                "days_left": max(0, (u.subscription_expires_at - now).days) if u.subscription_expires_at and u.subscription_expires_at > now else 0,
                "total_stars_paid": int(u.total_stars_paid or 0),
                "referral_count": int(u.referral_count or 0),
                "extra_days_granted": int(u.extra_days_granted or 0),
                "trial_used": bool(u.trial_used),
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


# ─── POST /api/admin/grant ───────────────────────────────────────────────────
@app.post("/api/admin/grant")
async def admin_grant(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    tg_id = _tg_id(x_telegram_init_data)
    _require_admin(tg_id)
    body = await request.json()
    target_id = int(body.get("telegram_id", 0))
    days = int(body.get("days", 0))
    if not target_id or days <= 0:
        raise HTTPException(400, "telegram_id and days required")

    async with AsyncSessionLocal() as session:
        r = await session.execute(select(User).where(User.telegram_id == target_id))
        user: User | None = r.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found")

        # Продлеваем все активные устройства в Marzban
        dev_result = await session.execute(
            select(Device).where(Device.telegram_id == target_id, Device.is_active.is_(True))
        )
        devices = list(dev_result.scalars().all())
        if devices:
            for dev in devices:
                try:
                    await marzban.extend_user(dev.marzban_username, days)
                    # Включаем аккаунт если был забанен/отключён
                    await marzban.enable_user(dev.marzban_username)
                except Exception as e:
                    logger.warning("admin_grant extend device %s: %s", dev.marzban_username, e)
        elif user.marzban_username:
            await marzban.extend_user(user.marzban_username, days)
        else:
            mz = await marzban.create_user(target_id, days, note="admin_grant|webapp")
            user.marzban_username = mz["username"]

        now = datetime.utcnow()
        base = user.subscription_expires_at if (user.subscription_expires_at and user.subscription_expires_at > now) else now
        user.subscription_expires_at = base + timedelta(days=days)
        await session.commit()

    await _tg_send(target_id, f"🎁 <b>Администратор выдал подписку на {days} дней!</b>\nОткрой 📱 Моя подписка для подключения.")
    return {"ok": True, "expires_at": user.subscription_expires_at.isoformat()}


# ─── POST /api/admin/ban ─────────────────────────────────────────────────────
@app.post("/api/admin/ban")
async def admin_ban(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    tg_id = _tg_id(x_telegram_init_data)
    _require_admin(tg_id)
    body = await request.json()
    target_id = int(body.get("telegram_id", 0))
    if not target_id:
        raise HTTPException(400, "telegram_id required")

    reason = (body.get("reason") or "").strip()[:500] or None

    async with AsyncSessionLocal() as session:
        r = await session.execute(select(User).where(User.telegram_id == target_id))
        user: User | None = r.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found")
        user.is_banned = True
        user.ban_reason = reason
        if user.marzban_username:
            try:
                await marzban.disable_user(user.marzban_username)
            except Exception:
                pass
        await session.commit()

    reason_line = f"\nПричина: {reason}" if reason else ""
    await _tg_send(target_id, f"🚫 <b>Ваш аккаунт STAR VPN заблокирован.</b>{reason_line}\nПо вопросам — обратитесь в поддержку.")
    return {"ok": True}


# ─── POST /api/admin/unban ───────────────────────────────────────────────────
@app.post("/api/admin/unban")
async def admin_unban(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    tg_id = _tg_id(x_telegram_init_data)
    _require_admin(tg_id)
    body = await request.json()
    target_id = int(body.get("telegram_id", 0))

    async with AsyncSessionLocal() as session:
        r = await session.execute(select(User).where(User.telegram_id == target_id))
        user: User | None = r.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found")
        user.is_banned = False
        user.ban_reason = None
        if user.marzban_username:
            try:
                await marzban.enable_user(user.marzban_username)
            except Exception:
                pass
        await session.commit()

    await _tg_send(target_id, "✅ Ваш аккаунт STAR VPN разблокирован.")
    return {"ok": True}


# ─── POST /api/admin/message ─────────────────────────────────────────────────
@app.post("/api/admin/message")
async def admin_message(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    tg_id = _tg_id(x_telegram_init_data)
    _require_admin(tg_id)
    body = await request.json()
    target_id = int(body.get("telegram_id", 0))
    text = (body.get("text") or "").strip()
    if not target_id or not text:
        raise HTTPException(400, "telegram_id and text required")

    await _tg_send(target_id, text)
    return {"ok": True}


# ─── POST /api/admin/broadcast ───────────────────────────────────────────────
@app.post("/api/admin/broadcast")
async def admin_broadcast(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    tg_id = _tg_id(x_telegram_init_data)
    _require_admin(tg_id)
    body = await request.json()
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "text required")

    async with AsyncSessionLocal() as session:
        ids = list((await session.execute(
            select(User.telegram_id).where(User.is_banned.is_(False))
        )).scalars().all())

    sent = failed = 0
    async with httpx.AsyncClient(timeout=10) as client:
        for uid in ids:
            try:
                await client.post(
                    f"https://api.telegram.org/bot{settings.telegram_api_token}/sendMessage",
                    json={"chat_id": uid, "text": text, "parse_mode": "HTML"},
                )
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.05)

    return {"ok": True, "sent": sent, "failed": failed}


# ─── GET /api/admin/payments ─────────────────────────────────────────────────
@app.get("/api/admin/payments")
async def admin_payments(x_telegram_init_data: str | None = Header(default=None)):
    tg_id = _tg_id(x_telegram_init_data)
    _require_admin(tg_id)

    async with AsyncSessionLocal() as session:
        r = await session.execute(
            select(Payment).where(Payment.status == "paid")
            .order_by(Payment.paid_at.desc()).limit(20)
        )
        payments = r.scalars().all()

    return [
        {
            "id": p.id,
            "telegram_id": p.telegram_id,
            "amount": int(p.amount),
            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            "order_id": p.order_id or "",
        }
        for p in payments
    ]




# ═══════════════════════════════════════════════════════════════
# PAYMENT INVOICE ENDPOINTS (для Mini App)
# ═══════════════════════════════════════════════════════════════

_PLANS_API = {
    "plan_1m": {"days": 30,  "stars": 99,  "label": "1 месяц",   "desc": "30 дней безлимитного VPN"},
    "plan_3m": {"days": 90,  "stars": 249, "label": "3 месяца",  "desc": "90 дней · скидка 16%"},
    "plan_6m": {"days": 180, "stars": 449, "label": "6 месяцев", "desc": "180 дней · скидка 25%"},
}


async def _create_tg_invoice(title: str, description: str, payload: str, stars: int) -> str:
    """Создаёт invoice link через Telegram Bot API и возвращает URL."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{settings.telegram_api_token}/createInvoiceLink",
            json={
                "title": title,
                "description": description,
                "payload": payload,
                "currency": "XTR",
                "prices": [{"label": title, "amount": stars}],
            },
        )
    data = resp.json()
    if not data.get("ok"):
        raise HTTPException(500, f"Telegram invoice error: {data.get('description', 'unknown')}")
    return data["result"]


# ─── POST /api/invoice/renew ─────────────────────────────────────────────────

@app.post("/api/invoice/renew")
async def invoice_renew(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    """Создать invoice для продления/покупки подписки."""
    _tg_id(x_telegram_init_data)  # только проверяем auth
    body = await request.json()
    plan_key = (body.get("plan") or "").strip()
    plan = _PLANS_API.get(plan_key)
    if not plan:
        raise HTTPException(400, "Invalid plan key")

    url = await _create_tg_invoice(
        title=f"STAR VPN — {plan['label']}",
        description=plan["desc"],
        payload=plan_key,
        stars=plan["stars"],
    )
    return {"url": url}


# ─── POST /api/invoice/gift ──────────────────────────────────────────────────

@app.post("/api/invoice/gift")
async def invoice_gift(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    """Создать invoice для подарка подписки."""
    tg_id = _tg_id(x_telegram_init_data)
    body = await request.json()
    plan_key = (body.get("plan") or "").strip()
    recipient_input = (body.get("recipient") or "").strip()
    anon = "1" if body.get("anon") else "0"
    personal_message = (body.get("message") or "").strip()[:300]

    plan = _PLANS_API.get(plan_key)
    if not plan:
        raise HTTPException(400, "Invalid plan key")
    if not recipient_input:
        raise HTTPException(400, "Recipient required")

    # Поиск получателя в БД
    async with AsyncSessionLocal() as session:
        if recipient_input.lstrip("-").isdigit():
            r = await session.execute(
                select(User).where(User.telegram_id == int(recipient_input))
            )
        else:
            r = await session.execute(
                select(User).where(User.username == recipient_input.lstrip("@"))
            )
        recipient: User | None = r.scalar_one_or_none()

    if not recipient:
        raise HTTPException(404, "Получатель не найден. Попроси его написать /start боту.")
    if recipient.telegram_id == tg_id:
        raise HTTPException(400, "Нельзя подарить подписку самому себе.")

    # Сохраняем (или очищаем) личное сообщение — используем тот же
    # _pending_messages из gift.py. Всегда пишем ключ явно, а не только когда
    # сообщение непустое, иначе повторный подарок этому же получателю без
    # сообщения подхватит старое, оставшееся от прошлого инвойса (см. тот же
    # фикс в bot/handlers/gift.py::_send_gift_invoice).
    from bot.handlers.gift import _pending_messages
    pending_key = f"{tg_id}:{recipient.telegram_id}"
    if personal_message:
        _pending_messages[pending_key] = personal_message
    else:
        _pending_messages.pop(pending_key, None)

    payload = f"gift:{plan_key}:{recipient.telegram_id}:{anon}"
    uname = f"@{recipient.username}" if recipient.username else str(recipient.telegram_id)

    url = await _create_tg_invoice(
        title=f"🎁 Подарок STAR VPN — {plan['label']}",
        description=f"Подарочная подписка для {uname} на {plan['days']} дней",
        payload=payload,
        stars=plan["stars"],
    )
    return {"url": url, "recipient_name": uname}


# ─── POST /api/invoice/gift/crypto ───────────────────────────────────────────

@app.post("/api/invoice/gift/crypto")
async def create_gift_crypto_invoice(
    request: Request,
    x_telegram_init_data: str | None = Header(default=None),
):
    """Создаёт крипто-инвойс для подарка подписки (мини-апп)."""
    tg_id = _tg_id(x_telegram_init_data)
    body = await request.json()
    plan_key = (body.get("plan") or "").strip()
    recipient_input = (body.get("recipient") or "").strip()
    anon = "1" if body.get("anon") else "0"
    personal_message = (body.get("message") or "").strip()[:300]

    from bot.utils.cryptopay import cryptopay, CRYPTO_PLANS
    plan = CRYPTO_PLANS.get(plan_key)
    if not plan:
        raise HTTPException(400, "Неизвестный тариф")
    if not recipient_input:
        raise HTTPException(400, "Получатель обязателен")

    # Поиск получателя
    async with AsyncSessionLocal() as session:
        if recipient_input.lstrip("-").isdigit():
            r = await session.execute(
                select(User).where(User.telegram_id == int(recipient_input))
            )
        else:
            r = await session.execute(
                select(User).where(User.username == recipient_input.lstrip("@"))
            )
        recipient: User | None = r.scalar_one_or_none()

    if not recipient:
        raise HTTPException(404, "Получатель не найден. Попроси его написать /start боту.")
    if recipient.telegram_id == tg_id:
        raise HTTPException(400, "Нельзя подарить самому себе.")

    # Сохраняем (или очищаем) личное сообщение — см. фикс выше в
    # /api/invoice/gift для того же issue.
    from bot.handlers.gift import _pending_messages
    pending_key = f"{tg_id}:{recipient.telegram_id}"
    if personal_message:
        _pending_messages[pending_key] = personal_message
    else:
        _pending_messages.pop(pending_key, None)

    uname = f"@{recipient.username}" if recipient.username else str(recipient.telegram_id)
    payload_str = f"gift:{plan_key}:{recipient.telegram_id}:{anon}:{tg_id}"

    try:
        invoice = await cryptopay.create_invoice(
            usd_amount=plan["usd"],
            payload=payload_str,
            description=f"STAR VPN — подарок {plan['label']} для {uname}",
        )
    except Exception as e:
        logger.error("CryptoPay gift invoice error: %s", e)
        raise HTTPException(502, "Ошибка CryptoPay. Попробуй позже.")

    invoice_id = invoice.get("invoice_id")
    pay_url = invoice.get("bot_invoice_url") or invoice.get("mini_app_invoice_url", "")

    async with AsyncSessionLocal() as session:
        payment = Payment(
            order_id=f"crypto_gift_{invoice_id}",
            telegram_id=tg_id,
            amount=float(plan["usd"]),
            status="pending",
            payment_method="crypto",
            invoice_id=invoice_id,
            days=plan["days"],
        )
        session.add(payment)
        await session.commit()

    return {"url": pay_url, "recipient_name": uname}


# ─── Подарок с сайта (личный кабинет) — только карта, без Stars ─────────────

async def _lookup_gift_recipient(recipient_input: str, session: AsyncSession) -> User | None:
    recipient_input = recipient_input.strip()
    if not recipient_input:
        return None
    if recipient_input.lstrip("-").isdigit():
        r = await session.execute(select(User).where(User.telegram_id == int(recipient_input)))
    else:
        r = await session.execute(select(User).where(User.username == recipient_input.lstrip("@")))
    return r.scalar_one_or_none()


@app.post("/api/gift/lookup")
async def gift_lookup(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    """Проверяет получателя подарка по @username или ID, до перехода к оплате."""
    body = await request.json()
    recipient_input = (body.get("recipient") or "").strip()
    if not recipient_input:
        raise HTTPException(400, "Укажите получателя")

    async with AsyncSessionLocal() as session:
        tg_id = await _resolve_tg_id(request, x_telegram_init_data, session)
        recipient = await _lookup_gift_recipient(recipient_input, session)

    if not recipient or recipient.telegram_id <= 0:
        raise HTTPException(404, "Получатель не найден. Он должен сначала написать /start боту @starisvpnbot.")
    if recipient.telegram_id == tg_id:
        raise HTTPException(400, "Нельзя подарить подписку самому себе.")

    uname = f"@{recipient.username}" if recipient.username else str(recipient.telegram_id)
    return {"telegram_id": recipient.telegram_id, "display_name": uname}


def _new_gift_link_code() -> str:
    return secrets.token_urlsafe(9).replace("-", "").replace("_", "")[:11]


@app.post("/api/gift/invoice")
async def gift_invoice(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    """
    Создаёт подарочный платёж с сайта (личный кабинет) — картой.
    Stars здесь недоступны — это оплата только внутри Telegram.

    Если recipient не указан — это подарок "по ссылке": получатель ещё
    неизвестен, платёж временно висит на самом отправителе (gift_sender_id),
    а после оплаты становится доступен на /gift/{code} — кто угодно
    открывает ссылку и забирает подарок под своим аккаунтом.
    """
    body = await request.json()
    provider = (body.get("provider") or "").strip()
    plan_key = (body.get("plan") or "").strip()
    recipient_input = (body.get("recipient") or "").strip()
    anon = bool(body.get("anon"))
    message = (body.get("message") or "").strip()[:300]
    link_mode = not recipient_input

    if provider != "card":
        raise HTTPException(400, "Неизвестный способ оплаты")

    from bot.utils.settings_store import is_provider_enabled

    async with AsyncSessionLocal() as session:
        tg_id = await _resolve_tg_id(request, x_telegram_init_data, session)

        if not await is_provider_enabled(session, provider):
            raise HTTPException(503, "Этот способ оплаты временно недоступен")

        gift_link_code = None
        if link_mode:
            recipient_tg_id = tg_id  # временный держатель записи, пока подарок не заберут
            uname = "по ссылке"
            gift_desc_suffix = "по ссылке"
            gift_link_code = _new_gift_link_code()
        else:
            recipient = await _lookup_gift_recipient(recipient_input, session)
            if not recipient or recipient.telegram_id <= 0:
                raise HTTPException(404, "Получатель не найден. Он должен сначала написать /start боту @starisvpnbot.")
            if recipient.telegram_id == tg_id:
                raise HTTPException(400, "Нельзя подарить подписку самому себе.")
            recipient_tg_id = recipient.telegram_id
            uname = f"@{recipient.username}" if recipient.username else str(recipient.telegram_id)
            gift_desc_suffix = f"для {uname}"

        from bot.utils.robokassa import robokassa, CARD_PLANS, payment_inv_id
        plan = CARD_PLANS.get(plan_key)
        if not plan:
            raise HTTPException(400, "Неизвестный тариф")
        if not robokassa.configured:
            raise HTTPException(503, "Оплата картой временно недоступна")

        payment = Payment(
            # Placeholder must be unique (order_id has a UNIQUE constraint) —
            # a shared "" would raise IntegrityError if two card checkouts
            # (site or gift) flush concurrently, before either gets a real id.
            order_id=f"card_pending_{secrets.token_hex(16)}",
            telegram_id=recipient_tg_id, amount=float(plan["rub"]),
            status="pending", payment_method="card", days=plan["days"],
            is_gift=True, gift_sender_id=tg_id, gift_anon=anon, gift_message=message,
            gift_link_code=gift_link_code,
        )
        session.add(payment)
        await session.flush()
        payment.order_id = f"card_{payment.id}"
        try:
            pay_url = robokassa.build_payment_url(
                inv_id=payment_inv_id(payment.id),
                amount=plan["rub"],
                description=f"STAR VPN — подарок {plan['label']} {gift_desc_suffix}",
            )
        except RuntimeError as e:
            await session.rollback()
            logger.error("Robokassa gift build_payment_url failed: %s", e)
            raise HTTPException(502, "Ошибка Robokassa. Попробуйте позже.")

        await session.commit()
        inv_id = payment.id

    result = {"url": pay_url, "invoice_id": inv_id, "recipient_name": uname}
    if gift_link_code:
        result["gift_link"] = f"{settings.site_url}/gift/{gift_link_code}"
    return result


_GIFT_PLAN_LABELS = {30: "1 месяц", 90: "3 месяца", 180: "6 месяцев"}


@app.get("/gift/{code}", include_in_schema=False)
async def gift_reveal_page(code: str):
    """Публичная страница-открытка для подарка по ссылке — см. /api/gift/link/{code}."""
    return _serve_html(_LANDING_DIR / "gift-reveal.html")


@app.get("/api/gift/link/{code}")
async def gift_link_status(code: str):
    """Публичный статус подарка по ссылке — без авторизации, для анимации на /gift/{code}."""
    async with AsyncSessionLocal() as session:
        r = await session.execute(
            select(Payment).where(Payment.gift_link_code == code, Payment.is_gift.is_(True))
        )
        payment: Payment | None = r.scalar_one_or_none()
        if not payment:
            return {"status": "not_found"}
        if payment.status != "paid":
            return {"status": "pending"}
        if payment.gift_claimed:
            return {"status": "claimed"}

        days = payment.days or 30
        plan_label = _GIFT_PLAN_LABELS.get(days, f"{days} дней")
        sender_name = "Аноним"
        if not payment.gift_anon and payment.gift_sender_id:
            sr = await session.execute(select(User).where(User.telegram_id == payment.gift_sender_id))
            sender: User | None = sr.scalar_one_or_none()
            if sender:
                sender_name = f"@{sender.username}" if sender.username else (sender.full_name or "пользователь")

        return {
            "status": "ready",
            "plan_days": days,
            "plan_label": plan_label,
            "sender_name": sender_name,
            "message": payment.gift_message or "",
        }


@app.post("/api/gift/link/{code}/claim")
async def gift_link_claim(code: str, request: Request, x_telegram_init_data: str | None = Header(default=None)):
    """Забрать подарок по ссылке — требует авторизации (Mini App или /login),
    поэтому фронт на 401 должен предложить войти и вернуться на эту же ссылку."""
    async with AsyncSessionLocal() as session:
        tg_id = await _resolve_tg_id(request, x_telegram_init_data, session)

        r = await session.execute(
            select(Payment).where(Payment.gift_link_code == code, Payment.is_gift.is_(True))
        )
        payment: Payment | None = r.scalar_one_or_none()
        if not payment:
            raise HTTPException(404, "Подарок не найден")
        if payment.status != "paid":
            raise HTTPException(409, "Дарящий ещё не завершил оплату")
        if payment.gift_claimed:
            raise HTTPException(409, "Этот подарок уже кто-то забрал")
        if payment.gift_sender_id == tg_id:
            raise HTTPException(400, "Нельзя забрать свой же подарок")

        from bot.handlers.payment import _grant_subscription
        from bot.utils.webauth import get_or_create_user_by_telegram_id

        claimant = await get_or_create_user_by_telegram_id(tg_id, None, None, session)
        days = payment.days or 30
        await _grant_subscription(claimant, days, session)

        payment.gift_claimed = True
        payment.telegram_id = tg_id
        await session.commit()

        plan_label = _GIFT_PLAN_LABELS.get(days, f"{days} дней")
        sender_name = "Аноним"
        if not payment.gift_anon and payment.gift_sender_id:
            sr = await session.execute(select(User).where(User.telegram_id == payment.gift_sender_id))
            sender: User | None = sr.scalar_one_or_none()
            if sender:
                sender_name = f"@{sender.username}" if sender.username else (sender.full_name or "пользователь")

        notif = GiftNotification(
            recipient_id=tg_id, sender_name=sender_name, plan_label=plan_label, plan_days=days,
        )
        session.add(notif)
        await session.commit()

        if payment.gift_sender_id and payment.gift_sender_id > 0:
            from aiogram import Bot
            bot = Bot(token=settings.telegram_api_token)
            try:
                await bot.send_message(
                    payment.gift_sender_id,
                    f"✅ <b>Подарок забрали по ссылке!</b>\n\n"
                    f"📦 Тариф: <b>{plan_label}</b>\n"
                    f"Получатель уже пользуется VPN 🎉",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning("Gift-link sender notify failed: %s", e)
            finally:
                try:
                    await bot.session.close()
                except Exception:
                    pass

    return {"ok": True, "plan_label": plan_label, "plan_days": days}


# ─── POST /api/trial ─────────────────────────────────────────────────────────

@app.post("/api/trial")
async def activate_trial_api(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    """Активировать пробный период (2 дня). Только один раз на аккаунт.
    Работает и для Mini App (initData), и для веб-аккаунта (star_session cookie)."""
    async with AsyncSessionLocal() as session:
        tg_id = await _resolve_tg_id(request, x_telegram_init_data, session)
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user: User | None = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        if user.trial_used:
            raise HTTPException(status_code=400, detail="Пробный период уже был активирован")

        from datetime import timedelta
        user.trial_used = True
        user.subscription_expires_at = datetime.utcnow() + timedelta(days=settings.trial_days)
        await session.commit()

        return {"ok": True, "days": settings.trial_days}


# ─── GET /api/plans ──────────────────────────────────────────────────────────

@app.get("/api/plans")
async def get_plans(x_telegram_init_data: str | None = Header(default=None)):
    _tg_id(x_telegram_init_data)
    return [
        {"key": k, "label": v["label"], "stars": v["stars"], "days": v["days"], "desc": v["desc"]}
        for k, v in _PLANS_API.items()
    ]


# ─── GET /api/gift/pending ───────────────────────────────────────────────────

@app.get("/api/gift/pending")
async def gift_pending(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    """Вернуть непрочитанное уведомление о подарке (или null).
    Работает и для Mini App (initData), и для веб-аккаунта (star_session cookie)."""
    async with AsyncSessionLocal() as session:
        tg_id = await _resolve_tg_id(request, x_telegram_init_data, session)
        r = await session.execute(
            select(GiftNotification)
            .where(
                GiftNotification.recipient_id == tg_id,
                GiftNotification.seen.is_(False),
            )
            .order_by(GiftNotification.created_at.desc())
            .limit(1)
        )
        notif: GiftNotification | None = r.scalar_one_or_none()

    if not notif:
        return {"gift": None}
    return {
        "gift": {
            "id": notif.id,
            "sender_name": notif.sender_name,
            "plan_label": notif.plan_label,
            "plan_days": notif.plan_days,
        }
    }


# ─── POST /api/gift/seen ─────────────────────────────────────────────────────

@app.post("/api/gift/seen")
async def gift_seen(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    """Пометить уведомление о подарке как прочитанное.
    Работает и для Mini App (initData), и для веб-аккаунта (star_session cookie)."""
    body = await request.json()
    notif_id = int(body.get("id", 0))

    async with AsyncSessionLocal() as session:
        tg_id = await _resolve_tg_id(request, x_telegram_init_data, session)
        r = await session.execute(
            select(GiftNotification).where(
                GiftNotification.id == notif_id,
                GiftNotification.recipient_id == tg_id,
            )
        )
        notif: GiftNotification | None = r.scalar_one_or_none()
        if notif:
            notif.seen = True
            await session.commit()

    return {"ok": True}


# GET /api/crypto/plans and POST /api/invoice/crypto used to be defined here
# a second time (a leftover from an earlier Mini-App-only pass) with the same
# paths as the "site" versions further down — Starlette matches routes in
# registration order, so this earlier pair silently shadowed the later ones,
# which are the only ones that support cookie-session auth (_resolve_tg_id).
# That made the website's own crypto checkout 401 in practice. Removed;
# see the "(сайт/личный кабинет)" versions below, which now serve both.


# ─── POST /crypto/webhook ────────────────────────────────────────────────────

@app.post("/crypto/webhook", include_in_schema=False)
async def crypto_webhook(request: Request):
    """
    Webhook от CryptoPay (@CryptoBot).
    Заголовок: crypto-pay-api-signature (HMAC-SHA256).
    При успешной оплате → выдаём подписку → уведомляем пользователя.
    """
    from bot.utils.cryptopay import cryptopay
    from bot.handlers.crypto_payment import handle_crypto_webhook
    from aiogram import Bot

    signature = request.headers.get("crypto-pay-api-signature", "")
    body_bytes = await request.body()

    # Верификация подписи
    if not cryptopay.check_signature(body_bytes, signature):
        logger.warning("Crypto webhook: invalid signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        data = json.loads(body_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Bad JSON")

    update_type = data.get("update_type")
    if update_type != "invoice_paid":
        # Другие события игнорируем
        return {"ok": True}

    payload_obj = data.get("payload", {})
    invoice_id = payload_obj.get("invoice_id")
    asset = payload_obj.get("asset", "USDT")
    status = payload_obj.get("status")
    invoice_payload = payload_obj.get("payload", "")  # наш payload: "plan:tg_id" или "gift:..."

    if status != "paid" or not invoice_id:
        return {"ok": True}

    # Выдаём подписку / подарок
    bot = Bot(token=settings.telegram_api_token)
    try:
        await handle_crypto_webhook(
            invoice_id=int(invoice_id),
            asset=asset,
            bot=bot,
            invoice_payload=invoice_payload,
        )
    except Exception as e:
        logger.error("handle_crypto_webhook error: %s", e)
    finally:
        try:
            await bot.session.close()
        except Exception:
            pass

    return {"ok": True}


# ─── GET /api/card/plans ──────────────────────────────────────────────────────

@app.get("/api/card/plans")
async def get_card_plans(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    """Тарифы для оплаты картой (RUB). Возвращает [] если Robokassa не настроена или отключена в админке."""
    from bot.utils.settings_store import is_provider_enabled
    async with AsyncSessionLocal() as session:
        await _resolve_tg_id(request, x_telegram_init_data, session)
        if not await is_provider_enabled(session, "card"):
            return []
    from bot.utils.robokassa import robokassa, CARD_PLANS
    if not robokassa.configured:
        return []
    return [
        {
            "key": k,
            "label": v["label"],
            "rub": float(v["rub"]),
            "days": v["days"],
            "desc": v["desc"],
        }
        for k, v in CARD_PLANS.items()
    ]


# ─── POST /api/invoice/card ───────────────────────────────────────────────────

@app.post("/api/invoice/card")
async def create_card_invoice(
    request: Request,
    x_telegram_init_data: str | None = Header(default=None),
):
    """Создаёт pending-платёж и подписанную ссылку Robokassa (мини-апп).

    Принимает либо {"plan": "plan_1m"} (фиксированный тариф), либо
    {"days": N} (7..180, произвольный срок — та же формула цены,
    что и в гостевом чекауте, см. robokassa.custom_plan_price)."""
    body = await request.json()
    plan_key = body.get("plan")
    custom_days = body.get("days")

    from bot.utils.robokassa import (
        robokassa, CARD_PLANS, CUSTOM_DAYS_MIN, CUSTOM_DAYS_MAX, custom_plan_price,
    )
    if plan_key:
        plan_days = CARD_PLANS[plan_key]["days"] if plan_key in CARD_PLANS else None
        if plan_days is None:
            raise HTTPException(status_code=400, detail="Неизвестный тариф")
        rub = CARD_PLANS[plan_key]["rub"]
        label = CARD_PLANS[plan_key]["label"]
    elif isinstance(custom_days, int) and CUSTOM_DAYS_MIN <= custom_days <= CUSTOM_DAYS_MAX:
        plan_days = custom_days
        rub = custom_plan_price(custom_days)
        label = f"{custom_days} дней"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Укажите тариф или срок от {CUSTOM_DAYS_MIN} до {CUSTOM_DAYS_MAX} дней",
        )
    if not robokassa.configured:
        raise HTTPException(status_code=503, detail="Оплата картой временно недоступна")

    from bot.utils.settings_store import is_provider_enabled
    async with AsyncSessionLocal() as session:
        tg_id = await _resolve_tg_id(request, x_telegram_init_data, session)
        if not await is_provider_enabled(session, "card"):
            raise HTTPException(status_code=503, detail="Оплата картой временно недоступна")
        payment = Payment(
            # See the gift-invoice card path above for why this can't be "".
            order_id=f"card_pending_{secrets.token_hex(16)}",
            telegram_id=tg_id,
            amount=float(rub),
            status="pending",
            payment_method="card",
            days=plan_days,
        )
        session.add(payment)
        await session.flush()
        payment.order_id = f"card_{payment.id}"

        try:
            from bot.utils.robokassa import payment_inv_id
            pay_url = robokassa.build_payment_url(
                inv_id=payment_inv_id(payment.id),
                amount=rub,
                description=f"STAR VPN - {label}",
            )
        except RuntimeError as e:
            await session.rollback()
            logger.error("Robokassa build_payment_url failed: %s", e)
            raise HTTPException(status_code=502, detail="Ошибка Robokassa. Попробуйте позже.")

        await session.commit()
        inv_id = payment.id

    return {"url": pay_url, "invoice_id": inv_id}


# ─── GET /api/crypto/plans, POST /api/invoice/crypto (сайт/личный кабинет) ───

@app.get("/api/crypto/plans")
async def get_crypto_plans_api(request: Request, x_telegram_init_data: str | None = Header(default=None)):
    """Тарифы для оплаты криптовалютой (USD, через @CryptoBot). Возвращает []
    если CryptoPay не настроен или отключён в админке."""
    from bot.utils.settings_store import is_provider_enabled
    async with AsyncSessionLocal() as session:
        await _resolve_tg_id(request, x_telegram_init_data, session)
        if not await is_provider_enabled(session, "crypto"):
            return []
    from bot.utils.cryptopay import cryptopay, CRYPTO_PLANS
    if not cryptopay.configured:
        return []
    return [
        {"key": k, "label": v["label"], "usd": float(v["usd"]), "days": v["days"], "desc": v["desc"]}
        for k, v in CRYPTO_PLANS.items()
    ]


@app.post("/api/invoice/crypto")
async def create_crypto_invoice_api(
    request: Request,
    x_telegram_init_data: str | None = Header(default=None),
):
    """Создаёт CryptoPay-инвойс для личного кабинета/сайта — тот же payload
    "{plan_key}:{tg_id}", что и в bot/handlers/crypto_payment.py, поэтому
    его обрабатывает тот же /crypto/webhook без отдельной ветки."""
    body = await request.json()
    plan_key = body.get("plan")

    from bot.utils.cryptopay import cryptopay, CRYPTO_PLANS
    plan = CRYPTO_PLANS.get(plan_key)
    if not plan:
        raise HTTPException(status_code=400, detail="Неизвестный тариф")
    if not cryptopay.configured:
        raise HTTPException(status_code=503, detail="Оплата криптовалютой временно недоступна")

    from bot.utils.settings_store import is_provider_enabled
    async with AsyncSessionLocal() as session:
        tg_id = await _resolve_tg_id(request, x_telegram_init_data, session)
        if not await is_provider_enabled(session, "crypto"):
            raise HTTPException(status_code=503, detail="Оплата криптовалютой временно недоступна")

        try:
            invoice = await cryptopay.create_invoice(
                usd_amount=plan["usd"],
                payload=f"{plan_key}:{tg_id}",
                description=f"STAR VPN - {plan['label']}",
                paid_btn_name="callback",
                paid_btn_url=f"{settings.site_url}/account",
            )
        except Exception as e:
            logger.error("CryptoPay invoice (site) failed for tg=%s: %s", tg_id, e)
            raise HTTPException(status_code=502, detail="Ошибка CryptoPay. Попробуйте позже.")

        invoice_id = invoice.get("invoice_id")
        pay_url = invoice.get("bot_invoice_url") or invoice.get("mini_app_invoice_url", "")

        payment = Payment(
            order_id=f"crypto_{invoice_id}",
            telegram_id=tg_id,
            amount=float(plan["usd"]),
            status="pending",
            payment_method="crypto",
            invoice_id=invoice_id,
            days=plan["days"],
        )
        session.add(payment)
        await session.commit()

    return {"url": pay_url, "invoice_id": invoice_id}


# ─── Гостевые заказы (покупка без Telegram, с лендинга) ──────────────────────

@app.get("/api/guest/plans")
async def get_guest_plans():
    """Тарифы для покупки без Telegram. Публичный эндпоинт — initData не нужен."""
    from bot.utils.robokassa import robokassa, CARD_PLANS
    from bot.utils.settings_store import get_all_provider_states
    async with AsyncSessionLocal() as session:
        states = await get_all_provider_states(session)
    card_available = robokassa.configured and states["card"]
    if not card_available:
        return []
    return [
        {"key": k, "label": v["label"], "rub": float(v["rub"]), "days": v["days"], "desc": v["desc"]}
        for k, v in CARD_PLANS.items()
    ]


@app.get("/api/guest/providers")
async def get_guest_providers():
    """Какие способы оплаты доступны для покупки без Telegram."""
    from bot.utils.robokassa import robokassa
    from bot.utils.settings_store import get_all_provider_states
    async with AsyncSessionLocal() as session:
        states = await get_all_provider_states(session)
    return {
        "robokassa": robokassa.configured and states["card"],
    }


@app.post("/api/guest/checkout")
async def guest_checkout(request: Request):
    """
    Создаёт гостевой заказ и подписанную ссылку на оплату Robokassa.
    Публичный — для покупки VPN прямо с сайта, без Telegram (initData не требуется).
    """
    import uuid
    from bot.models.guest_order import GuestOrder
    from bot.utils.robokassa import (
        robokassa, CARD_PLANS, guest_inv_id,
        CUSTOM_DAYS_MIN, CUSTOM_DAYS_MAX, custom_plan_price,
    )

    body = await request.json()
    plan_key = body.get("plan")
    if plan_key == "custom":
        days = body.get("days")
        if not isinstance(days, int) or not (CUSTOM_DAYS_MIN <= days <= CUSTOM_DAYS_MAX):
            raise HTTPException(
                status_code=400,
                detail=f"Срок должен быть от {CUSTOM_DAYS_MIN} до {CUSTOM_DAYS_MAX} дней",
            )
        plan = {"days": days, "rub": custom_plan_price(days), "label": f"{days} дней"}
    else:
        plan = CARD_PLANS.get(plan_key)
        if not plan:
            raise HTTPException(status_code=400, detail="Неизвестный тариф")

    from bot.utils.settings_store import is_provider_enabled
    async with AsyncSessionLocal() as session:
        if not await is_provider_enabled(session, "card"):
            raise HTTPException(status_code=503, detail="Этот способ оплаты временно недоступен")

    async with AsyncSessionLocal() as session:
        order = GuestOrder(
            public_id=str(uuid.uuid4()),
            plan_key=body["plan"],
            days=plan["days"],
            amount=float(plan["rub"]),
            status="pending",
        )
        session.add(order)
        await session.flush()

        try:
            if not robokassa.configured:
                raise HTTPException(status_code=503, detail="Оплата картой временно недоступна")
            pay_url = robokassa.build_payment_url(
                inv_id=guest_inv_id(order.id),
                amount=plan["rub"],
                description=f"STAR VPN - {plan['label']} (сайт)",
            )
        except RuntimeError as e:
            await session.rollback()
            logger.error("build_payment_url (guest) failed: %s", e)
            raise HTTPException(status_code=502, detail="Ошибка платёжной системы. Попробуйте позже.")
        except HTTPException:
            await session.rollback()
            raise

        await session.commit()
        public_id = order.public_id

    return {"url": pay_url, "order_id": public_id}


@app.get("/api/guest/order/{public_id}")
async def guest_order_status(public_id: str):
    """Поллится страницей успеха, пока вебхук не подтвердит оплату."""
    from bot.models.guest_order import GuestOrder

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(GuestOrder).where(GuestOrder.public_id == public_id))
        order: GuestOrder | None = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")

        return {
            "status": order.status,
            "link": order.vless_link,
            "qr_url": (
                f"https://api.qrserver.com/v1/create-qr-code/?size=240x240&data={urllib.parse.quote(order.vless_link)}"
                if order.vless_link else None
            ),
        }


async def _fulfill_guest_order(order_id: int) -> None:
    """Создаёт Marzban-пользователя для гостевого заказа и сохраняет ключ."""
    from datetime import datetime
    from bot.models.guest_order import GuestOrder

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(GuestOrder).where(GuestOrder.id == order_id, GuestOrder.status == "pending")
        )
        order: GuestOrder | None = result.scalar_one_or_none()
        if not order:
            logger.warning("Guest webhook: pending order not found for id=%s", order_id)
            return

        mz_username = f"web_{order.public_id[:8]}"
        try:
            mz_user = await marzban.create_user(
                telegram_id=0,
                days=order.days,
                note=f"guest_order:{order.public_id}",
                ip_limit=1,
                username=mz_username,
            )
            link = marzban.extract_vless_link(mz_user) or ""
            link = _set_vless_remark(link)
        except Exception as e:
            logger.error("Guest order %s: Marzban create_user failed: %s", order.public_id, e)
            return

        order.status = "paid"
        order.marzban_username = mz_username
        order.vless_link = link
        order.paid_at = datetime.utcnow()
        await session.commit()

    logger.info("Guest order fulfilled: public_id=%s rub=%s days=%s", order.public_id, order.amount, order.days)


# ─── POST /card/webhook (Robokassa ResultURL) ────────────────────────────────

@app.post("/card/webhook", include_in_schema=False)
async def card_webhook(request: Request):
    """
    ResultURL от Robokassa (server-to-server, application/x-www-form-urlencoded).
    Подпись: MD5(OutSum:InvId:Password#2).
    Один InvId на два вида платежей — см. decode_inv_id: чётный/нечётный
    разделяет обычные Telegram-платежи (Payment) и гостевые заказы (GuestOrder).
    Обязан ответить строкой "OK{InvId}" — иначе Robokassa повторит запрос.
    """
    from bot.utils.robokassa import robokassa, decode_inv_id
    from bot.handlers.card_payment import handle_card_webhook
    from aiogram import Bot

    form = await request.form()
    out_sum = form.get("OutSum", "")
    inv_id = form.get("InvId", "")
    signature = form.get("SignatureValue", "")

    if not robokassa.check_result_signature(out_sum, inv_id, signature):
        logger.warning("Robokassa webhook: invalid signature for InvId=%s", inv_id)
        raise HTTPException(status_code=403, detail="Invalid signature")

    kind, real_id = decode_inv_id(int(inv_id))

    if kind == "guest":
        try:
            await _fulfill_guest_order(real_id)
        except Exception as e:
            logger.error("_fulfill_guest_order error: %s", e)
        return PlainTextResponse(f"OK{inv_id}")

    bot = Bot(token=settings.telegram_api_token)
    try:
        await handle_card_webhook(payment_id=real_id, bot=bot)
    except Exception as e:
        logger.error("handle_card_webhook error: %s", e)
    finally:
        try:
            await bot.session.close()
        except Exception:
            pass

    # Формат ответа фиксирован протоколом Robokassa.
    return PlainTextResponse(f"OK{inv_id}")


@app.get("/card/success", response_class=HTMLResponse, include_in_schema=False)
async def card_success():
    # Один SuccessURL обслуживает Robokassa, Telegram-платежи и
    # гостевые заказы с сайта. Различаем их на клиенте: если браузер,
    # вернувшийся с оплаты, это тот же браузер, что открывал чекаут на
    # /get-vpn, в localStorage будет лежать order_id гостевого заказа —
    # тогда поллим его статус и показываем QR + ключ прямо здесь, без Telegram.
    return _serve_html(_LANDING_DIR / "card-success.html")


@app.get("/card/fail", response_class=HTMLResponse, include_in_schema=False)
async def card_fail():
    return _serve_html(_LANDING_DIR / "card-fail.html")


# ═══════════════════════════════════════════════════════════════════
#  WEB ADMIN DASHBOARD — отдельная авторизация (не Telegram initData)
# ═══════════════════════════════════════════════════════════════════

def _web_auth(authorization: str | None):
    """Проверяет bearer-сессию админ-панели. Возвращает AdminIdentity —
    вызывающему коду не обязательно использовать возврат (большинство
    эндпоинтов просто гейтят доступ), но эндпоинты, которым нужен ранг
    вызывающего (например, приглашение), могут его забрать."""
    from bot.utils import admin_auth
    try:
        return admin_auth.check_session(authorization)
    except PermissionError:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.post("/web/register")
async def web_register(request: Request):
    """Первый вход в админ-панель — по инвайт-ключу (см. ADR-009).
    Мастер-ключ ADMIN_WEB_KEY даёт ранг 'admin' (с собственным invite_key
    для будущих приглашений); личный invite_key существующего 'admin' даёт
    ранг 'worker' (без права приглашать дальше)."""
    from bot.utils import admin_auth

    body = await request.json()
    invite_key = (body.get("invite_key") or "").strip()
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    if not invite_key:
        raise HTTPException(400, "Введите ключ доступа")
    if not (3 <= len(username) <= 64):
        raise HTTPException(400, "Логин должен быть от 3 до 64 символов")

    async with AsyncSessionLocal() as session:
        try:
            admin, token = await admin_auth.register_admin(invite_key, username, password, session)
        except ValueError as e:
            if str(e) == "username_taken":
                raise HTTPException(409, "Этот логин уже занят")
            if str(e) == "bad_invite_key":
                raise HTTPException(401, "Неверный ключ доступа")
            raise HTTPException(400, "Пароль должен быть от 8 символов")

    return {"ok": True, "token": token, "rank": admin.rank, "username": admin.username}


@app.post("/web/login")
async def web_login(request: Request):
    from bot.utils import admin_auth

    body = await request.json()
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    if not username or not password:
        raise HTTPException(400, "Введите логин и пароль")

    async with AsyncSessionLocal() as session:
        result = await admin_auth.login_admin(username, password, session)
    if not result:
        raise HTTPException(401, "Неверный логин или пароль")
    admin, token = result
    return {"ok": True, "token": token, "rank": admin.rank, "username": admin.username}


@app.post("/web/logout")
async def web_logout(authorization: str | None = Header(default=None)):
    from bot.utils import admin_auth
    async with AsyncSessionLocal() as session:
        await admin_auth.logout_admin(authorization, session)
    return {"ok": True}


@app.get("/web/me")
async def web_me(authorization: str | None = Header(default=None)):
    from bot.models.admin_account import AdminAccount as _AdminAccount
    identity = _web_auth(authorization)

    async with AsyncSessionLocal() as session:
        admin = (await session.execute(
            select(_AdminAccount).where(_AdminAccount.id == identity.admin_id)
        )).scalar_one_or_none()
        if not admin:
            raise HTTPException(404, "Not found")
        inviter_username = None
        if admin.invited_by_id:
            inviter = (await session.execute(
                select(_AdminAccount).where(_AdminAccount.id == admin.invited_by_id)
            )).scalar_one_or_none()
            inviter_username = inviter.username if inviter else None

    return {
        "username": admin.username,
        "rank": admin.rank,
        "invite_key": admin.invite_key,
        "invited_by": inviter_username,
        "created_at": admin.created_at.isoformat(),
    }


@app.get("/web/stats")
async def web_stats(authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    async with AsyncSessionLocal() as session:
        now = datetime.utcnow()
        total = (await session.execute(select(func.count(User.telegram_id)))).scalar_one()
        active = (await session.execute(
            select(func.count(User.telegram_id)).where(User.subscription_expires_at > now)
        )).scalar_one()
        banned = (await session.execute(
            select(func.count(User.telegram_id)).where(User.is_banned.is_(True))
        )).scalar_one()
        trial = (await session.execute(
            select(func.count(User.telegram_id)).where(User.trial_used.is_(True))
        )).scalar_one()
        stars = (await session.execute(select(func.sum(User.total_stars_paid)))).scalar_one() or 0
        pays = (await session.execute(
            select(func.count(Payment.id)).where(Payment.status == "paid")
        )).scalar_one()
        revenue_rows, new_rows = [], []
        for i in range(6, -1, -1):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            amt = (await session.execute(
                select(func.sum(Payment.amount)).where(Payment.status == "paid", Payment.paid_at >= day_start, Payment.paid_at < day_end)
            )).scalar_one() or 0
            cnt = (await session.execute(
                select(func.count(User.telegram_id)).where(User.created_at >= day_start, User.created_at < day_end)
            )).scalar_one() or 0
            label = day_start.strftime("%d.%m")
            revenue_rows.append({"date": label, "amount": float(amt)})
            new_rows.append({"date": label, "count": cnt})
    return {
        "total_users": total, "active_subscriptions": active, "banned": banned,
        "trial_used": trial, "total_stars": int(stars), "total_payments": pays,
        "online_now": -1, "revenue_chart": revenue_rows, "users_chart": new_rows,
    }


@app.get("/web/users")
async def web_users(
    limit: int = 200, offset: int = 0, q: str = "",
    status: str = "", sort: str = "created_at",
    authorization: str | None = Header(default=None),
):
    _web_auth(authorization)
    now = datetime.utcnow()
    async with AsyncSessionLocal() as session:
        query = select(User)
        if q:
            qs = q.strip().lstrip("@")
            if qs.lstrip("-").isdigit():
                query = query.where(User.telegram_id == int(qs))
            else:
                query = query.where(or_(User.username.ilike(f"%{qs}%"), User.full_name.ilike(f"%{qs}%")))
        if status == "active":
            query = query.where(User.subscription_expires_at > now, User.is_banned.is_(False))
        elif status == "banned":
            query = query.where(User.is_banned.is_(True))
        elif status == "trial":
            query = query.where(User.trial_used.is_(True))
        elif status == "expired":
            query = query.where(or_(User.subscription_expires_at.is_(None), User.subscription_expires_at <= now), User.is_banned.is_(False))
        sort_col = {"created_at": User.created_at, "stars": User.total_stars_paid, "refs": User.referral_count}.get(sort, User.created_at)
        count_query = query.with_only_columns(func.count(User.telegram_id)).order_by(None)
        total = (await session.execute(count_query)).scalar_one()
        users = (await session.execute(query.order_by(sort_col.desc()).limit(limit).offset(offset))).scalars().all()
    return {
        "total": total,
        "users": [{"telegram_id": u.telegram_id, "username": u.username or "", "full_name": u.full_name or "",
                   "email": u.email or "",
                   "is_banned": bool(u.is_banned), "ban_reason": u.ban_reason or "",
                   "subscription_active": bool(u.subscription_expires_at and u.subscription_expires_at > now),
                   "subscription_expires_at": u.subscription_expires_at.isoformat() if u.subscription_expires_at else None,
                   "days_left": max(0, (u.subscription_expires_at - now).days) if u.subscription_expires_at and u.subscription_expires_at > now else 0,
                   "total_stars_paid": int(u.total_stars_paid or 0), "referral_count": int(u.referral_count or 0),
                   "trial_used": bool(u.trial_used), "created_at": u.created_at.isoformat() if u.created_at else None,
                   "marzban_username": u.marzban_username or ""} for u in users],
    }


@app.get("/web/user/{tg_id}")
async def web_user_detail(tg_id: int, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    now = datetime.utcnow()
    async with AsyncSessionLocal() as session:
        u = (await session.execute(select(User).where(User.telegram_id == tg_id))).scalar_one_or_none()
        if not u:
            raise HTTPException(404, "User not found")
        # Только активные устройства из БД
        devs = (await session.execute(
            select(Device).where(Device.telegram_id == tg_id, Device.is_active.is_(True))
        )).scalars().all()
        pays = (await session.execute(
            select(Payment).where(Payment.telegram_id == tg_id, Payment.status == "paid").order_by(Payment.paid_at.desc()).limit(10)
        )).scalars().all()

        # Синхронизация с Marzban: убираем устройства которых там нет
        deactivated = False
        live_devs = []
        for d in devs:
            try:
                mz = await marzban.get_user(d.marzban_username)
                live_devs.append({"id": d.id, "name": d.name or "—",
                                  "marzban_username": d.marzban_username or "",
                                  "is_active": True,
                                  "status": mz.get("status", "unknown"),
                                  "expire": mz.get("expire"),
                                  "used_traffic": mz.get("used_traffic", 0)})
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    d.is_active = False
                    deactivated = True
                else:
                    live_devs.append({"id": d.id, "name": d.name or "—",
                                      "marzban_username": d.marzban_username or "",
                                      "is_active": True, "status": "unknown",
                                      "expire": None, "used_traffic": 0})
            except Exception:
                live_devs.append({"id": d.id, "name": d.name or "—",
                                  "marzban_username": d.marzban_username or "",
                                  "is_active": True, "status": "unknown",
                                  "expire": None, "used_traffic": 0})
        if deactivated:
            await session.commit()

    return {
        "telegram_id": u.telegram_id, "username": u.username or "", "full_name": u.full_name or "",
        "email": u.email or "",
        "is_banned": bool(u.is_banned), "ban_reason": u.ban_reason or "",
        "subscription_active": bool(u.subscription_expires_at and u.subscription_expires_at > now),
        "subscription_expires_at": u.subscription_expires_at.isoformat() if u.subscription_expires_at else None,
        "days_left": max(0, (u.subscription_expires_at - now).days) if u.subscription_expires_at and u.subscription_expires_at > now else 0,
        "total_stars_paid": int(u.total_stars_paid or 0), "referral_count": int(u.referral_count or 0),
        "trial_used": bool(u.trial_used), "marzban_username": u.marzban_username or "",
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "device_count": len(live_devs),
        "devices": live_devs,
        "payments": [{"amount": int(p.amount), "method": p.payment_method, "paid_at": p.paid_at.isoformat() if p.paid_at else None, "days": p.days} for p in pays],
    }


@app.post("/web/user/{tg_id}/grant")
async def web_user_grant(tg_id: int, request: Request, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    body = await request.json()
    days = int(body.get("days", 0))
    if days <= 0:
        raise HTTPException(400, "days required")
    async with AsyncSessionLocal() as session:
        u = (await session.execute(select(User).where(User.telegram_id == tg_id))).scalar_one_or_none()
        if not u:
            raise HTTPException(404)
        devs = (await session.execute(select(Device).where(Device.telegram_id == tg_id, Device.is_active.is_(True)))).scalars().all()
        for d in devs:
            try:
                await marzban.extend_user(d.marzban_username, days)
                await marzban.enable_user(d.marzban_username)
            except Exception as e:
                logger.warning("web grant %s: %s", d.marzban_username, e)
        now = datetime.utcnow()
        base = u.subscription_expires_at if (u.subscription_expires_at and u.subscription_expires_at > now) else now
        u.subscription_expires_at = base + timedelta(days=days)
        await session.commit()
    return {"ok": True}


@app.post("/web/user/{tg_id}/ban")
async def web_user_ban(tg_id: int, request: Request, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    reason = (body.get("reason") or "").strip()[:500] or None

    async with AsyncSessionLocal() as session:
        u = (await session.execute(select(User).where(User.telegram_id == tg_id))).scalar_one_or_none()
        if not u:
            raise HTTPException(404)
        u.is_banned = True
        u.ban_reason = reason
        if u.marzban_username:
            try:
                await marzban.disable_user(u.marzban_username)
            except Exception:
                pass
        await session.commit()

    reason_line = f"\nПричина: {reason}" if reason else ""
    await _tg_send(tg_id, f"🚫 <b>Ваш аккаунт STAR VPN заблокирован.</b>{reason_line}\nПо вопросам — обратитесь в поддержку.")
    return {"ok": True}


@app.post("/web/user/{tg_id}/unban")
async def web_user_unban(tg_id: int, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    async with AsyncSessionLocal() as session:
        u = (await session.execute(select(User).where(User.telegram_id == tg_id))).scalar_one_or_none()
        if not u:
            raise HTTPException(404)
        u.is_banned = False
        u.ban_reason = None
        if u.marzban_username:
            try:
                await marzban.enable_user(u.marzban_username)
            except Exception:
                pass
        await session.commit()

    await _tg_send(tg_id, "✅ Ваш аккаунт STAR VPN разблокирован.")
    return {"ok": True}


@app.post("/web/user/{tg_id}/message")
async def web_user_message(tg_id: int, request: Request, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    body = await request.json()
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(400, "text required")
    await _tg_send(tg_id, text)
    return {"ok": True}


@app.get("/web/payments")
async def web_payments(limit: int = 50, offset: int = 0, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    async with AsyncSessionLocal() as session:
        pays = (await session.execute(
            select(Payment).where(Payment.status == "paid").order_by(Payment.paid_at.desc()).limit(limit).offset(offset)
        )).scalars().all()
        total = (await session.execute(select(func.count(Payment.id)).where(Payment.status == "paid"))).scalar_one()
    return {
        "total": total,
        "payments": [{"id": p.id, "telegram_id": p.telegram_id, "amount": int(p.amount),
                      "method": p.payment_method or "stars", "asset": p.asset or "",
                      "days": p.days or 0, "paid_at": p.paid_at.isoformat() if p.paid_at else None} for p in pays],
    }


# ─── Устройства (админка) ─────────────────────────────────────────────────────

@app.get("/web/devices")
async def web_devices(limit: int = 100, offset: int = 0, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    async with AsyncSessionLocal() as session:
        query = (
            select(Device, User)
            .join(User, User.telegram_id == Device.telegram_id)
            .where(Device.is_active.is_(True))
            .order_by(Device.created_at.desc())
        )
        total = (await session.execute(
            select(func.count(Device.id)).where(Device.is_active.is_(True))
        )).scalar_one()
        rows = (await session.execute(query.limit(limit).offset(offset))).all()
    return {
        "total": total,
        "devices": [
            {
                "id": d.id,
                "name": d.name,
                "slot": d.slot,
                "marzban_username": d.marzban_username,
                "owner_id": u.telegram_id,
                "owner_label": u.email or (f"@{u.username}" if u.username else str(u.telegram_id)),
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d, u in rows
        ],
    }


# ─── Рефералы (админка) ────────────────────────────────────────────────────────

@app.get("/web/referrals")
async def web_referrals(limit: int = 100, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(User)
            .where(User.referral_count > 0)
            .order_by(User.referral_count.desc())
            .limit(limit)
        )).scalars().all()
        totals = (await session.execute(
            select(func.count(User.telegram_id), func.sum(User.referral_count), func.sum(User.extra_days_granted))
            .where(User.referral_count > 0)
        )).one()
    return {
        "referrers_count": totals[0] or 0,
        "total_paid_referrals": int(totals[1] or 0),
        "total_days_granted": int(totals[2] or 0),
        "referrers": [
            {
                "telegram_id": u.telegram_id,
                "label": u.email or (f"@{u.username}" if u.username else str(u.telegram_id)),
                "referral_count": u.referral_count,
                "extra_days_granted": u.extra_days_granted,
            }
            for u in rows
        ],
    }


# ─── Wiki CRUD (админка) ───────────────────────────────────────────────────────

@app.get("/web/wiki")
async def web_wiki_list(authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    from bot.models.wiki_article import WikiArticle

    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(WikiArticle).order_by(WikiArticle.updated_at.desc()))).scalars().all()
    return {
        "articles": [
            {
                "id": a.id, "slug": a.slug, "title": a.title, "lede": a.lede,
                "section": a.section, "keywords": a.keywords,
                "is_published": a.is_published, "views": a.views,
                "updated_at": a.updated_at.isoformat() if a.updated_at else None,
            }
            for a in rows
        ]
    }


@app.get("/web/wiki/{article_id}")
async def web_wiki_get(article_id: int, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    from bot.models.wiki_article import WikiArticle

    async with AsyncSessionLocal() as session:
        a = (await session.execute(select(WikiArticle).where(WikiArticle.id == article_id))).scalar_one_or_none()
        if not a:
            raise HTTPException(404, "Not found")
    return {
        "id": a.id, "slug": a.slug, "title": a.title, "lede": a.lede, "body": a.body,
        "section": a.section, "keywords": a.keywords, "is_published": a.is_published,
    }


def _valid_wiki_slug(slug: str) -> bool:
    import re
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}[a-z0-9]", slug))


@app.post("/web/wiki")
async def web_wiki_create(request: Request, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    from bot.models.wiki_article import WikiArticle

    body = await request.json()
    slug = (body.get("slug") or "").strip().lower()
    if slug in _WIKI_SLUGS or not _valid_wiki_slug(slug):
        raise HTTPException(400, "Недопустимый или занятый slug (латиница, цифры, дефис)")
    title = (body.get("title") or "").strip()[:200]
    if not title:
        raise HTTPException(400, "Заголовок обязателен")

    async with AsyncSessionLocal() as session:
        exists = (await session.execute(select(WikiArticle).where(WikiArticle.slug == slug))).scalar_one_or_none()
        if exists:
            raise HTTPException(400, "Статья с таким slug уже существует")
        a = WikiArticle(
            slug=slug, title=title,
            lede=(body.get("lede") or "").strip()[:400],
            body=(body.get("body") or "").strip()[:20000],
            section=(body.get("section") or "О сервисе").strip()[:64],
            keywords=(body.get("keywords") or "").strip()[:300],
            is_published=bool(body.get("is_published", False)),
        )
        session.add(a)
        await session.commit()
        await session.refresh(a)
    return {"ok": True, "id": a.id}


@app.put("/web/wiki/{article_id}")
async def web_wiki_update(article_id: int, request: Request, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    from bot.models.wiki_article import WikiArticle

    body = await request.json()
    async with AsyncSessionLocal() as session:
        a = (await session.execute(select(WikiArticle).where(WikiArticle.id == article_id))).scalar_one_or_none()
        if not a:
            raise HTTPException(404, "Not found")
        if "title" in body:
            a.title = (body.get("title") or "").strip()[:200] or a.title
        if "lede" in body:
            a.lede = (body.get("lede") or "").strip()[:400]
        if "body" in body:
            a.body = (body.get("body") or "").strip()[:20000]
        if "section" in body:
            a.section = (body.get("section") or "О сервисе").strip()[:64]
        if "keywords" in body:
            a.keywords = (body.get("keywords") or "").strip()[:300]
        if "is_published" in body:
            a.is_published = bool(body.get("is_published"))
        await session.commit()
    return {"ok": True}


@app.delete("/web/wiki/{article_id}")
async def web_wiki_delete(article_id: int, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    from bot.models.wiki_article import WikiArticle

    async with AsyncSessionLocal() as session:
        a = (await session.execute(select(WikiArticle).where(WikiArticle.id == article_id))).scalar_one_or_none()
        if not a:
            raise HTTPException(404, "Not found")
        await session.delete(a)
        await session.commit()
    return {"ok": True}


# ─── Настройки (обзор — тарифы/лимиты/провайдеры сейчас read-only) ────────────

@app.get("/web/settings/overview")
async def web_settings_overview(authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    from bot.handlers.payment import PLANS
    from bot.utils.robokassa import robokassa, CARD_PLANS
    from bot.models.device import MAX_DEVICES
    from bot.utils.settings_store import get_all_provider_states

    tariffs = []
    for key, plan in PLANS.items():
        card = CARD_PLANS.get(key, {})
        tariffs.append({
            "key": key, "label": plan["label"], "days": plan["days"],
            "stars": plan["stars"], "rub": float(card.get("rub", 0)),
        })

    async with AsyncSessionLocal() as session:
        toggles = await get_all_provider_states(session)

    return {
        "tariffs": tariffs,
        "providers": {
            "stars": {"configured": True, "enabled": toggles["stars"]},
            "card": {"configured": robokassa.configured, "enabled": toggles["card"]},
            "crypto": {"configured": bool(settings.cryptopay_token), "enabled": toggles["crypto"]},
        },
        "limits": {"max_devices": MAX_DEVICES, "trial_days": settings.trial_days},
        "admin_web_key_set": bool(settings.admin_web_key),
        "admin_web_key_masked": (settings.admin_web_key[:4] + "…" + settings.admin_web_key[-4:]) if len(settings.admin_web_key) > 8 else "",
        "bot_username": settings.bot_username,
        "site_url": settings.site_url,
    }


@app.post("/web/settings/payment-toggle")
async def web_settings_payment_toggle(request: Request, authorization: str | None = Header(default=None)):
    """Включить/выключить способ оплаты (card/crypto/stars)."""
    _web_auth(authorization)
    from bot.utils.settings_store import set_provider_enabled, PROVIDER_KEYS

    body = await request.json()
    provider = body.get("provider")
    enabled = bool(body.get("enabled"))
    if provider not in PROVIDER_KEYS:
        raise HTTPException(status_code=400, detail="Неизвестный способ оплаты")

    async with AsyncSessionLocal() as session:
        await set_provider_enabled(session, provider, enabled)

    return {"ok": True, "provider": provider, "enabled": enabled}


# ─── Рекламный баннер (верхняя полоса главной) ───────────────────────────────

# Фиксированный набор — не произвольная SVG-строка от админа (см. docstring
# AdBanner.icon). Тот же список ключей отрисован в landing/index.html и
# admin/index.html как BANNER_ICONS.
AD_BANNER_ICONS = {
    "sparkle", "star", "fire", "gift", "percent",
    "bell", "rocket", "heart", "zap", "clock",
}


async def _get_ad_banner(session: AsyncSession):
    from bot.models.ad_banner import AdBanner
    row = (await session.execute(select(AdBanner).where(AdBanner.id == 1))).scalar_one_or_none()
    if not row:
        row = AdBanner(id=1, enabled=False, text="")
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return row


@app.get("/api/ad-banner")
async def get_ad_banner_public():
    """Публичный — отдаёт баннер только если он включён и есть текст."""
    async with AsyncSessionLocal() as session:
        banner = await _get_ad_banner(session)
    if not banner.enabled or not banner.text.strip():
        return {"enabled": False}
    return {
        "enabled": True,
        "text": banner.text,
        "link_url": banner.link_url,
        "link_label": banner.link_label,
        "icon": banner.icon,
    }


@app.get("/web/ad-banner")
async def get_ad_banner_admin(authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    async with AsyncSessionLocal() as session:
        banner = await _get_ad_banner(session)
    return {
        "enabled": banner.enabled,
        "text": banner.text,
        "link_url": banner.link_url,
        "link_label": banner.link_label,
        "icon": banner.icon,
    }


@app.post("/web/ad-banner")
async def set_ad_banner(request: Request, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    body = await request.json()
    text = (body.get("text") or "").strip()
    link_url = (body.get("link_url") or "").strip() or None
    link_label = (body.get("link_label") or "").strip() or None
    enabled = bool(body.get("enabled"))
    icon = body.get("icon") or "sparkle"
    if icon not in AD_BANNER_ICONS:
        raise HTTPException(400, "Неизвестная иконка")

    if len(text) > 300:
        raise HTTPException(400, "Текст баннера — максимум 300 символов")

    async with AsyncSessionLocal() as session:
        banner = await _get_ad_banner(session)
        banner.enabled = enabled
        banner.text = text
        banner.link_url = link_url
        banner.link_label = link_label
        banner.icon = icon
        await session.commit()

    return {"ok": True}


@app.post("/web/broadcast")
async def web_broadcast(request: Request, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    body = await request.json()
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(400, "text required")
    from aiogram import Bot as ABot
    bot = ABot(token=settings.telegram_api_token)
    sent = failed = 0
    async with AsyncSessionLocal() as session:
        uids = (await session.execute(select(User.telegram_id).where(User.is_banned.is_(False)))).scalars().all()
    try:
        for uid in uids:
            try:
                await bot.send_message(uid, text, parse_mode="HTML")
                sent += 1
            except Exception:
                failed += 1
    finally:
        try:
            await bot.session.close()
        except Exception:
            pass
    return {"ok": True, "sent": sent, "failed": failed}


# ─── Тикеты поддержки (админка) ───────────────────────────────────────────────

TICKET_TOPIC_LABELS = {
    "connect": "Не подключается", "payment": "Оплата",
    "account": "Аккаунт", "other": "Другое",
}


@app.get("/web/tickets")
async def web_tickets(status: str = "", authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    from bot.models.support_ticket import SupportTicket

    async with AsyncSessionLocal() as session:
        query = select(SupportTicket, User).outerjoin(User, User.telegram_id == SupportTicket.user_id)
        if status:
            query = query.where(SupportTicket.status == status)
        rows = (await session.execute(query.order_by(SupportTicket.created_at.desc()).limit(300))).all()

    def label(t: "SupportTicket", u: User | None) -> str:
        if u:
            return u.email or (f"@{u.username}" if u.username else str(u.telegram_id))
        return t.contact or "—"

    return {
        "tickets": [
            {
                "id": t.id,
                "public_id": f"S-{t.id:06d}",
                "user_id": t.user_id,
                "user_label": label(t, u),
                "topic": t.topic,
                "topic_label": TICKET_TOPIC_LABELS.get(t.topic, t.topic),
                "message": t.message,
                "platform": t.platform or "",
                "status": t.status,
                "admin_reply": t.admin_reply or "",
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t, u in rows
        ]
    }


@app.post("/web/tickets/{ticket_id}/reply")
async def web_ticket_reply(ticket_id: int, request: Request, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    from bot.models.support_ticket import SupportTicket

    body = await request.json()
    reply = (body.get("reply") or "").strip()[:4000]
    new_status = (body.get("status") or "answered").strip()
    if new_status not in ("open", "answered", "closed"):
        raise HTTPException(400, "Invalid status")

    async with AsyncSessionLocal() as session:
        t = (await session.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))).scalar_one_or_none()
        if not t:
            raise HTTPException(404, "Ticket not found")
        if reply:
            t.admin_reply = reply
        t.status = new_status
        user_id, contact, topic_label = t.user_id, t.contact, TICKET_TOPIC_LABELS.get(t.topic, t.topic)
        user = (await session.execute(select(User).where(User.telegram_id == user_id))).scalar_one_or_none() if user_id else None
        await session.commit()

    if reply:
        # Аккаунт с реальным Telegram — шлём в бота. Веб-аккаунт (telegram_id
        # синтетический) или анонимное обращение с email-контактом — на почту.
        # @username без привязанного аккаунта Bot API написать не даёт —
        # для таких тикетов остаётся только ручной ответ через сам контакт.
        if user and user.telegram_id > 0:
            await _tg_send(user.telegram_id, f"💬 <b>Ответ поддержки по тикету «{topic_label}»:</b>\n\n{reply}")
        else:
            email = (user.email if user else None) or (contact if contact and "@" in contact and not contact.startswith("@") else None)
            if email:
                from bot.utils.mailer import send_ticket_reply_email
                try:
                    await send_ticket_reply_email(email, topic_label, reply)
                except Exception as e:
                    logger.error("Failed to email ticket reply to %s: %s", email, e)
    return {"ok": True}


@app.get("/web/marzban/ping")
async def web_marzban_ping(authorization: str | None = Header(default=None)):
    """Проверить соединение с Marzban и вернуть диагностику."""
    _web_auth(authorization)
    try:
        token = await marzban._auth()
        return {"ok": True, "url": marzban._base_url, "token_len": len(token)}
    except Exception as e:
        raise HTTPException(502, f"Marzban auth failed: {e}")


@app.get("/web/marzban/users")
async def web_marzban_users(authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    try:
        users = await marzban.get_all_users()
        return users
    except httpx.ConnectError as e:
        raise HTTPException(502, f"Marzban недоступен ({marzban._base_url}): {e}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(502, f"Marzban вернул {e.response.status_code}: {e.response.text[:200]}")
    except httpx.TimeoutException:
        raise HTTPException(504, f"Marzban не ответил за 15 сек ({marzban._base_url})")
    except Exception as e:
        raise HTTPException(502, f"Marzban ошибка: {type(e).__name__}: {e}")


@app.post("/web/marzban/users/{username}/enable")
async def web_marzban_enable(username: str, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    return await marzban.enable_user(username)


@app.post("/web/marzban/users/{username}/disable")
async def web_marzban_disable(username: str, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    return await marzban.disable_user(username)


@app.post("/web/marzban/users/{username}/extend")
async def web_marzban_extend(username: str, request: Request, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    body = await request.json()
    return await marzban.extend_user(username, int(body.get("days", 30)))


@app.delete("/web/marzban/users/{username}")
async def web_marzban_delete(username: str, authorization: str | None = Header(default=None)):
    _web_auth(authorization)
    return await marzban.delete_user(username)
