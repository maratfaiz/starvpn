"""Рендер CRUD wiki-статей (созданных из админ-панели) — та же визуальная
тема, что и у статичных статей в landing/wiki/, но собирается из БД."""

import html
import re

_LINK_RE = re.compile(r'\[([^\]]+)\]\((https?://[^\s)]+)\)')
_BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
_ITALIC_RE = re.compile(r'(?<!\*)\*([^*\n]+?)\*(?!\*)')


def _inline_markdown(escaped_text: str) -> str:
    """Применяет **bold**, *italic*, [text](url) к уже HTML-экранированному тексту."""
    text = _LINK_RE.sub(
        lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener">{m.group(1)}</a>',
        escaped_text,
    )
    text = _BOLD_RE.sub(lambda m: f'<strong>{m.group(1)}</strong>', text)
    text = _ITALIC_RE.sub(lambda m: f'<em>{m.group(1)}</em>', text)
    return text


def _render_body(body: str) -> str:
    """Абзацы разделяются пустой строкой. Блок, где каждая строка начинается
    с "- " или "* ", рендерится как маркированный список. Внутри поддерживается
    базовый markdown: **bold**, *italic*, [text](url)."""
    parts = []
    for block in body.split("\n\n"):
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        if all(ln.startswith("- ") or ln.startswith("* ") for ln in lines):
            items = "".join(
                f"<li>{_inline_markdown(html.escape(ln[2:].strip()))}</li>" for ln in lines
            )
            parts.append(f"<ul>{items}</ul>")
        else:
            escaped = html.escape(block.strip()).replace("\n", "<br>")
            parts.append(f"<p>{_inline_markdown(escaped)}</p>")
    return "".join(parts)


def render_wiki_article_page(*, slug: str, title: str, lede: str, body: str, section: str) -> str:
    safe_title = html.escape(title)
    safe_lede = html.escape(lede)
    safe_section = html.escape(section)
    paragraphs = _render_body(body)

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{safe_title} — STAR VPN Wiki</title>
<meta name="description" content="{safe_lede}">
<link rel="icon" href="/logo.png" type="image/png">
<link rel="apple-touch-icon" href="/logo.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth;-webkit-font-smoothing:antialiased}}
:root{{
  --gold:#FFB800;--gold2:#FFD84D;
  --gold-border:rgba(255,184,0,0.18);--gold-dim:rgba(255,184,0,0.08);
  --bg:#060606;--bg2:rgba(255,255,255,0.025);
  --text:#EBE0CC;--text2:#8A7A60;--text3:#3A3028;--max:900px;
}}
body{{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,sans-serif;font-size:16px;line-height:1.75;overflow-x:hidden}}
#nav{{position:fixed;top:0;left:0;right:0;z-index:100;padding:0 24px;background:rgba(6,6,6,.85);backdrop-filter:blur(28px);border-bottom:1px solid var(--gold-border)}}
.nav-inner{{max-width:var(--max);margin:0 auto;display:flex;align-items:center;height:64px;gap:32px}}
.nav-logo{{display:flex;align-items:center;gap:10px;text-decoration:none;flex-shrink:0}}
.nav-logo img{{width:30px;height:30px;border-radius:8px}}
.nav-logo-text{{font-family:'Space Grotesk',sans-serif;font-size:18px;font-weight:700;color:var(--gold)}}
.nav-links{{display:flex;gap:26px;flex:1}}
.nav-links a{{font-size:13px;font-weight:500;color:var(--text2);text-decoration:none}}
.nav-links a:hover,.nav-links a.active{{color:var(--gold)}}
@media(max-width:768px){{.nav-links{{display:none}}}}
.wrap{{position:relative;z-index:2;max-width:var(--max);margin:0 auto;padding:0 24px}}
.back-nav{{padding-top:118px}}
.back-link{{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--text2);text-decoration:none}}
.back-link:hover{{color:var(--gold)}}
.doc-hero{{padding:28px 0 40px}}
.doc-badge{{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--gold-border);border-radius:100px;padding:6px 20px;margin-bottom:24px;font-size:11px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--gold);background:var(--gold-dim)}}
.doc-title{{font-family:'Space Grotesk',sans-serif;font-size:clamp(30px,6vw,48px);font-weight:700;line-height:1.1;margin-bottom:14px}}
.doc-lede{{font-size:16px;color:var(--text2);max-width:60ch}}
.doc-body{{padding:24px 0 96px;font-size:15.5px;color:var(--text2);line-height:1.9}}
.doc-body p{{margin-bottom:16px}}
.doc-body strong{{color:var(--text);font-weight:600}}
.doc-body em{{color:var(--text);font-style:italic}}
.doc-body a{{color:var(--gold);text-decoration:none;border-bottom:1px solid var(--gold-border)}}
.doc-body a:hover{{border-color:var(--gold)}}
.doc-body ul{{margin:0 0 16px;padding-left:22px}}
.doc-body li{{margin-bottom:8px}}
footer{{border-top:1px solid var(--gold-border);padding:52px 24px 40px;text-align:center}}
.footer-links{{display:flex;gap:24px;justify-content:center;flex-wrap:wrap;margin-bottom:20px}}
.footer-links a{{font-size:13px;color:var(--text3);text-decoration:none}}
.footer-links a:hover{{color:var(--gold)}}
.footer-copy{{font-size:12px;color:var(--text3)}}
</style>
</head>
<body>
<nav id="nav">
  <div class="nav-inner">
    <a class="nav-logo" href="/"><img src="/logo.png" alt="STAR VPN"><span class="nav-logo-text">STAR VPN</span></a>
    <div class="nav-links">
      <a href="/tariffs">Тарифы</a>
      <a href="/connect">Подключение</a>
      <a href="/wiki" class="active">Wiki</a>
      <a href="/login">Войти</a>
    </div>
  </div>
</nav>
<main>
<div class="wrap">
  <div class="back-nav">
    <a href="/wiki" class="back-link">← Назад в Wiki</a>
  </div>
  <div class="doc-hero">
    <div class="doc-badge">Wiki · {safe_section}</div>
    <h1 class="doc-title">{safe_title}</h1>
    <p class="doc-lede">{safe_lede}</p>
  </div>
  <div class="doc-body">{paragraphs}</div>
</div>
</main>
<footer>
  <div class="footer-links">
    <a href="/tariffs">Тарифы</a><a href="/wiki">Wiki</a><a href="/connect">Подключение</a>
    <a href="/privacy">Конфиденциальность</a><a href="/terms">Условия</a>
    <a href="https://t.me/hashprojects">Поддержка</a>
  </div>
  <div class="footer-copy">© 2026 STAR VPN · VLESS Reality · Zero Logs</div>
</footer>
</body>
</html>"""
