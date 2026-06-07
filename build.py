"""
ДВИЖ КИНО — автосборка сайта
Уменьшен hero-блок на десктопе, убраны лишние надписи, отключено размытие.
"""
import os, re, requests
from datetime import datetime

VK_TOKEN   = os.environ.get("VK_TOKEN", "")
GROUP_ID   = 24961777
VK_VER     = "5.131"
OUT        = "index.html"
CITIES     = ["Тула", "Коломна", "Ступино", "Калуга"]

LOGO_URL = "logo.png"   # Укажите путь к логотипу (например "logo.png")
RUBRIC_PHRASE = "А вы знали?"

def fetch_videos():
    videos, offset = [], 0
    while True:
        r = requests.get("https://api.vk.com/method/video.get", params={
            "owner_id": f"-{GROUP_ID}", "count": 100, "offset": offset,
            "access_token": VK_TOKEN, "v": VK_VER,
        }, timeout=30)
        d = r.json()
        if "error" in d:
            raise RuntimeError("VK API: " + str(d["error"].get("error_msg", d["error"])))
        items = d["response"]["items"]
        videos.extend(items)
        print(f"  Загружено: {len(videos)}")
        if len(items) < 100:
            break
        offset += 100
    return videos

def extract_city(t):
    m = re.search(r"\((Тула|Коломна|Ступино|Калуга)\)", t)
    return m.group(1) if m else ""

def clean_title(t):
    t = re.sub(r"^Киножурнал\b.{0,15}?(ДВИЖ|Движ).{0,4}?\s*[-\u2014]\s*", "", t, flags=re.I)
    t = re.sub(r"^Движ\s*[-\u2014]\s*", "", t, flags=re.I)
    for c in CITIES:
        t = re.sub(r"\s*\(" + c + r"\)\s*$", "", t)
    if "Новости Коломны от 28 мая" in t:
        t = "Новости: съёмки нового сезона"
    return t.strip()

def best_thumb(imgs):
    vk = [i for i in imgs if "userapi.com" in i.get("url","")]
    pool = sorted(vk or imgs, key=lambda x: x.get("width", 0))
    for i in pool:
        if i.get("width", 0) >= 800:
            return i["url"]
    return pool[-1]["url"] if pool else ""

def process(raw):
    out = []
    for v in raw:
        raw_title = v.get("title", "")
        rubric = "aznali" if RUBRIC_PHRASE.lower() in raw_title.lower() else ""
        city = extract_city(raw_title) if not rubric else ""
        title = clean_title(raw_title)
        dur   = v.get("duration", 0)
        year  = datetime.fromtimestamp(v.get("date", 0)).year
        views = v.get("views", v.get("local_views", 0))
        out.append({
            "id":    v["id"],
            "title": title,
            "city":  city,
            "rubric": rubric,
            "year":  year,
            "views": views,
            "dur":   f"{dur//60}:{dur%60:02d}",
            "player": v.get("player","").replace("&amp;","&"),
            "thumb": best_thumb(v.get("image",[])),
            "isNew": year >= 2026,
            "isFeat": views >= 800,
        })
    return out

def esc_js(s):
    return (s.replace("\\","\\\\")
             .replace('"', '\\"')
             .replace("\r","")
             .replace("\n","\\n")
             .replace("\t"," "))

def to_js(films):
    rows = ["const FILMS=["]
    for f in films:
        rows.append(
            "{id:" + str(f["id"]) +
            ',title:"' + esc_js(f["title"]) + '"' +
            ',city:"'  + f["city"] + '"' +
            ',rubric:"' + f["rubric"] + '"' +
            ',year:'   + str(f["year"]) +
            ',views:'  + str(f["views"]) +
            ',dur:"'   + f["dur"] + '"' +
            ',player:"'+ esc_js(f["player"]) + '"' +
            ',thumb:"' + esc_js(f["thumb"]) + '"' +
            ',isNew:'  + ("true" if f["isNew"] else "false") +
            ',isFeat:' + ("true" if f["isFeat"] else "false") + "},"
        )
    rows.append("];")
    return "\n".join(rows)

