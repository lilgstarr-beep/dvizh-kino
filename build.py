"""
ДВИЖ КИНО — автосборка сайта
Тянет видео из ВК группы и генерирует index.html
"""

import os, re, json, requests
from datetime import datetime

# ── НАСТРОЙКИ ──────────────────────────────────────────────────────────────
VK_TOKEN    = os.environ.get("VK_TOKEN", "")   # берётся из GitHub Secret
GROUP_ID    = 24961777                          # ID группы без минуса
VK_API_VER  = "5.131"
OUTPUT_FILE = "index.html"
# ───────────────────────────────────────────────────────────────────────────

CITIES = ["Тула", "Коломна", "Ступино", "Калуга"]

def fetch_videos():
    """Получает все видео из группы через VK API (с пагинацией)."""
    all_videos = []
    offset = 0
    count = 100
    while True:
        resp = requests.get("https://api.vk.com/method/video.get", params={
            "owner_id":     f"-{GROUP_ID}",
            "count":        count,
            "offset":       offset,
            "access_token": VK_TOKEN,
            "v":            VK_API_VER,
        }, timeout=30)
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"VK API error: {data['error']}")
        items = data["response"]["items"]
        all_videos.extend(items)
        print(f"  Загружено: {len(all_videos)} видео...")
        if len(items) < count:
            break
        offset += count
    return all_videos

def extract_city(title):
    m = re.search(r"\((" + "|".join(CITIES) + r")\)", title)
    return m.group(1) if m else ""

def clean_title(t):
    t = re.sub(r"^Киножурнал\s+[«\""\u201c\u201d]?ДВИЖ[»\""\u201c\u201d]?\s*[-\u2014]\s*", "", t, flags=re.I)
    t = re.sub(r"^Киножурнал\s+[«\""\u201c\u201d]?Движ[»\""\u201c\u201d]?\s*[-\u2014]\s*", "", t, flags=re.I)
    t = re.sub(r"^Движ\s*[-\u2014]\s*", "", t, flags=re.I)
    for c in CITIES:
        t = re.sub(r"\s*\(" + c + r"\)\s*$", "", t)
    if "Новости Коломны от 28 мая" in t:
        t = "Новости: съёмки нового сезона в Коломне"
    return t.strip()

def best_thumb(imgs):
    # Только VK CDN (userapi.com) — надёжные, без срока действия
    vk = [i for i in imgs if "userapi.com" in i.get("url", "")]
    pool = sorted(vk or imgs, key=lambda x: x.get("width", 0))
    for img in pool:
        if img.get("width", 0) >= 800:
            return img["url"]
    return pool[-1]["url"] if pool else ""

def process_videos(raw):
    result = []
    for v in raw:
        title   = clean_title(v.get("title", ""))
        city    = extract_city(v.get("title", ""))
        thumb   = best_thumb(v.get("image", []))
        year    = datetime.fromtimestamp(v.get("date", 0)).year
        views   = v.get("views", v.get("local_views", 0))
        player  = v.get("player", "").replace("&amp;", "&")
        dur     = v.get("duration", 0)
        dur_str = f"{dur // 60}:{dur % 60:02d}"
        result.append({
            "id":         v["id"],
            "title":      title,
            "city":       city,
            "year":       year,
            "views":      views,
            "dur":        dur_str,
            "player":     player,
            "thumb":      thumb,
            "isNew":      year >= 2026,
            "isFeatured": views >= 800,
        })
    return result

def to_js(films):
    def js_str(s):
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    lines = ["const FILMS=["]
    for f in films:
        lines.append(
            f'  {{id:{f["id"]},title:"{js_str(f["title"])}",city:"{f["city"]}",year:{f["year"]},'
            f'views:{f["views"]},dur:"{f["dur"]}",player:"{js_str(f["player"])}",thumb:"{js_str(f["thumb"])}",'
            f'isNew:{"true" if f["isNew"] else "false"},isFeatured:{"true" if f["isFeatured"] else "false"}}},'
        )
    lines.append("];")
    return "\n".join(lines)

