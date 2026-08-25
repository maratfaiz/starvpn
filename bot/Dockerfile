# ──────────────────────────────────────────────────────────────────
#  STAR VPN — образ бота + API.
#
#  Mini App собирается ЗДЕСЬ ЖЕ (stage `webapp-build`), а не берётся
#  готовым файлом из репозитория: раньше webapp/app.html собирался
#  вручную через `npm run build:app`, и забытая пересборка означала,
#  что прод отдаёт старую версию мини-аппа при свежих исходниках.
#  Теперь `docker compose up --build` всегда даёт актуальный /app.
# ──────────────────────────────────────────────────────────────────

FROM node:22-slim AS webapp-build

WORKDIR /webapp

# Ставим зависимости отдельным слоем — пересобирается только при
# изменении package.json / package-lock.json.
COPY webapp/package.json webapp/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY webapp/ ./
RUN npm run build          # → /webapp/dist/index.html (single-file бандл)


FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY bot/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot package
COPY bot/ ./bot/

# Миграции: infra/deploy.sh предлагает гонять
# `docker compose exec bot python -m alembic upgrade head`,
# а без этих файлов такая команда в контейнере не работала.
COPY alembic/ ./alembic/
COPY alembic.ini ./alembic.ini

# Mini App (served via /app endpoint) — свежесобранный на предыдущем этапе
COPY --from=webapp-build /webapp/dist/index.html ./webapp/app.html

# Copy website (served via /, /tariffs, /wiki/*, ... endpoints)
COPY landing/ ./landing/

# Copy Admin Panel (served via /admin endpoint)
COPY admin/index.html ./admin/index.html

CMD ["python", "-m", "bot.main"]
