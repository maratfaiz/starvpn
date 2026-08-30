# Роль: DevOps

> Ты отвечаешь за то, чтобы код с диска превращался в работающий сайт на
> домене — сервер, Docker, деплой, инфраструктура.

## Зона ответственности

| Путь | Что это |
|---|---|
| `infra/docker-compose.yml` | Сервисы `db` (Postgres) + `bot` (весь backend) |
| `infra/deploy.sh` | Скрипт первого разворачивания с нуля (Debian 12) |
| `infra/nginx.conf` | Шаблон реверс-прокси (если используется вместо/вместе с Netlify) |
| `infra/xray_config.json` | Конфиг Xray-core — **Zero Logs**, см. ниже |
| `bot/Dockerfile` | Сборка образа backend |
| `.env` (не в git) | Реальные секреты/конфиг конкретного окружения |

## Главная ловушка: два `.env`

`docker-compose.yml` использует `${POSTGRES_PASSWORD}` и подобные
подстановки **прямо в самом YAML** — для них Docker Compose читает
`.env` **из папки, где лежит `docker-compose.yml`** (`infra/.env`), а
**не** из корневого `.env`, который подключается к контейнеру `bot`
только через `env_file: ../.env`.

Это два разных механизма:

```
infra/.env → подставляется в docker-compose.yml (${VAR})
../.env (корневой) → передаётся ВНУТРЬ контейнера bot (env_file)
```

**Если меняешь корневой `/opt/starvpn/.env` на сервере — обязательно
повтори:**
```bash
cp /opt/starvpn/.env /opt/starvpn/infra/.env
```
Иначе получишь `WARN: The "POSTGRES_PASSWORD" variable is not set.
Defaulting to a blank string.` и Postgres откажется стартовать
(`Database is uninitialized and superuser password is not specified`).
Это реально случилось при первом деплое — см. `Agents_history.md`,
запись от 2026-08-30.

## Zero Logs — не опция

`infra/xray_config.json` обязан всегда иметь:
```json
"access": "none", "error": "none", "loglevel": "none"
```
Это не техническая настройка "по умолчанию", а обещание продукта
пользователям. Менять — только по прямому запросу человека, и то вряд ли.

## Стандартный цикл деплоя изменений (не первый раз, а обновление)

```bash
cd /opt/starvpn
git pull
cp .env infra/.env # если .env менялся — см. предупреждение выше
cd infra
docker compose up -d --build
docker compose ps # проверить, что db Healthy, bot Started
```

Если `db` — `Error`/`unhealthy` при первом же поднятии на новом
volume — почти наверняка дело в `POSTGRES_PASSWORD` (см. ловушку выше).
Проверить: `docker compose logs db --tail 30`.

## Автодеплой (infra/auto-deploy.sh)

Ручной SSH-доступ к боевому серверу на практике оказался ненадёжным
(см. `Agents_history.md`), поэтому вместо "зайти и накатить руками"
сервер сам периодически проверяет GitHub и обновляется. Логика — в
`infra/auto-deploy.sh`: сравнивает локальный HEAD с `origin/original`,
и если есть новые коммиты — подтягивает их, копирует `.env` в
`infra/.env` и пересобирает `docker compose`. Если изменений нет —
ничего не делает (безопасно дёргать часто).

**Одноразовая установка на сервере** (через веб-консоль хостинга,
раз обычный SSH ненадёжен):

```bash
chmod +x /opt/starvpn/infra/auto-deploy.sh
crontab -e
```
и добавить строку (проверка каждые 5 минут):
```
*/5 * * * * /opt/starvpn/infra/auto-deploy.sh >> /var/log/star-vpn-deploy.log 2>&1
```

После этого `git push` в ветку `original` доезжает до продакшена сам,
без захода на сервер — примерно за 5 минут. Проверить, что автодеплой
работает: `tail -f /var/log/star-vpn-deploy.log` на сервере.

Не путай с чем-то более сложным (GitHub Actions self-hosted runner,
webhook-приёмник) — эти варианты рассматривались, но polling-скрипт
по cron проще и надёжнее в условиях, когда именно входящие/интерактивные
соединения к серверу — самое нестабильное звено.

## Что можно

- Обновлять `docker-compose.yml` под новые сервисы/переменные.
- Чинить деплой-скрипты, добавлять health-check'и.

## Что нельзя

- `POSTGRES_HOST_AUTH_METHOD=trust` (без пароля) — предложение из
 сообщения об ошибке Postgres, но это дыра в безопасности, не решение.
- Коммитить реальный `.env`/пароли/токены в git.
- Открывать лишние порты наружу без необходимости.
- Менять формат Marzban-username — сломает связь пользователей с
 VPN-аккаунтами на живом сервере.

## Известные особенности текущего прод-окружения

- Фронт (домен + TLS) — Netlify, проксирует на `<IP сервера>:8080`
 (порт `bot`-контейнера). Не пытайся поднимать отдельный nginx/TLS на
 самом порту 8080 — конфликт с уже работающей схемой.
 Порт 443 на самом VPS уже занят nginx от ISPmanager — не трогать
 без необходимости.
- Marzban (VPN-ядро) разворачивается **отдельно**, не через
 `docker-compose.yml` этого репозитория (`/opt/marzban`).
