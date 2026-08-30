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
