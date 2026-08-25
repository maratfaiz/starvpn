#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
#  STAR VPN — настройка SSH-доступа к боевому серверу с Mac.
#  Запускать НА МАКЕ:  bash scripts/mac-setup-ssh.sh
#  Подробности и разбор ошибок: docs/SERVER_ACCESS.md
# ──────────────────────────────────────────────────────────────────
set -euo pipefail

SERVER_IP="64.188.60.178"
SERVER_USER="root"
KEY="$HOME/.ssh/star_vpn_key"
ALIAS="starvpn"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

echo "==> [1/4] Ищу существующий ключ..."
if [ ! -f "$KEY" ] && [ -f "$PROJECT_DIR/star_vpn_key" ]; then
  echo "     Нашёл ключ в папке проекта — переношу в ~/.ssh/"
  mv "$PROJECT_DIR/star_vpn_key" "$KEY"
fi

if [ -f "$KEY" ]; then
  echo "     Ключ на месте: $KEY"
else
  echo "     Ключа нет — генерирую новый."
  ssh-keygen -t ed25519 -f "$KEY" -C "mac-starvpn" -N ""
fi
chmod 600 "$KEY"

echo "==> [2/4] Прописываю алиас '$ALIAS' в ~/.ssh/config..."
if grep -qE "^Host[[:space:]]+$ALIAS\$" "$HOME/.ssh/config" 2>/dev/null; then
  echo "     Алиас уже есть — пропускаю."
else
  cat >> "$HOME/.ssh/config" << EOF

Host $ALIAS
    HostName $SERVER_IP
    User $SERVER_USER
    IdentityFile $KEY
    ServerAliveInterval 30
    ServerAliveCountMax 6
EOF
  chmod 600 "$HOME/.ssh/config"
  echo "     Готово."
fi

echo "==> [3/4] Проверяю вход по ключу..."
if ssh -o BatchMode=yes -o ConnectTimeout=10 "$ALIAS" "echo ok" 2>/dev/null | grep -q ok; then
  echo "     ✅ Ключ уже принят сервером."
else
  echo "     Ключ пока не установлен на сервере."
  echo "     Сейчас будет запрошен пароль root (берётся в панели FirstVDS)."
  echo "     Пароль при вводе не отображается — это нормально."
  if ssh-copy-id -i "${KEY}.pub" "${SERVER_USER}@${SERVER_IP}"; then
    echo "     ✅ Ключ залит."
  else
    echo "     ❌ Не удалось. Похоже, вход по паролю запрещён."
    echo "        Смотри раздел 2.3 в docs/SERVER_ACCESS.md — надо один раз"
    echo "        включить PasswordAuthentication через консоль FirstVDS."
    exit 1
  fi
fi

echo "==> [4/4] Финальная проверка..."
ssh -o ConnectTimeout=10 "$ALIAS" "hostname && docker compose -f /root/STAR_VPN/infra/docker-compose.yml ps 2>/dev/null || true"

echo ""
echo "✅ Готово. Теперь подключение к серверу — одна команда:"
echo "     ssh $ALIAS"
