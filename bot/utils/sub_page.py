"""
Страница подписки для браузера — когда кто-то открывает /sub/{username}
не из VPN-клиента, а просто по ссылке. Показывает статус подписки и
пошаговую установку (в первую очередь Happ — deep-link на "Добавить
подписку" проверен по реальному шаблону страниц подписки Marzban:
happ://add/{url_подписки}).

VPN-клиенты (Happ, v2rayNG, ...) отправляют свой User-Agent — им, как
и раньше, отдаётся сырое base64-тело подписки в api.py, эта страница
их не касается.
"""

import html
import urllib.parse

VPN_CLIENT_UA_MARKERS = (
    "happ", "v2rayng", "v2box", "v2raytun", "streisand", "shadowrocket",
    "clash", "sing-box", "singbox", "hiddify", "nekobox", "nekoray",
    "quantumult", "surfboard", "loon", "stash", "karing",
)


def is_vpn_client(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    return any(marker in ua for marker in VPN_CLIENT_UA_MARKERS)


def render_subscription_page(
    *,
    sub_url: str,
    display_name: str,
    is_active: bool,
    days_left: int | None,
    bot_username: str,
) -> str:
    happ_deeplink = f"happ://add/{sub_url}"
    status_text = (
        f"Истекает через {days_left} дн." if is_active and days_left is not None
        else "Подписка закончилась" if not is_active
        else "Активна"
    )
    status_color = "#4ADE80" if is_active else "#F87171"
    status_icon = (
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4ADE80" stroke-width="3" '
        'stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
        if is_active else
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F87171" stroke-width="3" '
        'stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/>'
        '<line x1="6" y1="6" x2="18" y2="18"/></svg>'
    )
    domain = urllib.parse.urlparse(sub_url).netloc
    safe_name = html.escape(display_name)
    safe_sub_url = html.escape(sub_url)
    safe_happ_link = html.escape(happ_deeplink)
    tg_share = f"https://t.me/share/url?url={urllib.parse.quote(sub_url)}&text=STAR%20VPN"

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>STAR VPN — Подписка</title>
<link rel="icon" href="/logo.png" type="image/png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --gold:#FFB800;--gold2:#FFD84D;
  --bg:#060606;--card:#0B0A09;
  --text:#EBE0CC;--text2:rgba(235,224,204,.55);--text3:rgba(235,224,204,.35);
  --border:rgba(255,184,0,.18);
}}
body{{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,sans-serif;
  min-height:100vh;padding:20px 16px 60px;font-size:15px;line-height:1.6}}
.wrap{{max-width:480px;margin:0 auto}}

header{{display:flex;align-items:center;gap:10px;margin-bottom:20px}}
.logo{{width:34px;height:34px;border-radius:10px;background:linear-gradient(145deg,var(--gold),var(--gold2));
  display:flex;align-items:center;justify-content:center;flex-shrink:0}}