# ── HTML TEMPLATE (CSS + JS) ─────────────────────────────────────────────────
CSS = """
:root{--bg:#0c0c10;--sf:#14141a;--sf2:#1e1e26;--bd:rgba(255,255,255,.07);
  --red:#e84545;--text:#f2f0ed;--dim:#8e8c88;--muted:#3e3c3a;
  --tula:#f0873c;--kolomna:#3da8e0;--stupino:#44c97a;--kaluga:#a67ee8;
  --aznali:#e8b35e;
  --cw:280px;--ch:158px;--gap:12px;--r:8px}
*{margin:0;padding:0;box-sizing:border-box}html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:Inter,sans-serif;overflow-x:hidden;min-height:100vh;-webkit-font-smoothing:antialiased}
nav{position:fixed;top:0;left:0;right:0;z-index:200;height:76px;padding:0 48px;display:flex;align-items:center;justify-content:space-between;transition:background .3s}
nav.solid{background:rgba(12,12,16,.96);backdrop-filter:blur(20px);border-bottom:1px solid var(--bd)}
.logo{font-family:Playfair Display,serif;font-size:39px;font-weight:700;color:var(--text);text-decoration:none;display:flex;align-items:center;gap:8px}
.logo img{height:66px;width:auto;display:block}
.dot{width:8px;height:8px;background:var(--red);border-radius:50%}
.nav-links{display:flex;gap:28px;list-style:none}
.nav-links a{color:var(--dim);text-decoration:none;font-size:13px;font-weight:500;transition:color .2s}
.nav-links a:hover{color:var(--text)}
.nav-count{font-size:12px;color:var(--muted)}
.hero{position:relative;height:60vh;min-height:480px;display:flex;align-items:flex-end;overflow:hidden}
.hero-img{position:absolute;inset:0;background-size:cover;background-position:center;transition:transform 0s ease}
.hero-img.on{transform:none}
.hero-grad{position:absolute;inset:0;background:linear-gradient(to right,rgba(12,12,16,.98) 0%,rgba(12,12,16,.6) 45%,rgba(12,12,16,.1) 80%),linear-gradient(to top,rgba(12,12,16,1) 0%,rgba(12,12,16,.5) 30%,transparent 65%)}
.hero-body{position:relative;z-index:2;padding:0 40px 64px;max-width:560px;animation:fadeUp .8s ease both}
.hero-tags{display:flex;align-items:center;gap:8px;margin-bottom:16px}
.live{display:flex;align-items:center;gap:6px;background:rgba(232,69,69,.15);border:1px solid rgba(232,69,69,.3);color:var(--red);font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;padding:4px 10px;border-radius:20px}
.live::before{content:'';width:6px;height:6px;background:var(--red);border-radius:50%;animation:pulse 2s ease infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.7)}}
.cpill{font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;padding:4px 10px;border-radius:20px}
.cpill.tula{background:rgba(240,135,60,.12);color:var(--tula)}.cpill.kolomna{background:rgba(61,168,224,.12);color:var(--kolomna)}.cpill.stupino{background:rgba(68,201,122,.12);color:var(--stupino)}.cpill.kaluga{background:rgba(166,126,232,.12);color:var(--kaluga)}.cpill.aznali{background:rgba(232,179,94,.15);color:var(--aznali)}
.hero-title{font-family:Playfair Display,serif;font-size:clamp(30px,5vw,56px);font-weight:700;line-height:1.08;margin-bottom:14px}
.hero-meta{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--dim);margin-bottom:28px}
.hero-sep{width:3px;height:3px;background:var(--muted);border-radius:50%}
.hero-btns{display:flex;gap:10px}
.btn-w{display:inline-flex;align-items:center;gap:8px;background:var(--text);color:#0c0c10;padding:12px 24px;border-radius:6px;font-size:14px;font-weight:700;border:none;cursor:pointer;transition:all .18s}
.btn-w:hover{background:#e0ddd8;transform:translateY(-1px)}
.btn-a{display:inline-flex;align-items:center;gap:8px;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.14);color:var(--text);padding:12px 20px;border-radius:6px;font-size:14px;font-weight:600;cursor:pointer;transition:all .18s}
.btn-a:hover{background:rgba(255,255,255,.16);transform:translateY(-1px)}
.controls{padding:28px 40px 0;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.sw{position:relative}
.sw svg{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--muted)}
.si{background:var(--sf2);border:1px solid var(--bd);color:var(--text);font-family:Inter,sans-serif;font-size:13px;padding:9px 14px 9px 36px;width:230px;border-radius:6px;outline:none;transition:border-color .2s}
.si::placeholder{color:var(--muted)}.si:focus{border-color:rgba(255,255,255,.2)}
.dv{width:1px;height:22px;background:var(--bd);margin:0 2px}
.fl{font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.fb{padding:7px 14px;background:transparent;border:1px solid var(--bd);color:var(--dim);font-family:Inter,sans-serif;font-size:12px;font-weight:600;cursor:pointer;border-radius:20px;transition:all .18s}
.fb:hover{border-color:rgba(255,255,255,.2);color:var(--text)}
.fb.active{background:var(--text);color:#0c0c10;border-color:var(--text)}
.fb.tula.active{background:var(--tula);color:#0c0c10;border-color:var(--tula)}
.fb.kolomna.active{background:var(--kolomna);color:#0c0c10;border-color:var(--kolomna)}
.fb.stupino.active{background:var(--stupino);color:#0c0c10;border-color:var(--stupino)}
.fb.kaluga.active{background:var(--kaluga);color:#0c0c10;border-color:var(--kaluga)}
.sections{padding:28px 0 80px}
.sec{margin-bottom:36px}
.sh{padding:0 40px;display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.st{font-size:17px;font-weight:700;letter-spacing:-.01em}.sc{font-size:12px;color:var(--muted)}
.sep{height:1px;margin:0 40px 28px;background:var(--bd)}
.cs{margin-bottom:36px}
.ch{padding:0 40px;display:flex;align-items:center;gap:12px;margin-bottom:14px}
.cn{font-size:17px;font-weight:700;letter-spacing:-.01em}
.cn.tula{color:var(--tula)}.cn.kolomna{color:var(--kolomna)}.cn.stupino{color:var(--stupino)}.cn.kaluga{color:var(--kaluga)}.cn.aznali{color:var(--aznali)}
.cr{flex:1;height:1px;background:var(--bd)}
.cb{font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);background:var(--sf2);padding:3px 8px;border-radius:10px}
.row{display:flex;gap:var(--gap);overflow-x:auto;padding:4px 40px 12px;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;scrollbar-width:none}
.row::-webkit-scrollbar{display:none}
.card{flex:0 0 var(--cw);width:var(--cw);cursor:pointer;scroll-snap-align:start;transition:transform .22s}
.card:hover{transform:scale(1.03)}
.ct{width:100%;height:var(--ch);border-radius:var(--r);overflow:hidden;position:relative;background:var(--sf2);margin-bottom:10px}
.ci{width:100%;height:100%;object-fit:cover;opacity:0;transition:opacity .4s;display:block}
.ci.on{opacity:1}
.cp{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity .2s;z-index:2}
.card:hover .cp{opacity:1}
.cpb{width:44px;height:44px;background:rgba(255,255,255,.92);border-radius:50%;display:flex;align-items:center;justify-content:center}
.cpb svg{fill:#0c0c10;width:18px;height:18px;margin-left:2px}
.cd{position:absolute;bottom:8px;right:8px;font-size:10px;font-weight:600;color:#fff;background:rgba(0,0,0,.72);padding:2px 6px;border-radius:4px;z-index:2}
.cn2{position:absolute;top:8px;right:8px;background:var(--red);color:#fff;font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;padding:2px 7px;border-radius:4px;z-index:2}
.ch2{position:absolute;top:8px;right:8px;background:rgba(232,188,106,.88);color:#0c0c10;font-size:9px;font-weight:700;padding:2px 7px;border-radius:4px;z-index:2}
.ci2{padding:0 2px}
.tl{font-size:13px;font-weight:600;line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;margin-bottom:5px;letter-spacing:-.01em}
.cf{display:flex;align-items:center;gap:6px}
.cc{font-size:10px;font-weight:600;padding:2px 8px;border-radius:10px}
.cc.tula{background:rgba(240,135,60,.12);color:var(--tula)}.cc.kolomna{background:rgba(61,168,224,.12);color:var(--kolomna)}.cc.stupino{background:rgba(68,201,122,.12);color:var(--stupino)}.cc.kaluga{background:rgba(166,126,232,.12);color:var(--kaluga)}.cc.aznali{background:rgba(232,179,94,.15);color:var(--aznali)}.cc.x{background:rgba(255,255,255,.05);color:var(--muted)}
.cv{font-size:11px;color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--cw),1fr));gap:18px var(--gap);padding:0 40px}
.grid .card{flex:none;width:100%}
.mb{position:fixed;inset:0;z-index:500;background:rgba(0,0,0,.88);backdrop-filter:blur(16px);display:flex;align-items:center;justify-content:center;opacity:0;pointer-events:none;transition:opacity .25s;padding:16px}
.mb.open{opacity:1;pointer-events:all}
.md{width:100%;max-width:900px;background:var(--sf);border-radius:12px;overflow:hidden;position:relative;transform:scale(.95) translateY(14px);transition:transform .25s;box-shadow:0 32px 80px rgba(0,0,0,.8)}
.mb.open .md{transform:scale(1) translateY(0)}
.mv{width:100%;aspect-ratio:16/9;background:#000}
.mv iframe{width:100%;height:100%;border:none;display:block}
.mc{position:absolute;top:12px;right:12px;z-index:10;width:32px;height:32px;background:rgba(0,0,0,.6);border:1px solid rgba(255,255,255,.12);border-radius:50%;color:var(--dim);font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .18s}
.mc:hover{background:rgba(255,255,255,.12);color:var(--text)}
.mby{padding:18px 22px 20px;display:flex;justify-content:space-between;align-items:flex-start;gap:16px}
.mi{flex:1;min-width:0}
.mt{font-size:18px;font-weight:700;margin-bottom:8px;letter-spacing:-.01em}
.mm{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.mp{font-size:11px;font-weight:600;padding:3px 9px;border-radius:10px}
.mp.tula{background:rgba(240,135,60,.12);color:var(--tula)}.mp.kolomna{background:rgba(61,168,224,.12);color:var(--kolomna)}.mp.stupino{background:rgba(68,201,122,.12);color:var(--stupino)}.mp.kaluga{background:rgba(166,126,232,.12);color:var(--kaluga)}.mp.aznali{background:rgba(232,179,94,.15);color:var(--aznali)}
.minfo{font-size:12px;color:var(--muted)}
.mvk{display:inline-flex;align-items:center;gap:7px;background:rgba(255,255,255,.07);border:1px solid var(--bd);color:var(--dim);text-decoration:none;font-size:12px;font-weight:600;padding:9px 16px;border-radius:6px;white-space:nowrap;flex-shrink:0;transition:all .18s}
.mvk:hover{background:rgba(255,255,255,.12);color:var(--text)}
.empty{padding:60px 40px;text-align:center;font-size:18px;color:var(--muted)}
footer{border-top:1px solid var(--bd);padding:24px 40px;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}
.fl2{font-family:Playfair Display,serif;font-size:16px;font-weight:700;color:var(--dim);display:flex;align-items:center;gap:8px}
.fl2 img{height:28px;width:auto}
.flinks{display:flex;gap:16px}
.flinks a{color:var(--muted);text-decoration:none;font-size:12px;font-weight:500;transition:color .2s}
.flinks a:hover{color:var(--text)}
.fupd{font-size:11px;color:var(--muted)}
@keyframes fadeUp{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:translateY(0)}}
@media(max-width:640px){
  :root{--cw:200px;--ch:113px;--gap:10px}
  nav{padding:0 20px;height:64px}
  .logo{font-size:33px}
  .logo img{height:54px}
  .nav-links{display:none}
  .hero{height:70vw;min-height:300px}.hero-body{padding:0 18px 40px}
  .hero-title{font-size:22px}.hero-btns{flex-direction:column;gap:8px}
  .controls{padding:16px 16px 0;gap:8px}.row{padding:4px 16px 10px}
  .sh,.ch,.sep,.grid{padding-left:16px;padding-right:16px}
  .grid{grid-template-columns:1fr;gap:16px}
  .grid .card{width:100%}
  .grid .card .ct{height:auto;aspect-ratio:16/9}
  .mb{padding:0;align-items:flex-end}.md{border-radius:12px 12px 0 0;max-height:92vh;overflow-y:auto}
  .mby{flex-direction:column}.mvk{align-self:stretch;justify-content:center}
  footer{flex-direction:column;padding:20px 16px;gap:8px}.si{width:160px}
}
"""

