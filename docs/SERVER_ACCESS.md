# Доступ к боевому серверу с Mac (Terminal)

Как вернуть управление сервером из терминала на маке вместо неудобной
браузерной консоли FirstVDS (в которой не работает вставка).

---

## Реквизиты (взяты из `deploy.sh` и `infra/post-receive`)

| Что | Значение |
|-----|----------|
| IP сервера | `64.188.60.178` |
| Пользователь | `root` |
| SSH-ключ (имя) | `star_vpn_key` |
| Код проекта на сервере | `/root/STAR_VPN` |
| Docker Compose | `/root/STAR_VPN/infra/docker-compose.yml` |
| Bare-repo для push-деплоя | `/root/STAR_VPN.git` (хук `post-receive` пересобирает compose) |
| Папка проекта на маке | `/Users/helloimmarat/Desktop/Проекты/STAR_VPN` |

---

## Шаг 1. Проверить, есть ли ещё ключ на маке

Открой **Terminal** на маке (Cmd+Space → «Terminal») и выполни:

```bash
ls -la ~/.ssh/
ls -la ~/Desktop/Проекты/STAR_VPN/star_vpn_key*
```

Ключ мог остаться в двух местах: в `~/.ssh/star_vpn_key` (так его ищет
`deploy.sh`) или прямо в папке проекта — в `.gitignore` есть строка
`star_vpn_key`, то есть когда-то он лежал именно там.

### Если ключ нашёлся → сразу подключайся

```bash
chmod 600 ~/.ssh/star_vpn_key          # SSH откажется работать с ключом, доступным всем
ssh -i ~/.ssh/star_vpn_key root@64.188.60.178
```

Если ключ лежит в папке проекта — сначала перенеси его на место:

```bash
mkdir -p ~/.ssh
mv ~/Desktop/Проекты/STAR_VPN/star_vpn_key ~/.ssh/star_vpn_key
chmod 700 ~/.ssh && chmod 600 ~/.ssh/star_vpn_key
```

Дальше переходи к **Шагу 3**.

---

## Шаг 2. Если ключа нет — сделать новый

### 2.1. Создать ключ на маке

```bash
ssh-keygen -t ed25519 -f ~/.ssh/star_vpn_key -C "mac-starvpn" -N ""
```

`-N ""` — без пароля на ключ, чтобы `deploy.sh` работал без запросов.

### 2.2. Попробовать вход по паролю

Пароль `root` есть в панели FirstVDS (там же его можно сбросить).
Пароль в терминале **вводится, а не вставляется** — это нормально, символы
не отображаются.

```bash
ssh-copy-id -i ~/.ssh/star_vpn_key.pub root@64.188.60.178
```

Команда сама зальёт публичный ключ в `/root/.ssh/authorized_keys`.
После неё проверь:

```bash
ssh -i ~/.ssh/star_vpn_key root@64.188.60.178
```

### 2.3. Если вход по паролю запрещён (`Permission denied (publickey)`)

Тогда один раз зайди в **браузерную консоль FirstVDS** и включи пароль —
команды короткие, набираются руками:

```bash
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
grep -rn PasswordAuthentication /etc/ssh/sshd_config.d/
systemctl restart ssh
```

Вторая строка важна: на Debian 12 настройки часто переопределяются
файлами в `/etc/ssh/sshd_config.d/` (например `50-cloud-init.conf`) —
если там `PasswordAuthentication no`, поправь и его тем же `sed`.

После этого вернись к пункту 2.2. Когда ключ заработает, пароль можно
выключить обратно (`PasswordAuthentication no` + `systemctl restart ssh`).

---

## Шаг 3. Сделать короткий алиас

Чтобы не писать IP и путь к ключу каждый раз:

```bash
cat >> ~/.ssh/config << 'EOF'

Host starvpn
    HostName 64.188.60.178
    User root
    IdentityFile ~/.ssh/star_vpn_key
    ServerAliveInterval 30
    ServerAliveCountMax 6
EOF
chmod 600 ~/.ssh/config
```

Теперь подключение — одна команда:

```bash
ssh starvpn
```

`ServerAliveInterval` не даёт сессии отваливаться при простое — та самая
боль браузерной консоли.

---

## Шаг 4. Что делать после входа

```bash
cd /root/STAR_VPN/infra
docker compose ps                 # статус контейнеров
docker compose logs -f bot        # живые логи бота (Ctrl+C — выйти)
docker compose restart bot        # рестарт после git pull
cd /root/STAR_VPN && git pull     # подтянуть код
```

Можно и не заходя на сервер, одной строкой с мака:

```bash
ssh starvpn "cd /root/STAR_VPN && git pull && cd infra && docker compose restart bot"
```

---

## Шаг 5. Деплой с мака

### Вариант А — `deploy.sh` (rsync только папки `bot/`)

Лежит в корне проекта, уже настроен на этот сервер и ключ:

```bash
cd ~/Desktop/Проекты/STAR_VPN
./deploy.sh
```

### Вариант Б — push в bare-repo (полная пересборка)

На сервере есть `/root/STAR_VPN.git` с хуком `post-receive`, который
делает `docker compose down && up --build -d`. Подключить его как remote:

```bash
cd ~/Desktop/Проекты/STAR_VPN
git remote add prod ssh://root@64.188.60.178/root/STAR_VPN.git   # один раз
git push prod main
```

---

## Частые ошибки

| Сообщение | Что делать |
|-----------|-----------|
| `WARNING: UNPROTECTED PRIVATE KEY FILE!` | `chmod 600 ~/.ssh/star_vpn_key` |
| `Permission denied (publickey)` | Ключа нет на сервере — Шаг 2 |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | Сервер переустанавливали: `ssh-keygen -R 64.188.60.178`, затем подключиться заново |
| `Connection timed out` | Сервер выключен или IP сменился — проверь в панели FirstVDS |
| `Could not resolve hostname` | Опечатка в IP или алиасе `starvpn` |

---

## Мелочи про сам Terminal на маке

- Вставка — **Cmd+V**, копирование — **Cmd+C** (в браузерной консоли не работало именно это).
- Автодополнение путей — **Tab**.
- Предыдущая команда — **стрелка вверх**.
- Прервать процесс (например `logs -f`) — **Ctrl+C**.
- Выйти с сервера обратно на мак — `exit` или **Ctrl+D**.
