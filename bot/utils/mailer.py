"""
Отправка писем по SMTP (magic-link для входа в личный кабинет).

Пока SMTP_HOST не задан в .env — письмо не отправляется, а ссылка для
входа просто пишется в лог, чтобы можно было тестировать поток входа
до того как будут готовы реальные почтовые credentials.
"""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from bot.config import settings

logger = logging.getLogger(__name__)


def _send_sync(to_email: str, subject: str, text_body: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(settings.smtp_from, [to_email], msg.as_string())


async def send_magic_link_email(to_email: str, link: str) -> None:
    if not settings.smtp_host:
        logger.warning("SMTP не настроен — magic-link для %s: %s", to_email, link)
        return

    subject = "Вход в STAR VPN"
    text_body = f"Ссылка для входа в личный кабинет STAR VPN (действует 15 минут):\n\n{link}\n\nЕсли вы не запрашивали вход — просто проигнорируйте это письмо."
    html_body = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px;background:#060606;color:#EBE0CC">
      <h2 style="color:#FFB800;margin:0 0 16px">STAR VPN</h2>
      <p>Ссылка для входа в личный кабинет (действует 15 минут):</p>
      <p style="margin:24px 0">
        <a href="{link}" style="background:#FFB800;color:#000;padding:14px 28px;border-radius:10px;text-decoration:none;font-weight:700;display:inline-block">Войти в аккаунт</a>
      </p>
      <p style="color:#8A7A60;font-size:13px">Если вы не запрашивали вход — просто проигнорируйте это письмо.</p>
    </div>
    """

    try:
        await asyncio.to_thread(_send_sync, to_email, subject, text_body, html_body)
    except Exception as e:
        logger.error("Не удалось отправить magic-link на %s: %s", to_email, e)
        raise


async def send_ticket_reply_email(to_email: str, ticket_subject: str, reply: str) -> None:
    if not settings.smtp_host:
        logger.warning("SMTP не настроен — ответ на тикет для %s: %s", to_email, reply)
        return

    subject = f"Ответ поддержки STAR VPN: {ticket_subject}"
    text_body = f"Ответ поддержки по тикету «{ticket_subject}»:\n\n{reply}"
    html_body = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px;background:#060606;color:#EBE0CC">
      <h2 style="color:#FFB800;margin:0 0 16px">STAR VPN — Поддержка</h2>
      <p style="color:#8A7A60;margin:0 0 8px">По тикету «{ticket_subject}»:</p>
      <p style="white-space:pre-wrap">{reply}</p>
    </div>
    """

    try:
        await asyncio.to_thread(_send_sync, to_email, subject, text_body, html_body)
    except Exception as e:
        logger.error("Не удалось отправить ответ на тикет %s: %s", to_email, e)
        raise