JS = r"""
const CITIES=["Тула","Коломна","Ступино","Калуга"];
const CC={"Тула":"tula","Коломна":"kolomna","Ступино":"stupino","Калуга":"kaluga","aznali":"aznali"};
const GR={
  "Тула":"linear-gradient(135deg,#2a1005,#5c3010)",
  "Коломна":"linear-gradient(135deg,#05101e,#0e2840)",
  "Ступино":"linear-gradient(135deg,#05130a,#0a2e16)",
  "Калуга":"linear-gradient(135deg,#10051e,#261048)",
  "aznali":"linear-gradient(135deg,#402d12,#6e4f1e)",
  "":"linear-gradient(135deg,#111118,#1a1a22)"
};
let activeCity="all", searchQ="";
const cc=c=>CC[c]||"x";
const fmt=n=>n>=1000?(n/1000).toFixed(1)+"K":String(n);
const vkLink=id=>"https://vk.com/video-24961777_"+id;

const obs=new IntersectionObserver(es=>{es.forEach(e=>{
  if(e.isIntersecting){
    const i=e.target;
    if(i.dataset.src){i.src=i.dataset.src;i.onload=()=>i.classList.add("on");i.onerror=()=>i.style.display="none";obs.unobserve(i)}
  }
})},{rootMargin:"200px"});

function li(src){
  const i=document.createElement("img");
  i.className="ci";i.alt="";i.referrerPolicy="no-referrer";
  if(src){i.dataset.src=src;obs.observe(i);}
  return i;
}

function makeCard(f){
  let rubricClass = "", rubricLabel = "";
  if(f.rubric === "aznali") {
    rubricClass = "aznali";
    rubricLabel = "А вы знали?";
  } else if(f.city) {
    rubricClass = cc(f.city);
    rubricLabel = f.city;
  } else {
    rubricClass = "x";
    rubricLabel = "Разное";
  }
  const card=document.createElement("div");card.className="card";
  const wrap=document.createElement("div");wrap.className="ct";
  wrap.style.background=GR[f.rubric === "aznali" ? "aznali" : (f.city || "")]||GR[""];
  if(f.thumb)wrap.appendChild(li(f.thumb));
  const playDiv=document.createElement("div");playDiv.className="cp";
  playDiv.innerHTML="<div class='cpb'><svg viewBox='0 0 24 24'><path d='M8 5v14l11-7z'/></svg></div>";
  wrap.appendChild(playDiv);
  const durDiv=document.createElement("div");durDiv.className="cd";durDiv.textContent=f.dur;
  wrap.appendChild(durDiv);
  if(f.isNew){const b=document.createElement("div");b.className="cn2";b.textContent="Новинка";wrap.appendChild(b);}
  else if(f.isFeat){const b=document.createElement("div");b.className="ch2";b.textContent="★ Топ";wrap.appendChild(b);}
  const info=document.createElement("div");info.className="ci2";
  const title=document.createElement("div");title.className="tl";title.textContent=f.title;
  const foot=document.createElement("div");foot.className="cf";
  const cpill=document.createElement("span");cpill.className="cc "+rubricClass;cpill.textContent=rubricLabel;
  const views=document.createElement("span");views.className="cv";views.textContent=fmt(f.views)+" просм.";
  foot.appendChild(cpill);foot.appendChild(views);
  info.appendChild(title);info.appendChild(foot);
  card.appendChild(wrap);card.appendChild(info);
  card.addEventListener("click",()=>openModal(f));
  return card;
}

function makeRow(films){
  const r=document.createElement("div");r.className="row";
  films.forEach(f=>r.appendChild(makeCard(f)));
  return r;
}

function openModal(f){
  let rubricClass = "", rubricLabel = "";
  if(f.rubric === "aznali") {
    rubricClass = "aznali";
    rubricLabel = "А вы знали?";
  } else if(f.city) {
    rubricClass = cc(f.city);
    rubricLabel = f.city;
  } else {
    rubricClass = "x";
    rubricLabel = "Разное";
  }
  document.getElementById("mt").textContent=f.title;
  const mm=document.getElementById("mm");
  mm.innerHTML="";
  if(rubricLabel !== "Разное"){const p=document.createElement("span");p.className="mp "+rubricClass;p.textContent=rubricLabel;mm.appendChild(p);}
  ["·",f.year,"·",f.dur,"·",fmt(f.views)+" просм."].forEach(t=>{const s=document.createElement("span");s.className="minfo";s.textContent=t;mm.appendChild(s);});
  document.getElementById("mvk2").href=vkLink(f.id);
  document.getElementById("mv").innerHTML='<iframe src="'+f.player+'" allow="autoplay;encrypted-media;fullscreen;picture-in-picture" allowfullscreen></iframe>';
  document.getElementById("mb").classList.add("open");
  document.body.style.overflow="hidden";
}
function closeModal(){
  document.getElementById("mb").classList.remove("open");
  setTimeout(()=>document.getElementById("mv").innerHTML="",300);
  document.body.style.overflow="";
}
document.getElementById("mc").addEventListener("click",closeModal);
document.getElementById("mb").addEventListener("click",e=>{if(e.target===e.currentTarget)closeModal();});
document.addEventListener("keydown",e=>{if(e.key==="Escape")closeModal();});

function buildHero(){
  const pool=FILMS.filter(f=>f.isFeat&&f.views>=800&&f.thumb&&f.thumb.includes("userapi"));
  const f=pool[Math.floor(Math.random()*pool.length)]||FILMS[0];
  if(!f)return;
  let rubricClass = "";
  if(f.rubric === "aznali") rubricClass = "aznali";
  else if(f.city) rubricClass = cc(f.city);
  const bg=document.getElementById("hbg");
  const img=new Image();img.referrerPolicy="no-referrer";
  img.onload=()=>{bg.style.backgroundImage="url("+f.thumb+")";bg.classList.add("on");};
  img.src=f.thumb;
  const tags=document.getElementById("htags");
  // Полностью очищаем блок с тегами — убираем и город, и "ДВИЖ КИНО"
  tags.innerHTML="";
  document.getElementById("htitle").textContent=f.title;
  document.getElementById("hmeta").innerHTML=
    "<span>"+f.year+"</span><span class='hero-sep'></span><span>"+f.dur+"</span><span class='hero-sep'></span><span>"+fmt(f.views)+" просм.</span>";
  document.getElementById("hplay").onclick=()=>openModal(f);
  document.getElementById("hall").onclick=()=>document.getElementById("sections").scrollIntoView({behavior:"smooth"});
}

function sep(){return Object.assign(document.createElement("div"),{className:"sep"});}

function buildSections(){
  const c=document.getElementById("sections");c.innerHTML="";
  const fil=FILMS.filter(f=>(activeCity==="all"||f.city===activeCity)&&(!searchQ||f.title.toLowerCase().includes(searchQ)));
  document.getElementById("nc").textContent=FILMS.length+" фильмов";
  if(!fil.length){c.innerHTML="<div class='empty'>Ничего не найдено</div>";return;}
  if(activeCity!=="all"||searchQ){
    const s=document.createElement("div");s.className="sec";
    const sh=document.createElement("div");sh.className="sh";
    sh.innerHTML="<div class='st'>"+(activeCity!=="all"?activeCity:"Результаты")+"</div><span class='sc'>"+fil.length+" фильмов</span>";
    const g=document.createElement("div");g.className="grid";
    fil.forEach(f=>g.appendChild(makeCard(f)));
    s.appendChild(sh);s.appendChild(g);c.appendChild(s);return;
  }
  // Новинки
  const novie=FILMS.filter(f=>f.isNew);
  if(novie.length){
    const s=document.createElement("section");s.id="s-new";s.className="sec";
    const sh=document.createElement("div");sh.className="sh";
    sh.innerHTML="<div class='st'>Новинки</div><span class='sc'>"+novie.length+"</span>";
    s.appendChild(sh);s.appendChild(makeRow(novie));c.appendChild(s);c.appendChild(sep());
  }
  // Самое популярное (топ 12)
  const pop=[...FILMS].sort((a,b)=>b.views-a.views).slice(0,12);
  {
    const s=document.createElement("section");s.className="sec";
    const sh=document.createElement("div");sh.className="sh";
    sh.innerHTML="<div class='st'>Самое популярное</div><span class='sc'>топ 12</span>";
    s.appendChild(sh);s.appendChild(makeRow(pop));c.appendChild(s);c.appendChild(sep());
  }
  // Рекомендуем (3 фильма с максимальными просмотрами среди вышедших в 2025+)
  const recYear = 2025;
  const recCandidates = FILMS.filter(f => f.year >= recYear).sort((a,b)=>b.views-a.views).slice(0,3);
  if(recCandidates.length){
    const s=document.createElement("section");s.className="sec";
    const sh=document.createElement("div");sh.className="sh";
    sh.innerHTML="<div class='st'>Рекомендуем</div><span class='sc'>выбор редакции</span>";
    s.appendChild(sh);s.appendChild(makeRow(recCandidates));c.appendChild(s);c.appendChild(sep());
  }
  // А вы знали?
  const aznaliFilms = FILMS.filter(f => f.rubric === "aznali");
  if(aznaliFilms.length){
    const s=document.createElement("section");s.className="sec";
    const sh=document.createElement("div");sh.className="sh";
    sh.innerHTML="<div class='st'>А вы знали?</div><span class='sc'>интересные факты</span>";
    s.appendChild(sh);s.appendChild(makeRow(aznaliFilms));c.appendChild(s);c.appendChild(sep());
  }
  // По городам
  const cw=document.createElement("div");cw.id="s-cities";
  CITIES.forEach(city=>{
    const films=FILMS.filter(f=>f.city===city);if(!films.length)return;
    const cs=document.createElement("div");cs.className="cs";
    const ch=document.createElement("div");ch.className="ch";
    const cn=document.createElement("div");cn.className="cn "+CC[city];cn.textContent=city;
    const cr=document.createElement("div");cr.className="cr";
    const cb=document.createElement("div");cb.className="cb";cb.textContent=films.length+" фильмов";
    ch.appendChild(cn);ch.appendChild(cr);ch.appendChild(cb);
    cs.appendChild(ch);cs.appendChild(makeRow(films));cw.appendChild(cs);
  });
  // Разное (только фильмы без города и без рубрики)
  const uncat=FILMS.filter(f=>!f.city && !f.rubric);
  if(uncat.length){
    const cs=document.createElement("div");cs.className="cs";
    const ch=document.createElement("div");ch.className="ch";
    ch.innerHTML="<div class='cn' style='color:var(--muted)'>Разное</div><div class='cr'></div><div class='cb'>"+uncat.length+" видео</div>";
    cs.appendChild(ch);cs.appendChild(makeRow(uncat));cw.appendChild(cs);
  }
  c.appendChild(cw);
}

document.querySelector(".controls").addEventListener("click",e=>{
  const btn=e.target.closest("[data-city]");if(!btn)return;
  activeCity=btn.dataset.city;
  document.querySelectorAll(".fb").forEach(b=>b.classList.remove("active"));
  btn.classList.add("active");buildSections();
});
let dt;
document.getElementById("si").addEventListener("input",e=>{
  clearTimeout(dt);dt=setTimeout(()=>{searchQ=e.target.value.trim().toLowerCase();buildSections();},200);
});
function resetFilters(){
  activeCity="all";searchQ="";document.getElementById("si").value="";
  document.querySelectorAll(".fb").forEach(b=>b.classList.remove("active"));
  document.querySelector("[data-city='all']").classList.add("active");buildSections();
}
window.addEventListener("scroll",()=>{
  document.getElementById("nav").classList.toggle("solid",window.scrollY>40);
},{passive:true});

buildHero();buildSections();
"""

