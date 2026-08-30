# API Reference

Всё живёт в `bot/api.py` (FastAPI). Два больших семейства эндпоинтов:

- **`/api/*`** — публичное API для сайта (`landing/`) и Mini App (`webapp/`).
 Identity — через `_resolve_tg_id()` (Telegram initData **или** cookie
 `star_session`), см. `AGENTS/roles/backend.md`.
- **`/web/*`** — API веб-админки (`admin/index.html`). Identity — общий
 `Authorization: Bearer <ADMIN_WEB_KEY>` (один ключ на всех
 администраторов, не per-user учётки).

Плюс раздача HTML-страниц (`/`, `/tariffs`, `/wiki/{slug}`, `/account`,
`/login`, `/admin`, ...) — читаются с диска через `_serve_html`, не
эндпоинты в привычном смысле.

## `/api/*` — публичное API

| Метод | Путь | Назначение |
|---|---|---|
| `POST` | `/api/account/login` | Отправить magic-link на email |
| `GET` | `/account/verify` | Подтвердить magic-link → выставить cookie `star_session` |
| `POST` | `/api/account/logout` | Выйти из веб-аккаунта |
| `GET` | `/api/me` | Текущий пользователь (статус подписки, устройства, и т.д.) |
| `GET`/`POST`/`DELETE` | `/api/devices*` | Список / добавление / удаление устройств |
| `GET` | `/api/devices/{id}/link` | Получить VLESS-ссылку/QR устройства |
| `GET` | `/api/referral` | Реферальная статистика пользователя |
| `POST` | `/api/trial` | Активировать пробный период (2 дня, один раз) |
| `GET` | `/api/plans` | Тарифы (для Mini App/бота) |
| `POST` | `/api/support` | Отправить обращение в поддержку |
| `GET` | `/api/card/plans`, `/api/yoomoney/plans`, `/api/crypto/plans` | Тарифы по конкретному провайдеру оплаты |
| `POST` | `/api/invoice/card`, `/api/invoice/yoomoney`, `/api/invoice/crypto`, `/api/invoice/renew` | Создать счёт на оплату/продление |
| `POST` | `/api/gift/lookup` | Проверить получателя подарка по @username/ID |
| `POST` | `/api/gift/invoice` | Создать счёт на подарок |
| `GET` | `/api/gift/pending` | Есть ли непрочитанное уведомление о подарке |
| `POST` | `/api/gift/seen` | Пометить уведомление о подарке прочитанным |
| `GET` | `/api/guest/plans`, `/api/guest/providers` | Тарифы для покупки без Telegram |
| `POST` | `/api/guest/checkout` | Гостевой чекаут (`/get-vpn`) |
| `GET` | `/api/guest/order/{public_id}` | Статус гостевого заказа |
| `POST` | `/card/webhook`, `/yoomoney/webhook`, `/crypto/webhook` | Вебхуки платёжных провайдеров — **проверяют подпись**, не трогать без крайней необходимости |

## `/web/*` — API админки

| Метод | Путь | Назначение |
|---|---|---|
| `POST` | `/web/login` | Вход по общему `ADMIN_WEB_KEY` |
| `GET` | `/web/stats` | Дашборд (метрики за 7 дней) |
| `GET` | `/web/users`, `/web/user/{tg_id}` | Список / карточка пользователя |
| `POST` | `/web/user/{tg_id}/grant`, `/ban`, `/unban`, `/message` | Выдать дни / забанить / разбанить / написать пользователю |
| `GET` | `/web/payments`, `/web/devices`, `/web/referrals` | Таблицы платежей / устройств / рефералов |
| `GET`/`POST`/`PUT`/`DELETE` | `/web/wiki*` | CRUD статей базы знаний (хранятся в БД, `wiki_articles`) |
| `GET`/`POST` | `/web/tickets*` | Обращения в поддержку, ответы |
| `GET`/`POST` | `/web/settings/*` | Тарифы, лимиты, тумблеры провайдеров оплаты |
| `POST` | `/web/broadcast` | Массовая рассылка |
| `GET`/`POST`/`DELETE` | `/web/marzban/*` | Прямые операции с Marzban (ping, список юзеров, вкл/выкл/продление/удаление) |

## Важные детали контракта

- **Identity в `/api/*` — всегда через `_resolve_tg_id`**, кроме мест,
 которые сознательно требуют только Telegram (проверь перед тем, как
 добавлять новый эндпоинт — использовать общий резолвер по умолчанию).
- **Вебхуки НЕ используют `_resolve_tg_id`** — они идентифицируют
 платёж по `order_id`/`payload` из самого вебхука, а подлинность
 проверяют подписью провайдера (MD5 у Robokassa, SHA-256 у ЮMoney).
- Добавляя новый эндпоинт под фичу сайта — сначала проверь, нет ли уже
 подходящего в этом списке, не дублируй.
