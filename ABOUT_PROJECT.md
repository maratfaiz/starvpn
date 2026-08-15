Текст для файла ABOUT_PROJECT.md
Project Overview: STAR VPN (Sovereign Internet 2026)
--------------HA$H--PROJECT--------------
1. General Concept
STAR VPN — это современный VPN-сервис, интегрированный в экосистему Telegram (Bot + Mini App). Проект ориентирован на обход продвинутых систем DPI и обеспечение максимальной приватности в условиях 2026 года.
------------------------
2. Technical Core
VPN Engine: Marzban (Xray-core).

Primary Protocol: VLESS + Reality. Это критически важно: мы используем технологию заимствования TLS-рукопожатия (от популярных ресурсов, таких как Google или Microsoft), чтобы трафик выглядел как легитимный HTTPS.

Zero Logs Strategy: Конфигурация Xray должна исключать любые логи доступа. Параметры access и error в LogObject должны быть установлены в "none", а loglevel — в "none".
------------------------
3. Technology Stack
Backend: Python 3.11+, aiogram 3.x (асинхронный фреймворк для бота).

Database: PostgreSQL + SQLAlchemy 2.0.

Frontend: Telegram Mini App (React + Vite + Tailwind). Стиль — Glassmorphism.

Integration: Взаимодействие с Marzban через REST API (использование библиотеки aiomarzban или прямые запросы).

Infrastructure: Docker Compose (сервисы: bot, webapp, database, marzban).
------------------------
4. Business Logic & Features
24h Auto-Trial: При первом запуске бота (/start) пользователь автоматически получает временный доступ на 24 часа через API Marzban (add_user с expiration_date +86400с).

Referral System (2+1): За каждых двух активных рефералов (купивших подписку) пригласивший получает +30 дней к своему тарифу. Логика отслеживается в БД через referrer_id.

Payments:

Telegram Stars (XTR): Использование метода sendInvoice с валютой XTR. Обработка pre_checkout_query обязательна.

Russian Gateways: Интеграция с Prodamus/Robokassa через вебхуки с проверкой HMAC-SHA256 подписи.
------------------------
5. UI/UX Requirements
Haptic Feedback: Каждое ключевое действие в Mini App (оплата, включение VPN, ошибка) должно сопровождаться тактильной отдачей через @tma.js/sdk.

Theme Sync: Интерфейс должен автоматически подстраиваться под цветовую схему Telegram (Dark/Light).
------------------------
6. Project Structure (Monorepo)
/bot: Логика Telegram-бота, хендлеры, мидлвари.

/webapp: Исходный код Mini App (React).

/infra: Docker-конфигурации, скрипты деплоя, конфиги Xray.

/.env: Все секреты (Bot Token, Marzban API Key, DB Credentials).
------------------------
7. Веб-аккаунт — второй способ подключиться (в разработке, дизайн отдельно)
Сейчас единственный способ пользоваться сервисом — Telegram (бот/Mini App), User.telegram_id обязателен и является главным ключом identity.

Планируется: личный кабинет на сайте как полноценная альтернатива Telegram, а не разовая покупка без возможности потом зайти. Актуально в первую очередь для пользователей, которым сам Telegram недоступен без VPN.

Вход — email (magic-link, без пароля, без Telegram). Опционально можно привязать существующий Telegram-аккаунт из кабинета.

Данные не дублируются: один и тот же User сможет входить и через бота, и через сайт — это один аккаунт с одной подпиской, а не отдельная копия состояния. Для этого User.telegram_id станет опциональным (сейчас обязателен), добавится User.email.

Дизайн и вёрстку сайта под это делает отдельная design-сессия — здесь описана только бизнес-логика, не UI.