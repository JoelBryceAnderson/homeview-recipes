#!/usr/bin/env python3
"""Build a static recipe site from recipes/*.json (schema.org Recipe).

Each recipe becomes _site/<slug>/index.html with the JSON-LD embedded, so
Safari on Apple HomeView (and Paprika, Mela, Google, etc.) can parse it.
Standard library only. Usage: python3 build.py [--check]
"""
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "recipes"
IMAGES = ROOT / "images"
OUT = ROOT / "_site"


def site_url():
    """Absolute base URL, so JSON-LD image links work outside the page."""
    if os.environ.get("SITE_URL"):
        return os.environ["SITE_URL"].rstrip("/") + "/"
    repo = os.environ.get("GITHUB_REPOSITORY")  # set in GitHub Actions
    if repo:
        owner, name = repo.split("/")
        return f"https://{owner.lower()}.github.io/{name}/"
    return ""


def images_of(r):
    """Normalize schema.org image (str | list | ImageObject) to a list of str."""
    img = r.get("image")
    if not img:
        return []
    items = img if isinstance(img, list) else [img]
    return [i.get("url") if isinstance(i, dict) else i for i in items if i]


def is_local(path):
    return not re.match(r"^https?://", path)
REQUIRED = ["name", "recipeIngredient", "recipeInstructions"]
DURATION = re.compile(r"^P(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+S)?)?$")

