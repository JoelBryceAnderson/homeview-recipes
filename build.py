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
/* Sized for HomeView: a 7-inch square touch screen with rounded corners, read from arm's length. */
body{font:19px/1.5 var(--sans);color:var(--ink);background:var(--paper);max-width:760px;margin:0 auto;padding:24px 28px 80px}
a{color:var(--accent)}
h1,h2,h3{font-family:var(--display);font-weight:700;letter-spacing:-.015em;text-wrap:balance}
h1{font-weight:800;letter-spacing:-.025em}
h1{font-size:2em;line-height:1.08;margin:.15em 0 .3em}
h2{font-size:1.3em;margin:1.8em 0 .5em}
h3{font-size:1.1em;margin:1.4em 0 .2em;color:var(--accent)}
.kicker{font:700 .7em/1.2 var(--sans);text-transform:uppercase;letter-spacing:.14em;color:var(--accent);margin:0}
.muted{color:var(--muted)}
.back{display:inline-flex;align-items:center;gap:6px;min-height:48px;padding:0 18px 0 14px;border-radius:24px;background:var(--tint);color:var(--ink);font-weight:600;text-decoration:none}
.back::before{content:"‹";font-size:1.5em;line-height:0;color:var(--accent);margin-top:-3px}
/* recipe page */
.head{display:grid;grid-template-columns:1fr auto;gap:22px;align-items:start;margin:22px 0 8px}
.head.noimg{grid-template-columns:1fr}
.head .desc{margin:.2em 0 0;color:var(--muted);font-size:.95em}
.photo{width:clamp(130px,34vw,220px);aspect-ratio:1;border-radius:14px;object-fit:cover;box-shadow:var(--shadow);display:block}
.facts{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(0,1fr);margin:18px 0 0;padding:14px 0 0;border-top:1px solid var(--line)}
.facts div{padding:0 14px}
.facts div:first-child{padding-left:0}
.facts div+div{border-left:1px solid var(--line)}
.facts dt{font:700 .62em/1.4 var(--sans);text-transform:uppercase;letter-spacing:.14em;color:var(--muted)}
.facts dd{margin:0;font:600 1em/1.3 var(--display)}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow);padding:6px 24px 8px;margin:26px 0}
.card h2{margin:.6em 0 0;padding-bottom:.35em;border-bottom:2px solid var(--accent)}
.ing{list-style:none;padding:0;margin:0}
.ing li{padding:11px 0;border-bottom:1px solid var(--line)}
.ing li:last-child{border:0}
.steps{list-style:none;padding:0;margin:0;counter-reset:step}
.steps li{position:relative;counter-increment:step;padding:14px 0 16px 52px;border-bottom:1px solid var(--line)}
.steps li:last-child{border:0}
.steps li::before{content:counter(step);position:absolute;left:0;top:13px;width:36px;height:36px;border-radius:50%;background:var(--accent);color:#fff;display:grid;place-items:center;font:700 .95em/1 var(--display);font-variant-numeric:tabular-nums}
.steps strong{font-family:var(--display);font-weight:650}
.tip{background:var(--tint);border-radius:12px;padding:14px 18px;margin:16px 0}
.tip b{display:block;font:700 .66em/1.6 var(--sans);text-transform:uppercase;letter-spacing:.14em;color:var(--accent)}
.source{font-size:.8em;color:var(--muted);overflow-wrap:anywhere}
/* index */
.idx{padding-right:64px}
.masthead{margin:8px 0 6px}
.masthead h1{font-size:2.4em;margin:0;letter-spacing:-.03em}
.masthead p{margin:.2em 0 0;color:var(--muted)}
.group{margin:0}
.letter{position:sticky;top:0;z-index:1;margin:0;padding:14px 0 6px;background:var(--paper);font-size:1.5em;color:var(--accent);border-bottom:2px solid var(--accent)}
.list{list-style:none;padding:0;margin:0 0 8px}
.list li{border-bottom:1px solid var(--line)}
.list li:last-child{border:0}
.list a{display:flex;gap:18px;align-items:center;min-height:116px;padding:14px 0;text-decoration:none;color:inherit}
.list img,.list .ph{flex:none;width:86px;height:86px;border-radius:12px;object-fit:cover;background:var(--tint);box-shadow:var(--shadow)}
.list .ph{display:grid;place-items:center;font:700 2.1em/1 var(--display);color:var(--accent);box-shadow:none}
.list b{display:block;font:700 1.15em/1.2 var(--display);margin:.15em 0}
.list .sub{font-size:.8em;color:var(--muted)}
.scrub{position:fixed;top:50%;right:max(10px,calc(50vw - 380px + 6px));transform:translateY(-50%);display:flex;flex-direction:column;justify-content:space-between;height:min(calc(100vh - 72px),620px);width:44px;padding:8px 0;border-radius:22px;background:var(--card);border:1px solid var(--line);box-shadow:var(--shadow);touch-action:none;user-select:none;-webkit-user-select:none;z-index:2}
.scrub a,.scrub span{display:block;text-align:center;font:700 .7em/1 var(--sans);text-decoration:none;flex:1;display:grid;place-items:center}
.scrub span{color:var(--muted);opacity:.4}
.scrub a.on{color:var(--card);background:var(--accent);border-radius:8px;margin:0 6px}
.mini{position:fixed;top:0;left:0;right:0;z-index:5;background:color-mix(in srgb,var(--paper) 88%,transparent);-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);border-bottom:1px solid var(--line);transform:translateY(-110%);transition:transform .22s ease;visibility:hidden}
.mini.show{transform:none;visibility:visible}
.mini div{max-width:760px;margin:0 auto;padding:10px 28px;display:flex;align-items:center;gap:14px}
.mini .back{flex:none;padding:0 14px 0 12px}
.mini img{flex:none;width:44px;height:44px;border-radius:9px;object-fit:cover}
.mini b{font:700 1.05em/1.2 var(--display);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
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
    header = f"""<header class="head{'' if hero else ' noimg'}"><div>
{f'<p class="kicker">{e(cat)}</p>' if cat else ''}
<h1>{e(r['name'])}</h1>
{f'<p class="desc">{e(r["description"])}</p>' if r.get('description') else ''}
</div>{f'<img class="photo" src="{e(hero)}" alt="">' if hero else ''}</header>
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
<nav class="mini" aria-hidden="true"><div><a class="back" href="../" tabindex="-1">Recipes</a>{f'<img src="{e(hero)}" alt="">' if hero else ''}<b>{e(r['name'])}</b></div></nav>
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


SCRUB_JS = """
(()=>{const bar=document.querySelector('.scrub');if(!bar)return;
const links=[...bar.querySelectorAll('a')];let cur;
function go(y){let best=null,d=1e9;for(const a of links){const r=a.getBoundingClientRect(),m=Math.abs(r.top+r.height/2-y);if(m<d){d=m;best=a}}
if(best&&best!==cur){cur=best;const t=document.querySelector(best.getAttribute('href'));window.scrollTo({top:t.getBoundingClientRect().top+scrollY,behavior:'instant'});links.forEach(l=>l.classList.toggle('on',l===best))}}
let down=false;
bar.addEventListener('pointerdown',e=>{e.preventDefault();down=true;try{bar.setPointerCapture(e.pointerId)}catch(_){}go(e.clientY)});
bar.addEventListener('pointermove',e=>{if(down)go(e.clientY)});
bar.addEventListener('pointercancel',()=>{down=false});
bar.addEventListener('pointerup',()=>{down=false;setTimeout(()=>{links.forEach(l=>l.classList.remove('on'));cur=null},400)});
bar.addEventListener('click',e=>e.preventDefault());})();
"""


MINI_JS = """
(()=>{const bar=document.querySelector('.mini'),h=document.querySelector('.head h1');if(!bar||!h)return;
new IntersectionObserver(([en])=>{const off=!en.isIntersecting&&en.boundingClientRect.top<0;bar.classList.toggle('show',off);bar.setAttribute('aria-hidden',off?'false':'true')}).observe(h);})();
"""


def letter_of(name):
    c = name.strip()[:1].upper()
    return c if "A" <= c <= "Z" else "#"


def index(recipes):
    def item(slug, r):
        imgs = images_of(r)
        thumb = (
            f'<img src="{e(imgs[0])}" alt="" loading="lazy">'
            if imgs
            else f'<span class="ph">{e(letter_of(r["name"]))}</span>'
        )
        cat = r.get("recipeCategory")
        cat = cat[0] if isinstance(cat, list) else cat
        total = fmt_duration(r.get("totalTime"))
        sub = " · ".join(x for x in (cat, total) if x)
        sub_html = f'<span class="sub">{e(sub)}</span>' if sub else ""
        return f'<li><a href="{slug}/"><span>{thumb}</span><span><b>{e(r["name"])}</b>{sub_html}</span></a></li>'

    groups = {}
    for slug, r in sorted(recipes, key=lambda x: x[1]["name"].lower()):
        groups.setdefault(letter_of(r["name"]), []).append((slug, r))
    order = sorted(groups, key=lambda L: (L == "#", L))
    sections = "".join(
        f'<section class="group" id="L-{L if L != "#" else "0"}"><h2 class="letter">{L}</h2>'
        f'<ul class="list">{"".join(item(s_, r) for s_, r in groups[L])}</ul></section>'
        for L in order
    )
    letters = [chr(c) for c in range(ord("A"), ord("Z") + 1)] + (["#"] if "#" in groups else [])
    scrub = "".join(
        f'<a href="#L-{L if L != "#" else "0"}">{L}</a>' if L in groups else f"<span>{L}</span>"
        for L in letters
    )
    n = len(recipes)
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Recipes</title>
<style>{CSS}</style>
</head><body class="idx">
<header class="masthead"><h1>Recipes</h1><p>{n} recipe{'s' if n != 1 else ''}, A to Z</p></header>
{sections}
<nav class="scrub" aria-label="Jump to letter">{scrub}</nav>
<script>{SCRUB_JS}</script>
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