.logo svg{{width:18px;height:18px}}
.app-name{{font-family:'Space Grotesk',sans-serif;font-weight:800;font-size:16px;flex-shrink:0}}
.domain-pill{{flex:1;min-width:0;background:rgba(255,255,255,.05);border:1px solid var(--border);
  border-radius:100px;padding:8px 14px;font-size:12px;color:var(--text2);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.icon-btn{{width:38px;height:38px;flex-shrink:0;border-radius:12px;background:rgba(255,255,255,.05);
  border:1px solid var(--border);display:flex;align-items:center;justify-content:center;
  cursor:pointer;text-decoration:none;color:var(--text)}}

.status-card{{display:flex;align-items:center;gap:12px;background:var(--card);border:1px solid var(--border);
  border-radius:18px;padding:16px 18px;margin-bottom:32px}}
.status-dot{{width:34px;height:34px;border-radius:50%;background:rgba(46,217,166,.12);
  display:flex;align-items:center;justify-content:center;flex-shrink:0}}
.status-name{{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:16px}}
.status-sub{{font-size:13px;color:{status_color};margin-top:2px;font-weight:600}}

h2.section{{font-family:'Space Grotesk',sans-serif;font-size:20px;margin-bottom:18px}}

.steps{{position:relative;padding-left:44px}}
.steps::before{{content:'';position:absolute;left:16px;top:14px;bottom:14px;width:2px;background:var(--border)}}
.step{{position:relative;margin-bottom:28px}}
.step:last-child{{margin-bottom:0}}
.step-num{{position:absolute;left:-44px;top:0;width:32px;height:32px;border-radius:50%;
  background:rgba(247,206,104,.12);border:1px solid rgba(247,206,104,.3);color:var(--gold);
  display:flex;align-items:center;justify-content:center;font-family:'Space Grotesk',sans-serif;
  font-weight:700;font-size:13px}}
.step-title{{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:16px;margin-bottom:6px}}
.step-text{{color:var(--text2);font-size:13.5px;margin-bottom:14px}}

.btn{{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;
  border:none;border-radius:14px;padding:14px;font-family:'Space Grotesk',sans-serif;
  font-weight:700;font-size:14px;cursor:pointer;text-decoration:none;margin-bottom:10px}}
.btn-gold{{background:linear-gradient(135deg,var(--gold),var(--gold2));color:#1A1408}}
.btn-outline{{background:rgba(255,255,255,.04);border:1px solid var(--border);color:var(--text)}}

.linkbox{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 14px;
  font-family:monospace;font-size:11px;color:var(--text2);word-break:break-all;margin-bottom:14px}}
.alt-note{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;
  font-size:13px;color:var(--text2);line-height:1.65;margin-top:8px}}
.alt-note a{{color:var(--gold);text-decoration:none}}

footer{{text-align:center;margin-top:44px;color:var(--text3);font-size:12px}}
footer a{{color:var(--gold);text-decoration:none}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="logo">
      <svg viewBox="0 0 24 24" fill="#1A1408"><path d="M12 1l3.09 6.26L22 8.27l-5 4.87 1.18 6.88L12 16.9l-6.18 3.12L7 13.14 2 8.27l6.91-1.01L12 1z"/></svg>
    </div>
    <span class="app-name">STAR VPN</span>
    <div class="domain-pill">{html.escape(domain)}</div>
    <a class="icon-btn" href="#" onclick="navigator.clipboard.writeText('{safe_sub_url}');this.textContent='✓';return false;" title="Скопировать ссылку">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>
    </a>
    <a class="icon-btn" href="{tg_share}" target="_blank" title="Поделиться в Telegram">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M22 2L2 10.5l6 2.5m14-11l-4 18-8-6m12-12L8 15m0 0l-1 6 4-4"/></svg>
    </a>
  </header>

  <div class="status-card">
    <div class="status-dot">{status_icon}</div>
    <div>
      <div class="status-name">{safe_name}</div>
      <div class="status-sub">{html.escape(status_text)}</div>
    </div>
  </div>

  <h2 class="section">Установка</h2>
  <div class="steps">
    <div class="step">
      <div class="step-num">1</div>
      <div class="step-title">Установите и откройте Happ</div>
      <div class="step-text">Скачайте приложение из App Store или Google Play.</div>
      <a class="btn btn-outline" href="https://apps.apple.com/us/app/happ-proxy-utility/id6504287215" target="_blank">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
        Открыть в App Store (iOS)
      </a>
      <a class="btn btn-outline" href="https://play.google.com/store/apps/details?id=com.happproxy" target="_blank">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
        Открыть в Google Play (Android)
      </a>
    </div>
    <div class="step">
      <div class="step-num">2</div>
      <div class="step-title">Добавить подписку</div>
      <div class="step-text">Нажмите кнопку ниже — приложение откроется, и подписка добавится автоматически.</div>
      <a class="btn btn-gold" href="{safe_happ_link}">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#1A1408" stroke-width="2.4"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        Добавить подписку
      </a>
      <div class="linkbox">{safe_sub_url}</div>
    </div>
    <div class="step">
      <div class="step-num">3</div>
      <div class="step-title">Подключитесь и используйте</div>
      <div class="step-text">В главном экране Happ нажмите большую кнопку включения — готово, вы под защитой STAR VPN.</div>
    </div>
  </div>

  <div class="alt-note">
    Используете другое приложение — Streisand, v2rayNG, v2rayN, V2Box или NekoRay?
    Скопируйте ссылку выше кнопкой 📋 и добавьте её как подписку в настройках приложения.
    Пошаговые инструкции для каждого устройства — на странице
    <a href="/connect">«Как подключиться»</a>.
  </div>

  <footer>
    Проблемы с подключением? <a href="https://t.me/{html.escape(bot_username)}">Написать в поддержку</a>
  </footer>
</div>
</body>
</html>"""