CSS = """
:root{color-scheme:light dark;
--paper:#f2f2f7;--card:#ffffff;--ink:#1c1c1e;--muted:#6e6e73;--accent:#b0263b;--line:#e5e5ea;--tint:#f7e8ea;--shadow:0 1px 2px rgba(0,0,0,.05),0 4px 14px rgba(0,0,0,.05);
--display:-apple-system,"SF Pro Display",BlinkMacSystemFont,system-ui,sans-serif;--sans:-apple-system,BlinkMacSystemFont,system-ui,sans-serif}
@media (prefers-color-scheme:dark){:root{--paper:#000000;--card:#1c1c1e;--ink:#f5f5f7;--muted:#98989d;--accent:#ff6b7f;--line:#38383a;--tint:#2c1a1d;--shadow:none}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%;background:var(--paper)}
/* Sized for HomeView: a 7-inch square touch screen with rounded corners. Keep it dense. */
body{font:17px/1.45 var(--sans);color:var(--ink);background:var(--paper);max-width:760px;margin:0 auto;padding:16px 22px 48px}
a{color:var(--accent)}
h1,h2,h3{font-family:var(--display);font-weight:700;letter-spacing:-.015em;text-wrap:balance}
h1{font-size:1.75em;line-height:1.08;font-weight:800;letter-spacing:-.025em;margin:.1em 0 .2em}
h2{font-size:1.15em;margin:1.1em 0 .3em}
h3{font-size:1em;margin:1em 0 .1em;color:var(--accent)}
.kicker{font:700 .68em/1.2 var(--sans);text-transform:uppercase;letter-spacing:.14em;color:var(--accent);margin:0}
.back{display:inline-flex;align-items:center;gap:5px;min-height:44px;padding:0 16px 0 12px;border-radius:22px;background:var(--tint);color:var(--ink);font-weight:600;text-decoration:none}
.back::before{content:"‹";font-size:1.5em;line-height:0;color:var(--accent);margin-top:-3px}
/* typographic cover for recipes without a photo */
.ph{display:flex!important;flex-direction:column;justify-content:space-between;padding:9%;color:#fff;text-align:left;background:radial-gradient(circle at 15% 0%,rgba(255,255,255,.2),transparent 55%),linear-gradient(160deg,var(--c2),var(--c1))}
.ph i{font:700 calc(var(--s)*.042)/1.2 var(--sans);font-style:normal;text-transform:uppercase;letter-spacing:.16em;opacity:.78}
.ph b{font:800 calc(var(--s)*.105)/1.02 var(--display);letter-spacing:-.025em;text-wrap:balance;display:-webkit-box;-webkit-line-clamp:5;-webkit-box-orient:vertical;overflow:hidden}
/* recipe page */
.top{display:flex;align-items:center;justify-content:space-between;gap:12px}
.head{display:grid;grid-template-columns:1fr auto;gap:18px;align-items:start;margin:12px 0 0}
.head .desc{margin:.25em 0 0;color:var(--muted);font-size:.9em}
.photo{width:clamp(96px,24vw,156px);aspect-ratio:1;border-radius:14px;object-fit:cover;box-shadow:var(--shadow);display:block}
.facts{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(0,1fr);margin:12px 0 0;padding:10px 0 0;border-top:1px solid var(--line)}
.facts div{padding:0 12px}
.facts div:first-child{padding-left:0}
.facts div+div{border-left:1px solid var(--line)}
.facts dt{font:700 .6em/1.4 var(--sans);text-transform:uppercase;letter-spacing:.14em;color:var(--muted)}
.facts dd{margin:0;font:600 .95em/1.25 var(--display)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);padding:2px 16px 4px;margin:14px 0}
.card h2{margin:.55em 0 .1em;font-size:1em;color:var(--accent)}
.ing{list-style:none;padding:0;margin:0;columns:2 170px;column-gap:28px}
.ing li{padding:6px 0;border-top:1px solid var(--line);break-inside:avoid;font-size:.95em}
.steps{list-style:none;padding:0;margin:0;counter-reset:step}
.steps li{position:relative;counter-increment:step;padding:9px 0 10px 42px;border-bottom:1px solid var(--line)}
.steps li:last-child{border:0}
.steps li::before{content:counter(step);position:absolute;left:0;top:9px;width:28px;height:28px;border-radius:50%;background:var(--accent);color:#fff;display:grid;place-items:center;font:700 .8em/1 var(--display);font-variant-numeric:tabular-nums}
.steps strong{font-family:var(--display);font-weight:650}
.tip{background:var(--tint);border-radius:12px;padding:10px 14px;margin:10px 0;font-size:.92em}
.tip b{display:block;font:700 .66em/1.6 var(--sans);text-transform:uppercase;letter-spacing:.14em;color:var(--accent)}
.source{font-size:.78em;color:var(--muted);overflow-wrap:anywhere}
.mini{position:fixed;top:0;left:0;right:0;z-index:5;background:color-mix(in srgb,var(--paper) 88%,transparent);-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);border-bottom:1px solid var(--line);transform:translateY(-110%);transition:transform .22s ease;visibility:hidden}
.mini.show{transform:none;visibility:visible}
.mini div{max-width:760px;margin:0 auto;padding:8px 22px;display:flex;align-items:center;gap:12px}
.mini .back{flex:none}
.mini .thumb{flex:none;width:40px;height:40px;border-radius:9px;object-fit:cover;overflow:hidden}
.mini b{font:700 1em/1.2 var(--display);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
/* index: cover flow */
body.idx{max-width:none;height:100vh;height:100dvh;overflow:hidden;padding:14px 0 12px;display:flex;flex-direction:column}
.masthead{display:flex;align-items:baseline;gap:10px;padding:0 22px}
.masthead h1{font-size:1.6em;margin:0}
.masthead p{margin:0;color:var(--muted);font-size:.85em}
.flow{--s:min(250px,46vh,58vw);flex:1;min-height:0;display:flex;align-items:center;overflow-x:auto;overflow-y:hidden;scroll-snap-type:x mandatory;scrollbar-width:none;padding:0 calc(50% - var(--s)/2);position:relative;-webkit-overflow-scrolling:touch}
.flow::-webkit-scrollbar{display:none}
.cover{flex:none;width:var(--s);height:var(--s);margin:0 calc(var(--s)*-.3);scroll-snap-align:center;text-decoration:none;border-radius:18px;overflow:hidden;display:block;background:var(--card);box-shadow:0 10px 30px rgba(0,0,0,.18);transform-origin:50% 50%;will-change:transform;-webkit-box-reflect:below 6px linear-gradient(transparent 70%,rgba(255,255,255,.18))}
.cover img,.cover .ph{width:100%;height:100%;object-fit:cover;display:grid}
.cover:first-child{margin-left:0}.cover:last-child{margin-right:0}
.now{text-align:center;padding:0 22px;min-height:3.2em}
.now b{display:block;font:700 1.2em/1.2 var(--display);letter-spacing:-.015em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.now span{font-size:.8em;color:var(--muted)}
.scrub{position:relative;align-self:center;width:min(520px,calc(100% - 44px));height:44px;margin-top:6px;touch-action:none;user-select:none;-webkit-user-select:none}
.scrub::before{content:"";position:absolute;left:0;right:0;top:50%;height:4px;margin-top:-2px;border-radius:2px;background:var(--line);transition:opacity .2s}
.scrub .knob{position:absolute;top:50%;left:0;width:56px;height:6px;margin-top:-3px;border-radius:3px;background:var(--muted);transition:opacity .2s}
.scrub .letters{position:absolute;inset:0;display:flex;justify-content:space-evenly;align-items:center;padding:0 6px;border-radius:22px;background:var(--card);border:1px solid var(--line);box-shadow:0 4px 24px rgba(0,0,0,.14);opacity:0;transform:scale(.96);transition:opacity .18s,transform .18s;pointer-events:none}
.scrub.open .letters{opacity:1;transform:none}
.scrub.open .knob,.scrub.open::before{opacity:0}
.scrub .letters a{display:grid;place-items:center;min-width:32px;height:32px;border-radius:16px;font:700 .85em/1 var(--sans);text-decoration:none;color:var(--accent)}
.scrub .letters a.on{background:var(--accent);color:#fff}
"""


