"""
Страница подписки для браузера — когда кто-то открывает /sub/{username}
не из VPN-клиента, а просто по ссылке. Показывает статус подписки и
пошаговую установку с выбором платформы (в первую очередь Happ —
deep-link на "Добавить подписку" проверен по реальному шаблону страниц
подписки Marzban: happ://add/{url_подписки}).

VPN-клиенты (Happ, v2rayNG, ...) отправляют свой User-Agent — им, как
и раньше, отдаётся сырое base64-тело подписки в api.py, эта страница
их не касается.
"""

import html
import json
import urllib.parse

VPN_CLIENT_UA_MARKERS = (
    "happ", "v2rayng", "v2box", "v2raytun", "streisand", "shadowrocket",
    "clash", "sing-box", "singbox", "hiddify", "nekobox", "nekoray",
    "quantumult", "surfboard", "loon", "stash", "karing",
)


def is_vpn_client(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    return any(marker in ua for marker in VPN_CLIENT_UA_MARKERS)


# platform -> (client name, download blurb, store href, store label)
_CLIENTS = {
    "ios": (
        "Happ",
        "Установите Happ из App Store. Запустите приложение, в окне запроса разрешения на VPN нажмите «Разрешить» и введите код-пароль устройства.",
        "https://apps.apple.com/us/app/happ-proxy-utility/id6504287215",
        "Открыть в App Store",
    ),
    "android": (
        "v2rayNG",
        "Установите v2rayNG из Google Play. Запустите приложение и разрешите добавление VPN-конфигурации.",
        "https://play.google.com/store/apps/details?id=com.v2ray.ang",
        "Открыть в Google Play",
    ),
    "windows": (
        "v2rayN",
        "Скачайте v2rayN со страницы релизов проекта на GitHub и распакуйте архив. Запустите v2rayN.exe.",
        "https://github.com/2dust/v2rayN/releases",
        "Скачать v2rayN",
    ),
    "mac": (
        "V2Box",
        "Установите V2Box из App Store. Запустите приложение и разрешите добавление VPN-конфигурации.",
        "https://apps.apple.com/app/v2box-v2ray-client/id6446814690",
        "Открыть в App Store",
    ),
}


def render_subscription_page(
    *,
    sub_url: str,
    display_name: str,
    is_active: bool,
    days_left: int | None,
    bot_username: str,
) -> str:
    status_label = (
        f"Истекает через {days_left} дн." if is_active and days_left is not None
        else "Подписка закончилась" if not is_active
        else "Активна"
    )
    status_color = "#4ADE80" if is_active else "#F87171"
    status_icon = (
        '<svg viewBox="0 0 24 24" fill="none" stroke="#4ADE80" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px">'
        '<path d="M20 6L9 17l-5-5"/></svg>'
        if is_active else
        '<svg viewBox="0 0 24 24" fill="none" stroke="#F87171" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px">'
        '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'
    )
    status_icon_bg = "rgba(74,222,128,.12)" if is_active else "rgba(248,113,113,.12)"
    status_icon_border = "rgba(74,222,128,.3)" if is_active else "rgba(248,113,113,.3)"

    safe_name = html.escape(display_name)
    safe_sub_url = html.escape(sub_url)
    tg_share = f"https://t.me/share/url?url={urllib.parse.quote(sub_url)}&text=STAR%20VPN"

    client_blocks = ""
    for platform, (client_name, download_text, store_href, store_label) in _CLIENTS.items():
        happ_deeplink = f"happ://add/{sub_url}" if platform == "ios" else None
        deeplink_action = (
            f'<a href="{html.escape(happ_deeplink)}" class="step-btn step-btn--gold">Добавить подписку</a>'
            if happ_deeplink else
            f'<div class="linkbox">{safe_sub_url}</div>'
            f'<div class="step-hint">Скопируйте ссылку выше кнопкой 📋 и добавьте её как подписку в настройках приложения.</div>'
        )
        client_blocks += f"""
<div class="client-block" data-platform="{platform}" style="display:none">
  <div class="client-badge">
    <svg viewBox="0 0 24 24" fill="#FFB800" style="width:18px;height:18px"><path d="M12 3.6l2.6 5.3 5.8.8-4.2 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8L3.6 9.7l5.8-.8z"/></svg>
    <span>{client_name}</span>
  </div>
  <div class="steps">
    <div class="step">
      <span class="step-num">1</span>
      <div class="step-title">Скачайте {client_name}</div>
      <div class="step-text">{download_text}</div>
      <a class="step-btn step-btn--outline" href="{store_href}" target="_blank">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 4h6v6M20 4l-9 9M18 13v5a2 2 0 01-2 2H6a2 2 0 01-2-2V8a2 2 0 012-2h5"/></svg>
        {store_label}
      </a>
    </div>
    <div class="step">
      <span class="step-num">2</span>
      <div class="step-title">Добавьте подписку</div>
      <div class="step-text">Нажмите кнопку ниже — приложение откроется, и подписка добавится автоматически.</div>
      {deeplink_action}
    </div>
    <div class="step">
      <span class="step-num">3</span>
      <div class="step-title">Подключитесь</div>
      <div class="step-text">В приложении выберите сервер из списка и нажмите большую кнопку подключения. Готово — интернет открыт.</div>
    </div>
  </div>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Моя подписка — STAR VPN</title>
<link rel="icon" href="/logo.png" type="image/png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth;-webkit-font-smoothing:antialiased}}
:root{{
  --gold:#FFB800;--gold2:#FFD84D;
  --bg:#060606;--card:#0B0A09;
  --text:#EBE0CC;--text2:rgba(235,224,204,.55);--text3:rgba(235,224,204,.35);
  --border:rgba(255,184,0,.18);
}}
body{{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,sans-serif;
  min-height:100vh;font-size:15px;line-height:1.6}}
a{{color:var(--gold);text-decoration:none}}
a:hover{{color:var(--gold2)}}
select{{appearance:none;-webkit-appearance:none}}
.wrap{{position:relative;z-index:2;max-width:620px;margin:0 auto;padding:28px 20px 60px}}

header{{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:32px}}
.logo{{font-family:'Space Grotesk',sans-serif;font-size:20px;font-weight:700;letter-spacing:.04em;color:var(--gold)}}
.header-actions{{display:flex;gap:10px}}
.icon-btn{{cursor:pointer;width:44px;height:44px;border-radius:12px;background:rgba(255,255,255,.04);
  border:1px solid rgba(255,255,255,.1);display:flex;align-items:center;justify-content:center;
  color:var(--text2);text-decoration:none;transition:border-color .2s}}
.icon-btn:hover{{border-color:var(--border)}}
.icon-btn--gold{{background:rgba(255,184,0,.12);border-color:rgba(255,184,0,.3);color:var(--gold)}}
.icon-btn--gold:hover{{background:rgba(255,184,0,.2)}}
.icon-btn.copied{{color:#4ADE80}}

.status-card{{background:rgba(255,255,255,.028);border:1px solid rgba(255,255,255,.1);
  border-radius:18px;padding:18px 20px;margin-bottom:32px}}
.status-top{{display:flex;align-items:center;gap:14px}}
.status-dot{{width:38px;height:38px;border-radius:11px;background:{status_icon_bg};
  border:1px solid {status_icon_border};display:flex;align-items:center;justify-content:center;flex-shrink:0}}
.status-name{{font-family:'JetBrains Mono',monospace;font-size:15px;font-weight:500;color:var(--text);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.status-sub{{font-size:12.5px;color:{status_color};margin-top:3px;font-weight:600}}
.chevron{{cursor:pointer;color:var(--text2);padding:6px;transition:transform .2s}}
.chevron.open{{transform:rotate(180deg)}}
.status-meta{{margin-top:16px;padding-top:16px;border-top:1px solid rgba(255,255,255,.07);
  display:none;grid-template-columns:1fr 1fr;gap:1px;background:rgba(255,255,255,.07);
  border-radius:12px;overflow:hidden}}
.status-meta.open{{display:grid}}
.meta-cell{{background:var(--card);padding:13px 15px}}
.meta-label{{font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--text2);margin-bottom:4px}}
.meta-value{{font-family:'Space Grotesk',sans-serif;font-size:14px;font-weight:600;color:var(--text)}}
.meta-value--gold{{color:var(--gold)}}

.install-head{{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:22px;flex-wrap:wrap}}
.install-head h1{{font-family:'Space Grotesk',sans-serif;font-size:clamp(24px,3.4vw,32px);font-weight:700;letter-spacing:-.01em}}
.select-wrap{{position:relative}}
#platform-select{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.12);border-radius:12px;
  padding:12px 40px 12px 16px;color:var(--text);font-family:'Space Grotesk',sans-serif;font-size:14px;
  font-weight:600;cursor:pointer;outline:none}}
.select-chevron{{position:absolute;right:14px;top:50%;transform:translateY(-50%);pointer-events:none;color:var(--text2)}}

.client-badge{{border:1px solid rgba(255,184,0,.35);border-radius:14px;padding:16px;margin-bottom:26px;
  display:flex;align-items:center;justify-content:center;gap:10px;background:rgba(255,184,0,.04);
  font-family:'Space Grotesk',sans-serif;font-size:16px;font-weight:600;color:var(--gold)}}

.steps{{position:relative;padding-left:44px}}
.steps::before{{content:'';position:absolute;left:15px;top:16px;bottom:44px;width:2px;
  background:linear-gradient(180deg,var(--gold),rgba(255,184,0,.2))}}
.step{{position:relative;padding-bottom:28px}}
.step:last-child{{padding-bottom:0}}
.step-num{{position:absolute;left:-44px;top:0;width:32px;height:32px;border-radius:50%;background:var(--card);
  border:1px solid rgba(255,184,0,.4);display:flex;align-items:center;justify-content:center;
  font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:13px;color:var(--gold)}}
.step-title{{font-family:'Space Grotesk',sans-serif;font-size:17px;font-weight:600;color:var(--text);margin-bottom:6px}}
.step-text{{font-size:14px;line-height:1.6;color:var(--text2);margin-bottom:14px}}
.step-btn{{display:flex;align-items:center;justify-content:center;gap:9px;font-family:'Space Grotesk',sans-serif;
  font-size:14px;font-weight:700;padding:13px 20px;border-radius:12px;text-decoration:none;min-height:46px}}
.step-btn--gold{{background:var(--gold);color:#000}}
.step-btn--outline{{background:rgba(255,184,0,.1);color:var(--gold);border:1px solid rgba(255,184,0,.3)}}
.linkbox{{background:rgba(0,0,0,.5);border:1px solid rgba(255,255,255,.08);border-radius:11px;padding:12px 14px;
  font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text2);word-break:break-all;margin-bottom:8px}}
.step-hint{{font-size:12.5px;color:var(--text2)}}

.footer-links{{margin-top:16px;padding-top:24px;border-top:1px solid rgba(255,255,255,.07);
  display:flex;flex-direction:column;align-items:center;gap:14px;text-align:center}}
.footer-links a{{font-size:13.5px;font-weight:500;color:var(--text2)}}
.footer-links a:hover{{color:var(--gold)}}
.support-line{{font-size:12px;color:var(--text3)}}

.toast{{position:fixed;left:50%;transform:translateX(-50%);bottom:24px;z-index:300;
  background:rgba(12,11,10,.97);border:1px solid rgba(255,184,0,.35);border-radius:12px;
  padding:13px 20px;box-shadow:0 20px 50px rgba(0,0,0,.6);display:none;align-items:center;gap:11px}}
.toast.show{{display:flex}}
.toast-dot{{width:7px;height:7px;border-radius:50%;background:var(--gold);flex-shrink:0}}
.toast span{{font-size:13.5px;color:var(--text)}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <a class="logo" href="/">STAR VPN</a>
    <div class="header-actions">
      <div class="icon-btn" id="copy-btn" title="Скопировать ссылку">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" style="width:19px;height:19px"><path d="M10 13a5 5 0 007 0l2-2a5 5 0 00-7-7l-1 1M14 11a5 5 0 00-7 0l-2 2a5 5 0 007 7l1-1"/></svg>
      </div>
      <a class="icon-btn icon-btn--gold" href="{tg_share}" target="_blank" title="Поделиться в Telegram">
        <svg viewBox="0 0 24 24" fill="none" stroke="#FFB800" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" style="width:19px;height:19px"><path d="M22 3L2 10.5l6.5 2.5L11 20l3-4.5 5 3z"/></svg>
      </a>
    </div>
  </header>

  <div class="status-card">
    <div class="status-top">
      <span class="status-dot">{status_icon}</span>
      <div style="flex:1;min-width:0">
        <div class="status-name">{safe_name}</div>
        <div class="status-sub">{html.escape(status_label)}</div>
      </div>
      <div class="chevron" id="chevron">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px"><path d="M6 9l6 6 6-6"/></svg>
      </div>
    </div>
    <div class="status-meta" id="status-meta">
      <div class="meta-cell"><div class="meta-label">Статус</div><div class="meta-value">{html.escape(status_label)}</div></div>
      <div class="meta-cell"><div class="meta-label">Протокол</div><div class="meta-value meta-value--gold">VLESS + Reality</div></div>
    </div>
  </div>

  <div class="install-head">
    <h1>Установка</h1>
    <div class="select-wrap">
      <select id="platform-select">
        <option value="ios">iOS · iPhone, iPad</option>
        <option value="android">Android</option>
        <option value="windows">Windows</option>
        <option value="mac">macOS</option>
      </select>
      <span class="select-chevron">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="width:16px;height:16px"><path d="M8 9l4-4 4 4M8 15l4 4 4-4"/></svg>
      </span>
    </div>
  </div>

  {client_blocks}

  <div class="footer-links">
    <a href="/connect">Подробные инструкции по подключению →</a>
    <div class="support-line">Нужна помощь? <a href="https://t.me/{html.escape(bot_username)}">@{html.escape(bot_username)}</a></div>
  </div>
</div>

<div class="toast" id="toast"><span class="toast-dot"></span><span id="toast-text"></span></div>

<script>
const subUrl = {json.dumps(sub_url)};
const select = document.getElementById('platform-select');
const blocks = document.querySelectorAll('.client-block');
function showPlatform(p){{
  blocks.forEach(b => b.style.display = b.dataset.platform === p ? 'block' : 'none');
}}
select.addEventListener('change', () => showPlatform(select.value));
showPlatform('ios');

const chevron = document.getElementById('chevron');
const meta = document.getElementById('status-meta');
chevron.addEventListener('click', () => {{
  chevron.classList.toggle('open');
  meta.classList.toggle('open');
}});

const toast = document.getElementById('toast');
const toastText = document.getElementById('toast-text');
let toastTimer;
function flash(msg){{
  toastText.textContent = msg;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2000);
}}
document.getElementById('copy-btn').addEventListener('click', function(){{
  try {{ navigator.clipboard && navigator.clipboard.writeText(subUrl); }} catch (e) {{}}
  this.classList.add('copied');
  flash('Ссылка подписки скопирована');
  setTimeout(() => this.classList.remove('copied'), 2000);
}});
</script>
</body>
</html>"""