def build_html(films_js, total, updated_at):
    if LOGO_URL:
        logo_html = f'<img src="{LOGO_URL}" alt="ДВИЖ КИНО">'
    else:
        logo_html = '<span class="dot"></span>ДВИЖ КИНО'
    nav_logo = f'<a class="logo" href="#">{logo_html}</a>'
    footer_logo = f'<div class="fl2">{logo_html if LOGO_URL else "ДВИЖ КИНО"}</div>'

    return (
        '<!DOCTYPE html>\n<html lang="ru">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>ДВИЖ КИНО</title>\n'
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700'
        '&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">\n'
        '<style>' + CSS + '</style>\n'
        '</head>\n<body>\n'
        '<nav id="nav">\n'
        f'  {nav_logo}\n'
        '  <ul class="nav-links">\n'
        '    <li><a href="#" onclick="resetFilters();return false">Все фильмы</a></li>\n'
        '    <li><a href="#s-new">Новинки</a></li>\n'
        '    <li><a href="#s-cities">По городам</a></li>\n'
        '  </ul>\n'
        '  <span class="nav-count" id="nc"></span>\n'
        '</nav>\n'
        '<section class="hero">\n'
        '  <div class="hero-img" id="hbg"></div>\n'
        '  <div class="hero-grad"></div>\n'
        '  <div class="hero-body">\n'
        '    <div class="hero-tags" id="htags"></div>\n'
        '    <h1 class="hero-title" id="htitle"></h1>\n'
        '    <div class="hero-meta" id="hmeta"></div>\n'
        '    <div class="hero-btns">\n'
        '      <button class="btn-w" id="hplay">'
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>'
        'Смотреть</button>\n'
        '      <button class="btn-a" id="hall">Все фильмы</button>\n'
        '    </div>\n'
        '  </div>\n'
        '</section>\n'
        '<div class="controls">\n'
        '  <div class="sw">\n'
        '    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">'
        '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>\n'
        '    <input class="si" id="si" type="text" placeholder="Поиск...">\n'
        '  </div>\n'
        '  <div class="dv"></div>\n'
        '  <span class="fl">Город</span>\n'
        '  <button class="fb active" data-city="all">Все</button>\n'
        '  <button class="fb tula" data-city="Тула">Тула</button>\n'
        '  <button class="fb kolomna" data-city="Коломна">Коломна</button>\n'
        '  <button class="fb stupino" data-city="Ступино">Ступино</button>\n'
        '  <button class="fb kaluga" data-city="Калуга">Калуга</button>\n'
        '</div>\n'
        '<div class="sections" id="sections"></div>\n'
        '<div class="mb" id="mb">\n'
        '  <div class="md">\n'
        '    <button class="mc" id="mc">&#x2715;</button>\n'
        '    <div class="mv" id="mv"></div>\n'
        '    <div class="mby">\n'
        '      <div class="mi"><div class="mt" id="mt"></div><div class="mm" id="mm"></div></div>\n'
        '      <a class="mvk" id="mvk2" href="#" target="_blank" rel="noopener">\n'
        '        <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">'
        '<path d="M15.07 2H8.93C3.33 2 2 3.33 2 8.93v6.14C2 20.67 3.33 22 8.93 22h6.14'
        'C20.67 22 22 20.67 22 15.07V8.93C22 3.33 20.67 2 15.07 2zm3.08 13.57h-1.6'
        'c-.6 0-.78-.48-1.86-1.57-1-.94-1.39-1.07-1.63-1.07-.33 0-.42.1-.42.57v1.43'
        'c0 .41-.13.65-1.2.65-1.76 0-3.71-1.07-5.09-3.07C4.67 10.23 4.23 8.55 4.23 8.17'
        'c0-.24.1-.46.57-.46h1.6c.43 0 .59.2.75.65.82 2.39 2.2 4.49 2.77 4.49.21 0 .31-.1'
        '.31-.63V9.82c-.07-1.13-.67-1.22-.67-1.63 0-.21.17-.43.46-.43h2.52c.36 0 .49.2'
        '.49.62v3.37c0 .37.17.5.27.5.21 0 .39-.13.78-.52 1.21-1.35 2.07-3.43 2.07-3.43'
        '.12-.24.31-.46.74-.46h1.6c.48 0 .59.24.48.57-.2.93-2.13 3.65-2.13 3.65-.17.27'
        '-.23.39 0 .69.17.23.73.7 1.1 1.13.68.78 1.2 1.43 1.34 1.88.13.43-.1.65-.54.65z"/>'
        '</svg> Открыть в ВК\n'
        '      </a>\n'
        '    </div>\n'
        '  </div>\n'
        '</div>\n'
        '<footer>\n'
        f'  {footer_logo}\n'
        '  <div class="flinks">\n'
        '    <a href="https://vk.com/dvizh_kino" target="_blank">ВКонтакте</a>\n'
        '    <a href="https://t.me/dvizhfilm" target="_blank">Telegram</a>\n'
        '    <a href="https://rutube.ru/channel/27037876" target="_blank">Рутуб</a>\n'
        '  </div>\n'
        '  <div class="fupd">Обновлено: ' + updated_at + ' &middot; ' + str(total) + ' фильмов</div>\n'
        '</footer>\n'
        '<script>\n' + films_js + '\n' + JS + '\n</script>\n'
        '</body>\n</html>'
    )

def main():
    if not VK_TOKEN:
        raise ValueError("VK_TOKEN не задан!")
    print("Загружаю видео из ВКонтакте...")
    raw = fetch_videos()
    print(f"Всего: {len(raw)}")
    films = process(raw)
    js = to_js(films)
    updated = datetime.now().strftime("%d.%m.%Y %H:%M")
    html = build_html(js, len(films), updated)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Готово: {OUT} ({len(films)} фильмов, {len(html):,} байт)")

if __name__ == "__main__":
    main()
