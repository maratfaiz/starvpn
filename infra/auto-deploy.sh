#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
#  STAR VPN — Auto-deploy
#  Проверяет, есть ли новые коммиты в ветке origin/original, и если
#  есть — подтягивает их и пересобирает контейнеры.
#  Рассчитан на запуск по cron каждые несколько минут (см. README /
#  AGENTS/roles/devops.md за инструкцией по установке).
# ──────────────────────────────────────────────────────────────────

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRANCH="original"
LOCK_FILE="/tmp/star-vpn-autodeploy.lock"

cd "$PROJECT_DIR"

# Не запускаем второй раз, если предыдущий деплой ещё не закончился
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "$(date -Is) уже выполняется, пропускаем"
  exit 0
fi

git fetch origin "$BRANCH" --quiet

LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse "origin/$BRANCH")"

if [ "$LOCAL_SHA" = "$REMOTE_SHA" ]; then
  exit 0
fi

echo "$(date -Is) новые коммиты: $LOCAL_SHA -> $REMOTE_SHA"

git checkout -q "$BRANCH"
git merge --ff-only "origin/$BRANCH"

# docker-compose.yml подставляет ${POSTGRES_PASSWORD} и т.д. из .env,
# лежащего РЯДОМ с ним (infra/.env), а не из корневого — держим копию
# свежей на каждый деплой. См. AGENTS/roles/devops.md.
cp "$PROJECT_DIR/.env" "$PROJECT_DIR/infra/.env"

cd "$PROJECT_DIR/infra"
docker compose up -d --build

echo "$(date -Is) деплой завершён: $(git -C "$PROJECT_DIR" rev-parse --short HEAD)"
