# Database Schema

PostgreSQL 16, SQLAlchemy 2.0 (async), миграции — Alembic
(`alembic/versions/`). Полный источник правды — сами модели в
`bot/models/*.py`; здесь — карта для ориентации, сверяйся с кодом при
сомнении.

## Диаграмма связей

```
                              ┌───────────────────────┐
                              │        users           │
                              │ telegram_id (PK)        │◀─┐ referrer_id
                              │ email (unique, nullable)│  │ (self-FK,
                              │ password_hash            │  │  рефералка)
                              │ email_verified           │  │
                              │ marzban_username         │  │
                              │ trial_used               │──┘
                              │ subscription_expires_at  │
                              │ is_banned / is_admin      │
                              └───────────┬───────────────┘
                                          │ telegram_id (FK везде ниже)
        ┌───────────────┬────────────────┼────────────────┬─────────────────┐
        ▼               ▼                ▼                ▼                 ▼
   ┌─────────┐   ┌─────────────┐  ┌──────────────┐ ┌───────────────┐ ┌──────────────┐
   │ devices │   │  payments   │  │gift_          │ │support_tickets│ │ web_sessions │
   │ slot    │   │ order_id    │  │notifications  │ │ topic         │ │ token_hash   │
   │ marzban_│   │ status      │  │ recipient_id  │ │ status        │ │ expires_at   │
   │ username│   │ is_gift     │  │ plan_days     │ │ admin_reply   │ │              │
   └─────────┘   │ gift_sender_│  │ seen          │ └───────────────┘ └──────────────┘
                 │ id          │  └───────────────┘
                 └─────────────┘

   ┌──────────────────────┐    ┌──────────────┐        ┌───────────────┐
   │ email_verification_  │    │ guest_orders │        │ wiki_articles │
   │ codes                 │    │ public_id    │        │ slug (unique) │
   │ email                 │    │ (гостевая    │        │ section       │
   │ code_hash             │    │  покупка без │        │ is_published  │
   │ attempts / expires_at │    │  Telegram)   │        └───────────────┘
   └──────────────────────┘    └──────────────┘

   ┌───────────────┐
   │ app_settings  │  ← key/value, тумблеры (например, включена ли крипта)
   └───────────────┘
```

## Таблицы

| Таблица | Модель | Назначение |
|---|---|---|
| `users` | `User` | Центральная таблица. Реальный Telegram-пользователь **или** веб-аккаунт (email-only, отрицательный `telegram_id`) |
| `devices` | `Device` | Привязанные VPN-устройства (слот 1–3, `marzban_username` уникален) |
| `payments` | `Payment` | Все платежи (Stars/Robokassa/ЮMoney/крипта), включая подарки (`is_gift`) |
| `gift_notifications` | `GiftNotification` | Уведомление получателю о подарке (сами дни уже начислены в момент оплаты — это только UI-уведомление) |
| `support_tickets` | `SupportTicket` | Обращения в поддержку (сайт + бот) |
| `web_sessions` | `WebSession` | Сессии веб-личного кабинета (cookie `star_session`) |
| `email_verification_codes` | `EmailVerificationCode` | 6-значные коды подтверждения email при регистрации (хеш кода, cooldown на переотправку, лимит попыток) |
| `guest_orders` | `GuestOrder` | Покупка VPN-ключа без Telegram (гостевой чекаут, `/get-vpn`) |
| `wiki_articles` | `WikiArticle` | Статьи базы знаний, создаваемые из админки (в дополнение к статичным `.html` в `landing/wiki/`) |
| `app_settings` | `AppSetting` | Key-value тумблеры (например, включена ли оплата криптой) |

## Ключевые правила (см. также `AGENTS/roles/database.md`)

1. **`users.telegram_id` — всегда `NOT NULL`.** Веб-аккаунт получает
 синтетический **отрицательный** ID вместо `NULL` — так все FK на
 `users.telegram_id` работают одинаково для обоих типов аккаунтов.
 Проверка "настоящий Telegram?" — `telegram_id > 0`.
2. **`referrer_id`** в `users` — self-referencing FK, реализует
 реферальную цепочку "кто кого пригласил".
3. **`marzban_username`** — уникален и в `users`, и в `devices`, формат
 `tg_{telegram_id}` для Telegram-пользователей, `web_{id}` для
 веб-аккаунтов. Это внешний контракт с Marzban — не менять формат.
4. Любая новая таблица с FK на пользователя — на `users.telegram_id`,
 не заводи отдельный "универсальный" `user_id` без необходимости.
