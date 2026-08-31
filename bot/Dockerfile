FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY bot/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot package
COPY bot/ ./bot/

# Copy Alembic config/migrations (needed for `alembic upgrade head` inside the container)
COPY alembic.ini ./alembic.ini
COPY alembic/ ./alembic/

# Copy Mini App HTML (served via /app endpoint)
COPY webapp/app.html ./webapp/app.html

# Copy Admin Panel (served via /admin endpoint)
COPY admin/index.html ./admin/index.html

# Copy landing site (favicon, images, world-dots.js, all HTML pages — served via bot/api.py)
COPY landing/ ./landing/

CMD ["python", "-m", "bot.main"]
