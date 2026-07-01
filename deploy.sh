#!/bin/bash
echo "🚀 Деплой..."
rsync -avz -e "ssh -i ~/.ssh/star_vpn_key -o StrictHostKeyChecking=no" \
  /Users/helloimmarat/Desktop/Проекты/STAR_VPN/bot/ \
  root@64.188.60.178:/root/STAR_VPN/bot/
ssh -i ~/.ssh/star_vpn_key -o StrictHostKeyChecking=no root@64.188.60.178 \
  "cd /root/STAR_VPN/infra && docker compose restart bot"
echo "✅ Готово!"
