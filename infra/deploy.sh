#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
#  STAR VPN — Deploy Script
#  Target OS: Debian 12
#  Run as root or sudo-capable user.
#  Usage: bash deploy.sh
# ──────────────────────────────────────────────────────────────────

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> [1/6] Updating packages..."
apt-get update -qq && apt-get install -y -qq curl git docker.io docker-compose-plugin

echo "==> [2/6] Enabling Docker service..."
systemctl enable --now docker

echo "==> [3/6] Checking .env file..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
  echo "ERROR: .env not found at $PROJECT_DIR/.env"
  echo "       Copy .env.example to .env and fill in the values."
  exit 1
fi

echo "==> [4/6] Generating Xray Reality keys (if not set)..."
# Check if private key is still placeholder
if grep -q "REPLACE_WITH_YOUR_PRIVATE_KEY" "$PROJECT_DIR/infra/xray_config.json"; then
  echo "     Generating Reality keypair with xray x25519..."
  # Run xray inside a temporary container to generate keys
  KEYS=$(docker run --rm teddysun/xray xray x25519 2>/dev/null || echo "SKIP")
  if [ "$KEYS" != "SKIP" ]; then
    PRIVATE_KEY=$(echo "$KEYS" | grep "Private key:" | awk '{print $3}')
    PUBLIC_KEY=$(echo "$KEYS" | grep "Public key:" | awk '{print $3}')
    SHORT_ID=$(openssl rand -hex 4)
    sed -i "s/REPLACE_WITH_YOUR_PRIVATE_KEY/$PRIVATE_KEY/" "$PROJECT_DIR/infra/xray_config.json"
    sed -i "s/REPLACE_WITH_SHORT_ID/$SHORT_ID/" "$PROJECT_DIR/infra/xray_config.json"
    echo "     Private key: $PRIVATE_KEY"
    echo "     Public key:  $PUBLIC_KEY  (add to Marzban settings)"
    echo "     Short ID:    $SHORT_ID"
  else
    echo "     WARN: Could not auto-generate keys. Fill xray_config.json manually."
  fi
fi

echo "==> [5/6] Building and starting containers..."
cd "$PROJECT_DIR/infra"
docker compose pull --quiet
docker compose build --quiet
docker compose up -d

echo "==> [6/6] Checking service health..."
sleep 5
docker compose ps

echo ""
echo "✅  Deploy complete!"
echo "   Marzban dashboard: http://$(hostname -I | awk '{print $1}'):8000"
echo "   Webapp:            http://$(hostname -I | awk '{print $1}'):5173"
echo ""
echo "ℹ️  If this is an UPGRADE of an existing install (not a fresh deploy),"
echo "   the users table needs an email/is_admin column added once:"
echo "     docker compose exec bot python -m alembic stamp 0001_baseline"
echo "     docker compose exec bot python -m alembic upgrade head"
echo "   On a brand-new install this is unnecessary — the bot creates the"
echo "   current schema automatically on first startup."
echo ""
echo "   Next steps:"
echo "   1. Open Marzban dashboard → Settings → set Reality public key."
echo "   2. Create admin user in Marzban."
echo "   3. Fill MARZBAN_USERNAME / MARZBAN_PASSWORD in .env and restart bot:"
echo "      docker compose restart bot"