def e(s):
    return html.escape(str(s))


def fmt_duration(d):
    if not d:
        return None
    m = re.match(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?", d)
    days, hrs, mins = (int(x) if x else 0 for x in m.groups())
    hrs += days * 24
    parts = ([f"{hrs} hr"] if hrs else []) + ([f"{mins} min"] if mins else [])
    return " ".join(parts) or None


def steps_of(r):
    """Normalize recipeInstructions into (steps, tips, sections)."""
    out = []
    ins = r["recipeInstructions"]
    if isinstance(ins, str):
        ins = [{"@type": "HowToStep", "text": ins}]
    for item in ins:
        if isinstance(item, str):
            out.append(("step", None, item))
        elif item.get("@type") == "HowToSection":
            out.append(("section", item.get("name"), None))
            for s in item.get("itemListElement", []):
                out.append(("step", s.get("name"), s.get("text", "")))
        elif item.get("@type") == "HowToTip":
            out.append(("tip", None, item.get("text", "")))
        else:
            out.append(("step", item.get("name"), item.get("text", "")))
    return out


def validate(slug, r):
    errs = []
    if r.get("@type") != "Recipe":
        errs.append('"@type" must be "Recipe"')
    for k in REQUIRED:
        if not r.get(k):
            errs.append(f"missing {k}")
    for k in ("prepTime", "cookTime", "totalTime"):
        if r.get(k) and not DURATION.match(r[k]):
            errs.append(f"{k} {r[k]!r} is not ISO 8601 (e.g. PT1H15M)")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        errs.append("file name must be lowercase-kebab-case")
    for img in images_of(r):
        if is_local(img) and not (ROOT / img).is_file():
            errs.append(f"image {img!r} not found")
    return errs


COVER_COLORS = [  # muted two-tone gradients for photo-less covers
    ("#3a3f58", "#6a7194"), ("#5b3a46", "#94606f"), ("#2f4a43", "#557f71"),
    ("#6b4a2f", "#a87b52"), ("#7a2e36", "#b3555f"), ("#2f4459", "#5f7f9c"),
    ("#4a3d6b", "#7966a6"), ("#7d5419", "#c08b3d"),
]


def art(r, src, cls="", lazy=False, n=None):
    """The recipe's photo; on the index, a typographic cover when it has none."""
    if src:
        return f'<img class="{cls}" src="{e(src)}" alt=""{" loading=lazy" if lazy else ""}>'
    if cls:  # recipe page and sticky bar: no photo, no image
        return ""
    n = sum(map(ord, r["name"])) if n is None else n
    c1, c2 = COVER_COLORS[n % len(COVER_COLORS)]
    cat = r.get("recipeCategory")
    cat = cat[0] if isinstance(cat, list) else cat
    return (
        f'<span class="ph" style="--c1:{c1};--c2:{c2}" aria-hidden="true">'
        f'<i>{e(cat or "Recipe")}</i><b>{e(r["name"])}</b></span>'
    )


def page(r, slug, base):
    r = {"@context": "https://schema.org", **r}
    imgs = images_of(r)
    hero = ("../" + imgs[0]) if imgs and is_local(imgs[0]) else (imgs[0] if imgs else None)
    if imgs:  # JSON-LD wants absolute URLs
        r["image"] = [base + i if is_local(i) else i for i in imgs]
    facts = []
    if r.get("recipeYield"):
        y = r["recipeYield"]
        facts.append(("Yield", e(y[0] if isinstance(y, list) else y)))
    for label, k in (("Prep", "prepTime"), ("Cook", "cookTime"), ("Total", "totalTime")):
        d = fmt_duration(r.get(k))
        if d:
            facts.append((label, d))

    body, ol_open = [], False
    for kind, name, text in steps_of(r):
        if kind == "section":
            if ol_open:
                body.append("</ol>")
                ol_open = False
            body.append(f"<h3>{e(name)}</h3>")
        elif kind == "step":
            if not ol_open:
                body.append("<ol class='steps'>")
                ol_open = True
            label = f"<strong>{e(name)}.</strong> " if name else ""
            body.append(f"<li>{label}{e(text)}</li>")
        else:
            if ol_open:
                body.append("</ol>")
                ol_open = False
            body.append(f"<p class='tip'><b>Cook's note</b>{e(text)}</p>")
    if ol_open:
        body.append("</ol>")

    cat = r.get("recipeCategory")
    cat = cat[0] if isinstance(cat, list) else cat
    facts_html = (
        '<dl class="facts">'
        + "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in facts)
        + "</dl>"
        if facts
        else ""
    )
    header = f"""<header class="head"><div>
{f'<p class="kicker">{e(cat)}</p>' if cat else ''}
<h1>{e(r['name'])}</h1>
{f'<p class="desc">{e(r["description"])}</p>' if r.get('description') else ''}
</div>{art(r, hero, "photo")}</header>
{facts_html}"""
    source = r.get("isBasedOn") or r.get("url")
    ld_json = json.dumps(r, indent=2, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(r['name'])}</title>
<script type="application/ld+json">
{ld_json}
</script>
<style>{CSS}</style>
</head><body>
<nav class="mini" aria-hidden="true"><div><a class="back" href="../" tabindex="-1">Recipes</a>{art(r, hero, "thumb")}<b>{e(r['name'])}</b></div></nav>
<a class="back" href="../">Recipes</a>
{header}
<section class="card"><h2>Ingredients</h2>
<ul class="ing">{''.join(f'<li>{e(i)}</li>' for i in r['recipeIngredient'])}</ul></section>
<h2>Method</h2>
{''.join(body)}
{f'<p class="source">Adapted from <a href="{e(source)}">{e(source)}</a></p>' if source else ''}
<script>{MINI_JS}</script>
</body></html>
"""


FLOW_JS = """
(()=>{const flow=document.querySelector('.flow');if(!flow)return;
const covers=[...flow.children],now=document.querySelector('.now'),bar=document.querySelector('.scrub'),
knob=bar.querySelector('.knob'),links=[...bar.querySelectorAll('a')];
let cur=-1,timer,down=false,raf=0;
function center(i,smooth){const c=covers[i];flow.scrollTo({left:c.offsetLeft+c.offsetWidth/2-flow.clientWidth/2,behavior:smooth?'smooth':'instant'})}
function render(){raf=0;const mid=flow.scrollLeft+flow.clientWidth/2;let best=0,bd=1e9;
covers.forEach((c,i)=>{const o=(c.offsetLeft+c.offsetWidth/2-mid)/c.offsetWidth,a=Math.max(-1,Math.min(1,o*2)),d=Math.min(Math.abs(o),3);
c.style.transform='perspective(900px) translateZ('+(-Math.min(d,1)*120-d*20)+'px) rotateY('+(-a*62)+'deg)';c.style.zIndex=100-Math.round(d*10);
if(Math.abs(o)<bd){bd=Math.abs(o);best=i}});
const max=flow.scrollWidth-flow.clientWidth,p=max>0?flow.scrollLeft/max:0;
knob.style.transform='translateX('+p*(bar.clientWidth-knob.offsetWidth)+'px)';
if(best!==cur){cur=best;const c=covers[best];now.innerHTML='<b></b><span></span>';now.firstChild.textContent=c.dataset.name;now.lastChild.textContent=c.dataset.sub;
const L=c.dataset.letter;links.forEach(l=>l.classList.toggle('on',l.dataset.l===L))}}
const queue=()=>{if(!raf)raf=requestAnimationFrame(render)};
function open(){bar.classList.add('open');clearTimeout(timer);timer=setTimeout(()=>{if(!down)bar.classList.remove('open')},1200)}
flow.addEventListener('scroll',()=>{queue();open()},{passive:true});addEventListener('resize',queue);
covers.forEach((c,i)=>c.addEventListener('click',e=>{if(i!==cur){e.preventDefault();center(i,true)}}));
addEventListener('keydown',e=>{if(e.key==='ArrowRight'&&cur<covers.length-1)center(cur+1,true);if(e.key==='ArrowLeft'&&cur>0)center(cur-1,true);if(e.key==='Enter')location.href=covers[cur].href});
function go(x){let best=null,d=1e9;links.forEach(a=>{const r=a.getBoundingClientRect(),m=Math.abs(r.left+r.width/2-x);if(m<d){d=m;best=a}});
const i=covers.findIndex(c=>c.dataset.letter===best.dataset.l);if(i>=0&&i!==cur){center(i,false);cancelAnimationFrame(raf);render()}}
bar.addEventListener('pointerdown',e=>{e.preventDefault();down=true;try{bar.setPointerCapture(e.pointerId)}catch(_){}open();go(e.clientX)});
bar.addEventListener('pointermove',e=>{if(down)go(e.clientX)});
const end=()=>{down=false;open()};bar.addEventListener('pointerup',end);bar.addEventListener('pointercancel',end);
bar.addEventListener('click',e=>e.preventDefault());
render();})();
"""


MINI_JS = """
(()=>{const bar=document.querySelector('.mini'),h=document.querySelector('.head h1');if(!bar||!h)return;
new IntersectionObserver(([en])=>{const off=!en.isIntersecting&&en.boundingClientRect.top<0;bar.classList.toggle('show',off);bar.setAttribute('aria-hidden',off?'false':'true')}).observe(h);})();
"""


def letter_of(name):
    c = name.strip()[:1].upper()
    return c if "A" <= c <= "Z" else "#"


def index(recipes):
    items = sorted(recipes, key=lambda x: x[1]["name"].lower())

    def cover(i, slug, r):
        imgs = images_of(r)
        cat = r.get("recipeCategory")
        cat = cat[0] if isinstance(cat, list) else cat
        sub = " · ".join(x for x in (cat, fmt_duration(r.get("totalTime"))) if x)
        return (
            f'<a class="cover" href="{slug}/" data-name="{e(r["name"])}" data-sub="{e(sub)}" '
            f'data-letter="{letter_of(r["name"])}" aria-label="{e(r["name"])}">'
            f'{art(r, imgs[0] if imgs else None, lazy=True, n=i)}</a>'
        )

    letters = []
    for _, r in items:
        L = letter_of(r["name"])
        if L not in letters:
            letters.append(L)
    letters.sort(key=lambda L: (L == "#", L))
    scrub = '<span class="knob"></span><div class="letters">' + "".join(
        f'<a href="#" data-l="{L}">{L}</a>' for L in letters
    ) + "</div>"
    n = len(recipes)
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Recipes</title>
<style>{CSS}</style>
</head><body class="idx">
<header class="masthead"><h1>Recipes</h1><p>{n} recipe{'s' if n != 1 else ''}</p></header>
<div class="flow">{''.join(cover(i, s, r) for i, (s, r) in enumerate(items))}</div>
<div class="now" aria-live="polite"></div>
<nav class="scrub" aria-label="Jump to letter">{scrub}</nav>
<script>{FLOW_JS}</script>
</body></html>
"""


def main():
    check_only = "--check" in sys.argv
    recipes, failed = [], False
    for f in sorted(SRC.glob("*.json")):
        try:
            r = json.loads(f.read_text())
        except json.JSONDecodeError as err:
            print(f"✗ {f.name}: invalid JSON: {err}")
            failed = True
            continue
        errs = validate(f.stem, r)
        if errs:
            print(f"✗ {f.name}: " + "; ".join(errs))
            failed = True
        else:
            recipes.append((f.stem, r))
            print(f"✓ {f.name}")
    if failed:
        sys.exit(1)
    if check_only:
        return
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir()
    (OUT / ".nojekyll").touch()
    if IMAGES.is_dir():
        shutil.copytree(IMAGES, OUT / "images")
    base = site_url()
    (OUT / "index.html").write_text(index(recipes))
    for slug, r in recipes:
        (OUT / slug).mkdir()
        (OUT / slug / "index.html").write_text(page(r, slug, base))
    print(f"Built {len(recipes)} recipe(s) into {OUT}/")


if __name__ == "__main__":
    main()