def build_html(films_js, total, updated_at):
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ДВИЖ КИНО</title>
<meta name="description" content="Короткометражное кино из Тулы, Коломны, Ступино и Калуги">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,700;1,400&display=swap" rel="stylesheet">
<style>
:root{{
  --bg:#0c0c10;--surface:#14141a;--surface2:#1e1e26;--border:rgba(255,255,255,.07);
  --gold:#e8bc6a;--red:#e84545;
  --text:#f2f0ed;--text-dim:#8e8c88;--text-muted:#3e3c3a;
  --tula:#f0873c;--kolomna:#3da8e0;--stupino:#44c97a;--kaluga:#a67ee8;
  --cw:280px;--ch:158px;--gap:12px;--r:8px;
}}
*{{margin:0;padding:0;box-sizing:border-box}}
html{{scroll-behavior:smooth}}
body{{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;overflow-x:hidden;min-height:100vh;-webkit-font-smoothing:antialiased}}
body::before{{content:'';position:fixed;inset:0;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)' opacity='.025'/%3E%3C/svg%3E");pointer-events:none;z-index:1000;mix-blend-mode:overlay}}
nav{{position:fixed;top:0;left:0;right:0;z-index:200;height:60px;padding:0 40px;display:flex;align-items:center;justify-content:space-between;transition:background .3s}}
nav.solid{{background:rgba(12,12,16,.96);backdrop-filter:blur(20px);border-bottom:1px solid var(--border)}}
.logo{{font-family:'Playfair Display',serif;font-size:20px;font-weight:700;color:var(--text);text-decoration:none;display:flex;align-items:center;gap:6px}}
.logo-dot{{width:8px;height:8px;background:var(--red);border-radius:50%}}
.nav-links{{display:flex;gap:28px;list-style:none}}
.nav-links a{{color:var(--text-dim);text-decoration:none;font-size:13px;font-weight:500;transition:color .2s}}
.nav-links a:hover{{color:var(--text)}}
.nav-right{{display:flex;align-items:center;gap:12px}}
.nav-count{{font-size:12px;color:var(--text-muted);font-weight:500}}
.hero{{position:relative;height:88vh;min-height:520px;display:flex;align-items:flex-end;overflow:hidden}}
.hero-img{{position:absolute;inset:0;background-size:cover;background-position:center;transition:transform 10s ease}}
.hero-img.loaded{{transform:scale(1.04)}}
.hero-grad{{position:absolute;inset:0;background:linear-gradient(to right,rgba(12,12,16,.98) 0%,rgba(12,12,16,.7) 40%,rgba(12,12,16,.15) 75%,rgba(12,12,16,.4) 100%),linear-gradient(to top,rgba(12,12,16,1) 0%,rgba(12,12,16,.6) 25%,transparent 60%)}}
.hero-body{{position:relative;z-index:2;padding:0 40px 64px;max-width:560px;animation:fadeUp .8s ease both}}
.hero-tags{{display:flex;align-items:center;gap:8px;margin-bottom:16px}}
.hero-tag-live{{display:flex;align-items:center;gap:6px;background:rgba(232,69,69,.15);border:1px solid rgba(232,69,69,.3);color:var(--red);font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;padding:4px 10px;border-radius:20px}}
.hero-tag-live::before{{content:'';width:6px;height:6px;background:var(--red);border-radius:50%;animation:pulse 2s ease infinite}}
@keyframes pulse{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:.4;transform:scale(.7)}}}}
.hero-city-pill{{font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;padding:4px 10px;border-radius:20px}}
.hero-city-pill.tula{{background:rgba(240,135,60,.12);color:var(--tula)}}
.hero-city-pill.kolomna{{background:rgba(61,168,224,.12);color:var(--kolomna)}}
.hero-city-pill.stupino{{background:rgba(68,201,122,.12);color:var(--stupino)}}
.hero-city-pill.kaluga{{background:rgba(166,126,232,.12);color:var(--kaluga)}}
.hero-title{{font-family:'Playfair Display',serif;font-size:clamp(32px,5vw,58px);font-weight:700;line-height:1.08;margin-bottom:14px;color:var(--text)}}
.hero-meta{{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text-dim);margin-bottom:28px}}
.hero-sep{{width:3px;height:3px;background:var(--text-muted);border-radius:50%}}
.hero-views{{display:flex;align-items:center;gap:4px}}
.hero-btns{{display:flex;gap:10px}}
.btn-watch{{display:inline-flex;align-items:center;gap:8px;background:var(--text);color:#0c0c10;padding:13px 26px;border-radius:6px;font-size:14px;font-weight:700;border:none;cursor:pointer;transition:all .18s}}
.btn-watch:hover{{background:#e0ddd8;transform:translateY(-1px)}}
.btn-more{{display:inline-flex;align-items:center;gap:8px;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.14);color:var(--text);padding:13px 22px;border-radius:6px;font-size:14px;font-weight:600;cursor:pointer;transition:all .18s}}
.btn-more:hover{{background:rgba(255,255,255,.16);transform:translateY(-1px)}}
.controls{{padding:32px 40px 0;display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.search-wrap{{position:relative}}
.search-wrap svg{{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--text-muted)}}
.search-input{{background:var(--surface2);border:1px solid var(--border);color:var(--text);font-family:'Inter',sans-serif;font-size:13px;padding:9px 14px 9px 36px;width:240px;border-radius:6px;outline:none;transition:border-color .2s}}
.search-input::placeholder{{color:var(--text-muted)}}
.search-input:focus{{border-color:rgba(255,255,255,.2)}}
.divider{{width:1px;height:22px;background:var(--border);margin:0 4px}}
.flabel{{font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--text-muted)}}
.fbtn{{padding:7px 14px;background:transparent;border:1px solid var(--border);color:var(--text-dim);font-family:'Inter',sans-serif;font-size:12px;font-weight:600;cursor:pointer;border-radius:20px;transition:all .18s}}
.fbtn:hover{{border-color:rgba(255,255,255,.2);color:var(--text)}}
.fbtn.active{{background:var(--text);color:#0c0c10;border-color:var(--text)}}
.fbtn.tula.active{{background:var(--tula);color:#0c0c10;border-color:var(--tula)}}
.fbtn.kolomna.active{{background:var(--kolomna);color:#0c0c10;border-color:var(--kolomna)}}
.fbtn.stupino.active{{background:var(--stupino);color:#0c0c10;border-color:var(--stupino)}}
.fbtn.kaluga.active{{background:var(--kaluga);color:#0c0c10;border-color:var(--kaluga)}}
.sections{{padding:32px 0 80px}}
.sec{{margin-bottom:36px}}
.sec-hdr{{padding:0 40px;display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}}
.sec-title{{font-size:17px;font-weight:700;color:var(--text);letter-spacing:-.01em}}
.sec-count{{font-size:12px;color:var(--text-muted);font-weight:500}}
.sep{{height:1px;margin:0 40px 32px;background:var(--border)}}
.city-sec{{margin-bottom:40px}}
.city-hdr{{padding:0 40px;display:flex;align-items:center;gap:12px;margin-bottom:14px}}
.city-name{{font-size:17px;font-weight:700;letter-spacing:-.01em}}
.city-name.tula{{color:var(--tula)}}.city-name.kolomna{{color:var(--kolomna)}}.city-name.stupino{{color:var(--stupino)}}.city-name.kaluga{{color:var(--kaluga)}}
.city-rule{{flex:1;height:1px;background:var(--border)}}
.city-pill{{font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text-muted);background:var(--surface2);padding:3px 8px;border-radius:10px}}
.row{{display:flex;gap:var(--gap);overflow-x:auto;padding:4px 40px 12px;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;scrollbar-width:none}}
.row::-webkit-scrollbar{{display:none}}
.card{{flex:0 0 var(--cw);width:var(--cw);cursor:pointer;scroll-snap-align:start;transition:transform .22s ease}}
.card:hover{{transform:scale(1.03)}}
.card-thumb-wrap{{width:var(--cw);height:var(--ch);border-radius:var(--r);overflow:hidden;position:relative;background:var(--surface2);margin-bottom:10px}}
.card-thumb-wrap::after{{content:'';position:absolute;inset:0;background:linear-gradient(to top,rgba(0,0,0,.7) 0%,transparent 50%)}}
.card-img{{width:100%;height:100%;object-fit:cover;display:block;opacity:0;transition:opacity .4s ease}}
.card-img.on{{opacity:1}}
.card-play{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity .2s;z-index:2}}
.card:hover .card-play{{opacity:1}}
.card-play-btn{{width:44px;height:44px;background:rgba(255,255,255,.92);border-radius:50%;display:flex;align-items:center;justify-content:center}}
.card-play-btn svg{{fill:#0c0c10;width:18px;height:18px;margin-left:2px}}
.card-dur{{position:absolute;bottom:8px;right:8px;font-size:10px;font-weight:600;color:#fff;background:rgba(0,0,0,.72);padding:2px 6px;border-radius:4px;z-index:2}}
.card-new-badge{{position:absolute;top:8px;left:8px;background:var(--red);color:#fff;font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;padding:2px 7px;border-radius:4px;z-index:2}}
.card-hot-badge{{position:absolute;top:8px;left:8px;background:rgba(232,188,106,.9);color:#0c0c10;font-size:9px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;padding:2px 7px;border-radius:4px;z-index:2}}
.card-info{{padding:0 2px}}
.card-title{{font-size:13px;font-weight:600;color:var(--text);line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;margin-bottom:5px;letter-spacing:-.01em}}
.card-foot{{display:flex;align-items:center;gap:6px}}
.card-city-pill{{font-size:10px;font-weight:600;padding:2px 8px;border-radius:10px;letter-spacing:.04em}}
.card-city-pill.tula{{background:rgba(240,135,60,.12);color:var(--tula)}}
.card-city-pill.kolomna{{background:rgba(61,168,224,.12);color:var(--kolomna)}}
.card-city-pill.stupino{{background:rgba(68,201,122,.12);color:var(--stupino)}}
.card-city-pill.kaluga{{background:rgba(166,126,232,.12);color:var(--kaluga)}}
.card-city-pill.x{{background:rgba(255,255,255,.05);color:var(--text-muted)}}
.card-views{{font-size:11px;color:var(--text-muted);font-weight:500}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--cw),1fr));gap:18px var(--gap);padding:0 40px}}
.grid .card{{flex:none;width:100%}}
.grid .card-thumb-wrap{{width:100%;height:0;padding-bottom:56.25%;position:relative}}
.grid .card-img{{position:absolute;inset:0;width:100%;height:100%}}
.modal-bg{{position:fixed;inset:0;z-index:500;background:rgba(0,0,0,.88);backdrop-filter:blur(16px);display:flex;align-items:center;justify-content:center;opacity:0;pointer-events:none;transition:opacity .25s;padding:16px}}
.modal-bg.open{{opacity:1;pointer-events:all}}
.modal{{width:100%;max-width:900px;background:var(--surface);border-radius:12px;overflow:hidden;position:relative;transform:scale(.95) translateY(14px);transition:transform .25s;box-shadow:0 32px 80px rgba(0,0,0,.8)}}
.modal-bg.open .modal{{transform:scale(1) translateY(0)}}
.modal-video{{width:100%;aspect-ratio:16/9;background:#000}}
.modal-video iframe{{width:100%;height:100%;border:none;display:block}}
.modal-close{{position:absolute;top:12px;right:12px;z-index:10;width:32px;height:32px;background:rgba(0,0,0,.6);border:1px solid rgba(255,255,255,.12);border-radius:50%;color:var(--text-dim);font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .18s}}
.modal-close:hover{{background:rgba(255,255,255,.12);color:var(--text)}}
.modal-body{{padding:18px 22px 20px;display:flex;justify-content:space-between;align-items:flex-start;gap:16px}}
.modal-info{{flex:1;min-width:0}}
.modal-title{{font-size:18px;font-weight:700;color:var(--text);margin-bottom:8px;letter-spacing:-.01em}}
.modal-meta{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
.m-pill{{font-size:11px;font-weight:600;padding:3px 9px;border-radius:10px}}
.m-pill.tula{{background:rgba(240,135,60,.12);color:var(--tula)}}.m-pill.kolomna{{background:rgba(61,168,224,.12);color:var(--kolomna)}}.m-pill.stupino{{background:rgba(68,201,122,.12);color:var(--stupino)}}.m-pill.kaluga{{background:rgba(166,126,232,.12);color:var(--kaluga)}}
.m-info{{font-size:12px;color:var(--text-muted);font-weight:500}}
.modal-vk{{display:inline-flex;align-items:center;gap:7px;background:rgba(255,255,255,.07);border:1px solid var(--border);color:var(--text-dim);text-decoration:none;font-size:12px;font-weight:600;padding:9px 16px;border-radius:6px;white-space:nowrap;flex-shrink:0;transition:all .18s}}
.modal-vk:hover{{background:rgba(255,255,255,.12);color:var(--text)}}
.empty{{padding:60px 40px;text-align:center;font-size:18px;color:var(--text-muted);font-weight:500}}
footer{{border-top:1px solid var(--border);padding:28px 40px;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}}
.footer-logo{{font-family:'Playfair Display',serif;font-size:16px;font-weight:700;color:var(--text-dim)}}
.footer-links{{display:flex;gap:16px}}
.footer-links a{{color:var(--text-muted);text-decoration:none;font-size:12px;font-weight:500;transition:color .2s}}
.footer-links a:hover{{color:var(--text)}}
.footer-copy{{font-size:11px;color:var(--text-muted)}}
.updated{{font-size:11px;color:var(--text-muted)}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(18px)}}to{{opacity:1;transform:translateY(0)}}}}
@media(max-width:640px){{
  :root{{--cw:200px;--ch:113px;--gap:10px}}
  nav{{padding:0 18px;height:54px}}.nav-links{{display:none}}
  .hero{{height:75vw;min-height:320px}}.hero-body{{padding:0 18px 44px}}
  .controls{{padding:20px 18px 0;gap:8px}}.row{{padding:4px 18px 10px}}
  .sec-hdr,.city-hdr,.sep,.grid{{padding-left:18px;padding-right:18px}}
  .hero-title{{font-size:24px}}.hero-btns{{flex-direction:column;gap:8px}}
  .modal-bg{{padding:0;align-items:flex-end}}.modal{{border-radius:12px 12px 0 0;max-height:95vh;overflow-y:auto}}
  .modal-body{{flex-direction:column}}.modal-vk{{align-self:stretch;justify-content:center}}
  footer{{flex-direction:column;align-items:flex-start;padding:20px 18px;gap:10px}}
  .search-input{{width:160px}}
}}
</style>
</head>
<body>
<nav id="nav">
  <a class="logo" href="#"><span class="logo-dot"></span>ДВИЖ КИНО</a>
  <ul class="nav-links">
    <li><a href="#" onclick="resetFilters();return false">Все фильмы</a></li>
    <li><a href="#s-new">Новинки</a></li>
    <li><a href="#s-cities">По городам</a></li>
  </ul>
  <div class="nav-right"><span class="nav-count" id="navCount"></span></div>
</nav>
<section class="hero" id="hero">
  <div class="hero-img" id="heroBg"></div>
  <div class="hero-grad"></div>
  <div class="hero-body" id="heroBody"></div>
</section>
<div class="controls">
  <div class="search-wrap">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
    <input class="search-input" id="searchInput" type="text" placeholder="Поиск...">
  </div>
  <div class="divider"></div>
  <span class="flabel">Город</span>
  <button class="fbtn active" data-city="all">Все</button>
  <button class="fbtn tula" data-city="Тула">Тула</button>
  <button class="fbtn kolomna" data-city="Коломна">Коломна</button>
  <button class="fbtn stupino" data-city="Ступино">Ступино</button>
  <button class="fbtn kaluga" data-city="Калуга">Калуга</button>
</div>
<div class="sections" id="sections"></div>
<div class="modal-bg" id="modalBg">
  <div class="modal">
    <button class="modal-close" id="modalClose">✕</button>
    <div class="modal-video" id="modalVideo"></div>
    <div class="modal-body">
      <div class="modal-info">
        <div class="modal-title" id="mTitle"></div>
        <div class="modal-meta" id="mMeta"></div>
      </div>
      <a class="modal-vk" id="mVk" href="#" target="_blank" rel="noopener">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M15.07 2H8.93C3.33 2 2 3.33 2 8.93v6.14C2 20.67 3.33 22 8.93 22h6.14C20.67 22 22 20.67 22 15.07V8.93C22 3.33 20.67 2 15.07 2zm3.08 13.57h-1.6c-.6 0-.78-.48-1.86-1.57-1-.94-1.39-1.07-1.63-1.07-.33 0-.42.1-.42.57v1.43c0 .41-.13.65-1.2.65-1.76 0-3.71-1.07-5.09-3.07C4.67 10.23 4.23 8.55 4.23 8.17c0-.24.1-.46.57-.46h1.6c.43 0 .59.2.75.65.82 2.39 2.2 4.49 2.77 4.49.21 0 .31-.1.31-.63V9.82c-.07-1.13-.67-1.22-.67-1.63 0-.21.17-.43.46-.43h2.52c.36 0 .49.2.49.62v3.37c0 .37.17.5.27.5.21 0 .39-.13.78-.52 1.21-1.35 2.07-3.43 2.07-3.43.12-.24.31-.46.74-.46h1.6c.48 0 .59.24.48.57-.2.93-2.13 3.65-2.13 3.65-.17.27-.23.39 0 .69.17.23.73.7 1.1 1.13.68.78 1.2 1.43 1.34 1.88.13.43-.1.65-.54.65z"/></svg>
        Открыть в ВК
      </a>
    </div>
  </div>
</div>
<footer>
  <div class="footer-logo">ДВИЖ КИНО</div>
  <div class="footer-links">
    <a href="https://vk.com/dvizh_kino" target="_blank">ВКонтакте</a>
    <a href="https://t.me/dvizhfilm" target="_blank">Telegram</a>
    <a href="https://rutube.ru/channel/27037876" target="_blank">Рутуб</a>
  </div>
  <div class="footer-copy">Тула · Коломна · Ступино · Калуга · 2022–2026</div>
  <div class="updated">Обновлено: {updated_at} · {total} фильмов</div>
</footer>
<script>
{films_js}
const CITIES=['Тула','Коломна','Ступино','Калуга'];
const CC={{Тула:'tula',Коломна:'kolomna',Ступино:'stupino',Калуга:'kaluga'}};
const GRADS={{Тула:'linear-gradient(135deg,#2a1005,#5c3010)',Коломна:'linear-gradient(135deg,#05101e,#0e2840)',Ступино:'linear-gradient(135deg,#05130a,#0a2e16)',Калуга:'linear-gradient(135deg,#10051e,#261048)','':'linear-gradient(135deg,#111118,#1a1a22)'}};
let activeCity='all',searchQ='';
const cc=c=>CC[c]||'x';
const fmt=n=>n>=1000?(n/1000).toFixed(1)+'K':String(n);
const vkLink=id=>`https://vk.com/video-24961777_${{id}}`;
const imgObs=new IntersectionObserver(entries=>{{entries.forEach(e=>{{if(e.isIntersecting){{const img=e.target;if(img.dataset.src){{img.src=img.dataset.src;img.onload=()=>img.classList.add('on');img.onerror=()=>img.style.display='none';imgObs.unobserve(img)}}}}}})}},{{rootMargin:'200px'}});
function lazyImg(src){{const img=document.createElement('img');img.className='card-img';img.alt='';img.referrerPolicy='no-referrer';if(src){{img.dataset.src=src;imgObs.observe(img)}};return img}}
function makeCard(f){{const ccc=cc(f.city);const card=document.createElement('div');card.className='card';const wrap=document.createElement('div');wrap.className='card-thumb-wrap';wrap.style.background=GRADS[f.city]||GRADS[''];if(f.thumb)wrap.appendChild(lazyImg(f.thumb));wrap.insertAdjacentHTML('beforeend',`<div class="card-play"><div class="card-play-btn"><svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg></div></div><div class="card-dur">${{f.dur}}</div>${{f.isNew?'<div class="card-new-badge">Новинка</div>':f.isFeatured?'<div class="card-hot-badge">★ Топ</div>':''}}`);const info=document.createElement('div');info.className='card-info';info.innerHTML=`<div class="card-title">${{f.title}}</div><div class="card-foot"><span class="card-city-pill ${{ccc}}">${{f.city||'Разное'}}</span><span class="card-views">${{fmt(f.views)}} просм.</span></div>`;card.appendChild(wrap);card.appendChild(info);card.addEventListener('click',()=>openModal(f));return card}}
function makeRow(films){{const r=document.createElement('div');r.className='row';films.forEach(f=>r.appendChild(makeCard(f)));return r}}
function openModal(f){{const ccc=cc(f.city);document.getElementById('mTitle').textContent=f.title;document.getElementById('mMeta').innerHTML=`${{f.city?`<span class="m-pill ${{ccc}}">${{f.city}}</span>`:''}} <span class="m-info">${{f.year}}</span><span class="m-info">·</span><span class="m-info">${{f.dur}}</span><span class="m-info">·</span><span class="m-info">${{fmt(f.views)}} просм.</span>`;document.getElementById('mVk').href=vkLink(f.id);document.getElementById('modalVideo').innerHTML=`<iframe src="${{f.player}}" allow="autoplay;encrypted-media;fullscreen;picture-in-picture" allowfullscreen></iframe>`;document.getElementById('modalBg').classList.add('open');document.body.style.overflow='hidden'}}
function closeModal(){{document.getElementById('modalBg').classList.remove('open');setTimeout(()=>document.getElementById('modalVideo').innerHTML='',300);document.body.style.overflow=''}}
document.getElementById('modalClose').addEventListener('click',closeModal);
document.getElementById('modalBg').addEventListener('click',e=>{{if(e.target===e.currentTarget)closeModal()}});
document.addEventListener('keydown',e=>{{if(e.key==='Escape')closeModal()}});
function buildHero(){{const pool=FILMS.filter(f=>f.isFeatured&&f.views>=800&&f.thumb&&f.thumb.includes('userapi'));const f=pool[Math.floor(Math.random()*pool.length)]||FILMS[0];const ccc=cc(f.city);const bg=document.getElementById('heroBg');const img=new Image();img.onload=()=>{{bg.style.backgroundImage=`url(${{f.thumb}})`;bg.classList.add('loaded')}};img.referrerPolicy='no-referrer';img.src=f.thumb;document.getElementById('heroBody').innerHTML=`<div class="hero-tags"><div class="hero-tag-live">ДВИЖ КИНО</div>${{f.city?`<span class="hero-city-pill ${{ccc}}">${{f.city}}</span>`:''}}</div><h1 class="hero-title">${{f.title}}</h1><div class="hero-meta"><span>${{f.year}}</span><span class="hero-sep"></span><span>${{f.dur}}</span><span class="hero-sep"></span><span class="hero-views"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>${{fmt(f.views)}}</span></div><div class="hero-btns"><button class="btn-watch" id="heroBtnPlay"><svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>Смотреть</button><button class="btn-more" onclick="document.getElementById('sections').scrollIntoView({{behavior:'smooth'}})">Все фильмы</button></div>`;document.getElementById('heroBtnPlay').addEventListener('click',()=>openModal(f))}}
function sep(){{return Object.assign(document.createElement('div'),{{className:'sep'}})}}
function buildSections(){{const c=document.getElementById('sections');c.innerHTML='';const fil=FILMS.filter(f=>(activeCity==='all'||f.city===activeCity)&&(!searchQ||f.title.toLowerCase().includes(searchQ)));document.getElementById('navCount').textContent=activeCity==='all'&&!searchQ?`${{FILMS.length}} фильмов`:`${{fil.length}} фильмов`;if(!fil.length){{c.innerHTML='<div class="empty">Ничего не найдено</div>';return}}if(activeCity!=='all'||searchQ){{const s=document.createElement('div');s.className='sec';s.innerHTML=`<div class="sec-hdr"><div class="sec-title">${{activeCity!=='all'?activeCity:'Результаты'}}</div><span class="sec-count">${{fil.length}} фильмов</span></div>`;const g=document.createElement('div');g.className='grid';fil.forEach(f=>g.appendChild(makeCard(f)));s.appendChild(g);c.appendChild(s);return}}const novie=FILMS.filter(f=>f.isNew);if(novie.length){{const s=document.createElement('section');s.id='s-new';s.className='sec';s.innerHTML=`<div class="sec-hdr"><div class="sec-title">Новинки</div><span class="sec-count">${{novie.length}}</span></div>`;s.appendChild(makeRow(novie));c.appendChild(s);c.appendChild(sep())}}const pop=[...FILMS].sort((a,b)=>b.views-a.views).slice(0,12);{{const s=document.createElement('section');s.className='sec';s.innerHTML=`<div class="sec-hdr"><div class="sec-title">Самое популярное</div><span class="sec-count">топ 12</span></div>`;s.appendChild(makeRow(pop));c.appendChild(s);c.appendChild(sep())}}const cw=document.createElement('div');cw.id='s-cities';CITIES.forEach(city=>{{const films=FILMS.filter(f=>f.city===city);if(!films.length)return;const cs=document.createElement('div');cs.className='city-sec';const ch=document.createElement('div');ch.className='city-hdr';ch.innerHTML=`<div class="city-name ${{CC[city]}}">${{city}}</div><div class="city-rule"></div><div class="city-pill">${{films.length}} фильмов</div>`;cs.appendChild(ch);cs.appendChild(makeRow(films));cw.appendChild(cs)}});const uncat=FILMS.filter(f=>!f.city);if(uncat.length){{const cs=document.createElement('div');cs.className='city-sec';const ch=document.createElement('div');ch.className='city-hdr';ch.innerHTML=`<div class="city-name" style="color:var(--text-muted)">Разное</div><div class="city-rule"></div><div class="city-pill">${{uncat.length}} видео</div>`;cs.appendChild(ch);cs.appendChild(makeRow(uncat));cw.appendChild(cs)}}c.appendChild(cw)}}
document.querySelector('.controls').addEventListener('click',e=>{{const btn=e.target.closest('[data-city]');if(!btn)return;activeCity=btn.dataset.city;document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');buildSections()}});
let dt;document.getElementById('searchInput').addEventListener('input',e=>{{clearTimeout(dt);dt=setTimeout(()=>{{searchQ=e.target.value.trim().toLowerCase();buildSections()}},200)}});
function resetFilters(){{activeCity='all';searchQ='';document.getElementById('searchInput').value='';document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('active'));document.querySelector('[data-city="all"]').classList.add('active');buildSections()}}
window.addEventListener('scroll',()=>{{document.getElementById('nav').classList.toggle('solid',window.scrollY>40)}},{{passive:true}});
buildHero();buildSections();
</script>
</body>
</html>"""

def main():
    if not VK_TOKEN:
        raise ValueError("Не задан VK_TOKEN! Добавь токен в GitHub Secrets.")

    print("Загружаю видео из ВКонтакте...")
    raw = fetch_videos()
    print(f"Всего видео: {len(raw)}")

    films = process_videos(raw)
    films_js = to_js(films)

    updated_at = datetime.now().strftime("%d.%m.%Y %H:%M")
    html = build_html(films_js, len(films), updated_at)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Готово! Сохранено в {OUTPUT_FILE} ({len(films)} фильмов)")

if __name__ == "__main__":
    main()
