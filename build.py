#!/usr/bin/env python3
"""Build a static recipe site from recipes/*.json (schema.org Recipe).

Each recipe becomes _site/<slug>/index.html with the JSON-LD embedded, so
Safari on Apple HomeView (and Paprika, Mela, Google, etc.) can parse it.
Standard library only. Usage: python3 build.py [--check]
"""
import html
import json
import math
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
:root{color-scheme:light dark;--a-l:#b0263b;--a-d:#ff6b7f;
--paper:#f2f2f7;--card:#ffffff;--ink:#1c1c1e;--muted:#6e6e73;--line:#e5e5ea;--shadow:0 1px 2px rgba(0,0,0,.05),0 4px 14px rgba(0,0,0,.05);--accent:var(--a-l);
--display:-apple-system,"SF Pro Display",BlinkMacSystemFont,system-ui,sans-serif;--sans:-apple-system,BlinkMacSystemFont,system-ui,sans-serif}
:root[data-accent=blue]{--a-l:#0a64d6;--a-d:#4ea1ff}
:root[data-accent=green]{--a-l:#1d7f46;--a-d:#4cd17f}
:root[data-accent=orange]{--a-l:#c2560f;--a-d:#ff9f45}
:root[data-accent=purple]{--a-l:#6e3fd1;--a-d:#b18cff}
:root[data-accent=tiffany]{--a-l:#0f8a83;--a-d:#4cc4ba}
:root[data-accent=graphite]{--a-l:#48484a;--a-d:#8e8e93}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){color-scheme:dark;--paper:#000;--card:#1c1c1e;--ink:#f5f5f7;--muted:#98989d;--line:#38383a;--shadow:none;--accent:var(--a-d)}}
:root[data-theme=dark]{color-scheme:dark;--paper:#000;--card:#1c1c1e;--ink:#f5f5f7;--muted:#98989d;--line:#38383a;--shadow:none;--accent:var(--a-d)}
:root[data-theme=light]{color-scheme:light}
:root{--tint:color-mix(in srgb,var(--accent) 13%,var(--card))}
*{box-sizing:border-box}
html{touch-action:manipulation;-webkit-text-size-adjust:100%;text-size-adjust:100%;background:var(--paper)}
/* Sized for HomeView: a 7-inch square touch screen with rounded corners. Keep it dense. */
body{font:17px/1.45 var(--sans);color:var(--ink);background:var(--paper);max-width:760px;margin:0 auto;padding:16px 22px 48px}
a{color:var(--accent)}
button{font:inherit;cursor:pointer;-webkit-tap-highlight-color:transparent}
h1,h2,h3{font-family:var(--display);font-weight:700;letter-spacing:-.015em;text-wrap:balance}
h1{font-size:1.75em;line-height:1.08;font-weight:800;letter-spacing:-.025em;margin:.1em 0 .2em}
h2{font-size:1.15em;margin:1.1em 0 .3em}
h3{font-size:1em;margin:1em 0 .1em;color:var(--accent)}
.kicker{font:700 .68em/1.2 var(--sans);text-transform:uppercase;letter-spacing:.14em;color:var(--accent);margin:0}
.back{display:inline-flex;align-items:center;gap:5px;min-height:44px;padding:0 16px 0 12px;border-radius:22px;background:var(--tint);color:var(--ink);font-weight:600;text-decoration:none}
.back::before{content:"‹";font-size:1.5em;line-height:0;color:var(--accent);margin-top:-3px}
/* recipe page */
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
.mini{position:fixed;top:0;left:0;right:0;z-index:5;background:color-mix(in srgb,var(--paper) 88%,transparent);-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);border-bottom:1px solid var(--line);transform:translateY(-110%);transition:transform .32s cubic-bezier(.2,.9,.25,1);visibility:hidden}
.mini.show{transform:none;visibility:visible}
.mini div{max-width:760px;margin:0 auto;padding:8px 22px;display:flex;align-items:center;gap:12px}
.mini .back{flex:none}
.mini .thumb{flex:none;width:40px;height:40px;border-radius:9px;object-fit:cover}
.mini b{font:700 1em/1.2 var(--display);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
/* index: cover flow */
body.idx{max-width:none;height:100vh;height:100dvh;overflow:hidden;padding:12px 0 10px;display:flex;flex-direction:column}
.masthead{display:flex;align-items:center;gap:10px;padding:0 16px 0 22px;min-height:44px}
.masthead h1{font-size:1.6em;margin:0}
.where{flex:none;display:flex;justify-content:center;align-items:center;gap:7px;min-height:22px;font:600 .72em/1 var(--sans);font-variant-numeric:tabular-nums;letter-spacing:.02em;color:var(--muted);opacity:.8;margin:2px 0 4px;transition:opacity .2s}
.active{flex:1;min-width:0;display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;padding:2px 0}
.active::-webkit-scrollbar{display:none}
.clear{flex:none;display:inline-flex;align-items:center;gap:6px;height:30px;padding:0 10px 0 12px;border-radius:15px;border:0;background:var(--accent);color:#fff;font-weight:600;font-size:.78em}
.clear[hidden]{display:none}
.clear::after{content:"×";font-size:1.3em;line-height:0}
.gear,.view{flex:none;display:grid;place-items:center;width:44px;height:44px;border-radius:22px;border:0;background:var(--tint);color:var(--accent);transition:transform .25s cubic-bezier(.2,.9,.3,1.3)}
.gear:active,.view:active{transform:scale(.88)}
/* view toggle icon: three bars (list) that morph into a little coverflow (covers). It shows the view you'll switch to. */
.ic{position:relative;width:24px;height:24px;perspective:36px}
.ic span{position:absolute;left:3px;width:18px;height:3px;border-radius:1.5px;background:currentColor;transition-property:left,top,width,height,border-radius,transform;transition-duration:.5s;transition-timing-function:cubic-bezier(.3,1.35,.45,1)}
.ic span:nth-child(1){top:5.5px}
.ic span:nth-child(2){top:10.5px;transition-delay:.035s}
.ic span:nth-child(3){top:15.5px;transition-delay:.07s}
.view.lv .ic span:nth-child(1){left:1px;top:8px;width:5px;height:8px;border-radius:1.5px;transform:rotateY(42deg)}
.view.lv .ic span:nth-child(2){left:7px;top:7px;width:10px;height:10px;border-radius:2.5px;z-index:1}
.view.lv .ic span:nth-child(3){left:18px;top:8px;width:5px;height:8px;border-radius:1.5px;transform:rotateY(-42deg)}
.gear svg{width:24px;height:24px;fill:currentColor;stroke:currentColor;stroke-width:1.3;stroke-linejoin:round}
.stage{--s:min(290px,52vh,62vw);position:relative;flex:1;min-height:0;overflow:hidden}
.probe{position:absolute;width:var(--s);height:0;visibility:hidden}
.cover{position:absolute;left:50%;top:45%;width:var(--s);height:var(--s);margin:calc(var(--s)/-2) 0 0 calc(var(--s)/-2);border-radius:18px;overflow:hidden;display:block;text-decoration:none;color:#fff;background:var(--card);box-shadow:0 10px 30px rgba(0,0,0,.22);will-change:transform;-webkit-box-reflect:below 6px linear-gradient(transparent 74%,rgba(255,255,255,.16))}
.cover[hidden]{display:none}
.cover img,.cover .ph{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}
.ph{background:radial-gradient(circle at 15% 0%,rgba(255,255,255,.2),transparent 55%),linear-gradient(160deg,var(--c2),var(--c1))}
.cap{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:space-between;padding:8%;text-align:left}
.cover.pic .cap{background:linear-gradient(rgba(0,0,0,.45),transparent 30%,transparent 48%,rgba(0,0,0,.72))}
.cap i{font:700 calc(var(--s)*.042)/1.2 var(--sans);font-style:normal;text-transform:uppercase;letter-spacing:.16em;opacity:.85}
.cap b{font:800 calc(var(--s)*.1)/1.03 var(--display);letter-spacing:-.025em;text-wrap:balance;display:-webkit-box;-webkit-line-clamp:5;-webkit-box-orient:vertical;overflow:hidden;text-shadow:0 1px 8px rgba(0,0,0,.18)}
.wl{position:relative;display:grid;width:22px;height:22px;border-radius:11px;overflow:hidden;background:var(--tint);color:var(--accent);font:700 1.15em/1 var(--sans)}
.wl:empty{display:none}
.wl b{grid-area:1/1;display:grid;place-items:center}
.flow{position:absolute;inset:0;overflow-x:auto;overflow-y:hidden;scrollbar-width:none;z-index:3000;-webkit-overflow-scrolling:touch}
.flow::-webkit-scrollbar{display:none}
.track{position:relative;height:100%}
.snap{position:absolute;top:0;width:2px;height:1px;scroll-snap-align:center}
.scrub{position:relative;align-self:center;width:min(520px,calc(100% - 44px));height:44px;flex:none;touch-action:none;user-select:none;-webkit-user-select:none}
.scrub::before{content:"";position:absolute;left:0;right:0;top:50%;height:4px;margin-top:-2px;border-radius:2px;background:var(--line);transition:opacity .25s .3s}
.scrub .knob{position:absolute;top:50%;left:0;width:56px;height:6px;margin-top:-3px;border-radius:3px;background:var(--muted);transition:opacity .25s .3s}
.scrub.open .knob,.scrub.open::before{opacity:0;transition:opacity .12s}
.scrub .letters{position:absolute;inset:0;display:flex;justify-content:space-between;align-items:center;padding:0 22px;pointer-events:none}
.scrub .shape{position:absolute;left:0;top:0;width:100%;height:100%;overflow:visible;pointer-events:none;filter:drop-shadow(0 4px 14px rgba(0,0,0,.13));
transform-origin:50% 50%;transform:scale(.97,.1);opacity:0;transition:transform .34s cubic-bezier(.45,0,.2,1) .1s,opacity .14s .34s}
.scrub.open .shape{transform:none;opacity:1;transition:transform .5s cubic-bezier(.2,1.3,.4,1),opacity .1s}
.scrub .letters a span{display:block;opacity:0;scale:.2;transition:opacity .16s,scale .22s cubic-bezier(.5,0,.75,0);transition-delay:var(--d,0s)}
.scrub.open .letters a span{opacity:1;scale:1;transition:opacity .2s,scale .5s cubic-bezier(.2,1.7,.4,1);transition-delay:var(--d,0s)}
.scrub .shape path{fill:var(--card);stroke:var(--line);stroke-width:1}
.scrub .letters a{position:relative;flex:1;max-width:30px;display:grid;place-items:center;height:30px;border-radius:15px;font:700 .72em/1 var(--sans);text-decoration:none;color:var(--accent);transform-origin:50% 100%;transition:transform .42s cubic-bezier(.2,1.5,.35,1),background .15s,color .15s}
.scrub.mag .letters a{transition:background .15s,color .15s}
.scrub .sel{position:absolute;left:0;top:0;width:34px;height:34px;margin:-17px 0 0 -17px;border-radius:50%;background:var(--accent);box-shadow:0 2px 8px rgba(0,0,0,.2);opacity:0;transition:transform .2s cubic-bezier(.2,.9,.3,1.05),opacity .15s;pointer-events:none}
.scrub.open .sel{opacity:1}
.scrub .letters a.on{color:var(--accent)}
.scrub .letters.lit a.on{color:#fff}
.scrub .letters a.off{color:var(--muted);opacity:.35}
/* index: list view */
.list{position:absolute;inset:0;z-index:4000;overflow-y:auto;overscroll-behavior:contain;-webkit-overflow-scrolling:touch;padding:0 16px 16px}
.list[hidden],.row[hidden],.lh[hidden]{display:none}
.lw{max-width:640px;margin:0 auto}
.lcount{margin:0;padding:18px 0 6px;text-align:center;font:600 .78em/1 var(--sans);color:var(--muted);font-variant-numeric:tabular-nums}
.lh{position:sticky;top:0;z-index:1;margin:0;padding:10px 6px 5px;font:700 .72em/1 var(--sans);letter-spacing:.12em;color:var(--accent);background:color-mix(in srgb,var(--paper) 88%,transparent);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px)}
.row{display:flex;align-items:center;gap:14px;min-height:68px;padding:8px 6px;color:var(--ink);text-decoration:none;position:relative;-webkit-tap-highlight-color:transparent}
.row::before{content:"";position:absolute;left:72px;right:0;bottom:0;height:1px;background:var(--line);transform-origin:0 50%;transition:transform .5s cubic-bezier(.2,.9,.25,1) var(--dd,0s)}
.list.pre .row::before{transform:scaleX(0);transition-duration:.16s;transition-delay:0s}
.row:active{background:var(--tint)}
.row::after{content:"›";flex:none;margin-left:auto;font-size:1.5em;line-height:1;color:var(--muted)}
.th{position:relative;flex:none;width:52px;height:52px;border-radius:10px;overflow:hidden;background:var(--card);box-shadow:var(--shadow)}
.th img,.th .ph{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}
.tx{min-width:0}
.tx i{display:block;font:700 .62em/1.4 var(--sans);font-style:normal;text-transform:uppercase;letter-spacing:.14em;color:var(--muted)}
.tx b{display:block;font:650 1em/1.2 var(--display);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.stage.lvd .cover,.stage.lvd .flow{visibility:hidden}
.listing .where{display:none}
.listing .list{padding-right:44px}
/* in list view the letter bar stands on the right edge: the same element, turned and mirrored so A sits at the top
   and the magnifying bulge opens to the left; each letter is turned back upright */
.listing .scrub{position:fixed;margin:0;z-index:4200;transform-origin:0 50%;transform:rotate(90deg) scaleY(-1)}
.listing .scrub .letters a span{display:block;transform:rotate(90deg) scaleY(-1)}
.rail{position:fixed;left:0;top:0;width:100%;height:100%;z-index:4500;pointer-events:none;overflow:visible}
.rail path{fill:none;stroke-linecap:round}
.rail .t{stroke:var(--line);stroke-width:4}
.rail .k{stroke:var(--muted);stroke-width:6}
.ghost{position:fixed;z-index:9000;pointer-events:none;overflow:hidden;border-radius:18px;transform-origin:50% 50%;will-change:transform;box-shadow:0 10px 30px rgba(0,0,0,.22)}
/* settings sheet */
.sheet{position:fixed;top:62px;right:14px;width:min(330px,calc(100% - 28px));background:var(--card);border:1px solid var(--line);border-radius:18px;box-shadow:0 14px 44px rgba(0,0,0,.26);padding:14px 16px 16px;z-index:5000}
.sheet[hidden]{display:none}
.sheet h3{margin:0 0 .55em;font:700 .66em/1.2 var(--sans);text-transform:uppercase;letter-spacing:.13em;color:var(--muted)}
.sheet section+section{margin-top:14px}
.swatches{display:flex;gap:9px;flex-wrap:wrap}
.swatches button{width:32px;height:32px;border-radius:50%;border:0;background:var(--sw);box-shadow:inset 0 0 0 1px rgba(0,0,0,.1);transition:box-shadow .2s}
.swatches button[aria-pressed=true]{box-shadow:0 0 0 2px var(--card),0 0 0 4px var(--sw)}
.seg{display:flex;background:var(--paper);border-radius:10px;padding:3px}
.seg button{flex:1;height:34px;border:0;border-radius:8px;background:none;color:var(--ink);font-weight:600;font-size:.82em}
.seg button[aria-pressed=true]{background:var(--card);box-shadow:0 1px 4px rgba(0,0,0,.16)}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chips button{height:34px;padding:0 14px;border-radius:17px;border:0;background:var(--tint);color:var(--accent);font-weight:600;font-size:.82em}
.chips button[aria-pressed=true]{background:var(--accent);color:#fff}
/* motion */
.fly{position:fixed;z-index:9000;pointer-events:none;perspective:1800px;transform-origin:50% 50%;will-change:transform;-webkit-box-reflect:below 6px linear-gradient(transparent 74%,rgba(255,255,255,.16))}
:root.tween,:root.tween *,:root.tween *::before,:root.tween *::after{transition:background-color .45s cubic-bezier(.3,0,.2,1),color .45s cubic-bezier(.3,0,.2,1),border-color .45s,box-shadow .45s,fill .45s,stroke .45s,opacity .2s!important}
.flip{position:absolute;inset:0;transform-style:preserve-3d;will-change:transform}
.face{position:absolute;inset:0;overflow:hidden;border-radius:18px;-webkit-backface-visibility:hidden;backface-visibility:hidden;box-shadow:0 24px 70px rgba(0,0,0,.3)}
.front{color:#fff;background:var(--card)}
.front img,.front .ph{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}
.front.pic .cap{background:linear-gradient(rgba(0,0,0,.45),transparent 30%,transparent 48%,rgba(0,0,0,.72))}
.backf{transform:rotateY(180deg);background:var(--paper)}
.pg{position:absolute;left:0;top:0;transform-origin:0 0;color:var(--ink);text-align:left}
.pg .in{max-width:760px;margin:0 auto;padding:16px 22px}
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
ACCENTS = [("", "#b0263b", "Cranberry"), ("blue", "#0a64d6", "Blue"), ("green", "#1d7f46", "Green"),
           ("orange", "#c2560f", "Orange"), ("purple", "#6e3fd1", "Purple"), ("tiffany", "#81d8d0", "Tiffany blue"),
           ("graphite", "#48484a", "Graphite")]


def spring_linear(response=0.42, damping=0.84, n=40):
    """CSS linear() approximation of an Apple-style damped spring, plus its settle time (ms)."""
    w = 2 * math.pi / response
    wd = w * math.sqrt(1 - damping * damping)
    T = -math.log(0.002) / (damping * w)
    pts = []
    for k in range(n + 1):
        t = T * k / n
        x = 1 - math.exp(-damping * w * t) * (math.cos(wd * t) + damping * w / wd * math.sin(wd * t))
        pts.append(f"{x:.4f}")
    return "linear(" + ",".join(pts) + ")", round(T * 1000)


SPRING, SPRING_MS = spring_linear()
FLIP, FLIP_MS = spring_linear(0.58, 0.8)  # slower, slightly bouncier spring for the card flip


def cat_of(r):
    c = r.get("recipeCategory")
    return (c[0] if isinstance(c, list) and c else c) or ""


def art(src, cls):
    return f'<img class="{cls}" src="{e(src)}" alt="">' if src else ""


def content_html(r):
    """Ingredients card and method steps."""
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
    ing = "".join(f"<li>{e(i)}</li>" for i in r["recipeIngredient"])
    return f'<section class="card"><h2>Ingredients</h2>\n<ul class="ing">{ing}</ul></section>\n<h2>Method</h2>\n{"".join(body)}'


def head_html(r, img):
    """Top of a recipe page: category, title, description, photo and facts.
    Also rendered onto the back of each index cover so the flip lands seamlessly."""
    facts = []
    if r.get("recipeYield"):
        y = r["recipeYield"]
        facts.append(("Yield", e(y[0] if isinstance(y, list) else y)))
    for label, k in (("Prep", "prepTime"), ("Cook", "cookTime"), ("Total", "totalTime")):
        d = fmt_duration(r.get(k))
        if d:
            facts.append((label, d))
    cat = cat_of(r)
    facts_html = (
        '<dl class="facts">' + "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in facts) + "</dl>"
        if facts else ""
    )
    return f"""<header class="head"><div>
{f'<p class="kicker">{e(cat)}</p>' if cat else ''}
<h1>{e(r['name'])}</h1>
{f'<p class="desc">{e(r["description"])}</p>' if r.get('description') else ''}
</div>{art(img, "photo")}</header>
{facts_html}"""


THEME_JS = "document.addEventListener('gesturestart',e=>e.preventDefault());(()=>{try{const s=JSON.parse(localStorage.getItem('hv-recipes'))||{},r=document.documentElement;if(s.accent)r.dataset.accent=s.accent;if(s.theme)r.dataset.theme=s.theme}catch(_){}})();"

MOTION_JS = """
const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches,
LIN=CSS.supports('animation-timing-function','linear(0, 1)'),EASE=LIN?'%SPRING%':'cubic-bezier(.2,.9,.25,1.05)',DUR=%DUR%,
FEASE=LIN?'%FLIP%':'cubic-bezier(.3,.9,.3,1.05)',FDUR=%FDUR%,
ss={get:k=>{try{return sessionStorage.getItem(k)}catch(_){return null}},set:(k,v)=>{try{v==null?sessionStorage.removeItem(k):sessionStorage.setItem(k,v)}catch(_){}}};
function arc(base,a,b,lift){const N=16,f=[],x0=a.x+a.w/2,y0=a.y+a.h/2,x1=b.x+b.w/2,y1=b.y+b.h/2,mx=(x0+x1)/2+(x1-x0)*.15,my=Math.min(y0,y1)-lift,bx=base.x+base.w/2,by=base.y+base.h/2;
for(let k=0;k<=N;k++){const t=k/N,u=1-t,cx=u*u*x0+2*u*t*mx+t*t*x1,cy=u*u*y0+2*u*t*my+t*t*y1,sx=(a.w+(b.w-a.w)*t)/base.w,sy=(a.h+(b.h-a.h)*t)/base.h,r=a.r+(b.r-a.r)*t;
f.push({transform:'translate('+(cx-bx).toFixed(2)+'px,'+(cy-by).toFixed(2)+'px) scale('+sx.toFixed(4)+','+sy.toFixed(4)+')',borderRadius:(r/sx).toFixed(2)+'px / '+(r/sy).toFixed(2)+'px',offset:t})}return f}
"""

PAGE_JS = """
(()=>{%MOTION%
const bar=document.querySelector('.mini'),h=document.querySelector('.head h1');
if(bar&&h)new IntersectionObserver(([en])=>{const off=!en.isIntersecting&&en.boundingClientRect.top<0;bar.classList.toggle('show',off);bar.setAttribute('aria-hidden',off?'false':'true')}).observe(h);
const slug=location.pathname.split('/').filter(Boolean).pop();
ss.set('hv-open',null);
document.querySelectorAll('a.back').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();ss.set('hv-back',slug);ss.set('hv-pos',slug);
if(reduce){location.href=a.href;return}
const y0=scrollY;if(y0<2){location.href=a.href;return}
const ms=Math.min(520,240+y0*.25),t0=performance.now();let gone=false;const leave=()=>{if(!gone){gone=true;location.href=a.href}};
const tick=t=>{const k=Math.min(1,(t-t0)/ms),ez=k<.5?4*k*k*k:1-Math.pow(-2*k+2,3)/2;scrollTo(0,y0*(1-ez));if(k<1)requestAnimationFrame(tick);else leave()};
requestAnimationFrame(tick);setTimeout(leave,ms+300)}));
addEventListener('pageshow',e=>{if(e.persisted)document.body.getAnimations().forEach(x=>x.cancel())});
})();
"""

FLOW_JS = """
(()=>{%MOTION%
const root=document.documentElement,KEY='hv-recipes';
let st={};try{st=JSON.parse(localStorage.getItem(KEY))||{}}catch(_){}
if(!Array.isArray(st.filters))st.filters=st.filter?[st.filter]:[];delete st.filter;
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(st))}catch(_){}};
const stage=document.querySelector('.stage'),flow=stage.querySelector('.flow'),track=flow.querySelector('.track'),probe=stage.querySelector('.probe'),
all=[...stage.querySelectorAll('.cover')],bar=document.querySelector('.scrub'),knob=bar.querySelector('.knob'),strip=bar.querySelector('.letters'),
sheet=document.querySelector('.sheet'),gear=document.querySelector('.gear'),act=document.querySelector('.active'),where=document.querySelector('.where'),
list=stage.querySelector('.list'),rows=[...list.querySelectorAll('.row')],heads=[...list.querySelectorAll('.lh')],vbtn=document.querySelector('.view');
let vis=[],pos=[],marks=[],S=1,step=1,cur=-1,anim=0,down=false,timer,picked='',LV=st.view==='list',lrows=[],lset=-1,vfin=null;
const X=o=>{const a=Math.abs(o),n=Math.min(a,1);return Math.sign(o)*(S*.66*Math.sqrt(n)+Math.max(a-1,0)*S*.19)};

function layout(slug){
S=Math.max(120,Math.round(Math.min(290,stage.clientHeight*.62,stage.clientWidth*.62)));stage.style.setProperty('--s',S+'px');step=S*.55;
const F=st.filters;vis=all.filter(c=>!F.length||F.includes(c.dataset.cat));if(!vis.length){st.filters=[];vis=all.slice()}
all.forEach(c=>{c.hidden=!vis.includes(c)});
const vs=new Set(vis.map(c=>c.dataset.slug));rows.forEach(r=>{r.hidden=!vs.has(r.dataset.slug)});lrows=rows.filter(r=>!r.hidden);
heads.forEach(h=>{h.hidden=!lrows.some(r=>r.dataset.letter===h.dataset.letter)});
list.querySelector('.lcount').textContent=lrows.length+(lrows.length===1?' Recipe':' Recipes');
marks.forEach(m=>m.remove());marks=[];pos=[];let p=0,prev=null;
vis.forEach(c=>{const L=c.dataset.letter;
pos.push(p);p+=1;prev=L});
const cw=flow.clientWidth;track.style.width=pos[pos.length-1]*step+cw+'px';track.innerHTML='';
pos.forEach(q=>{const s=document.createElement('span');s.className='snap';s.style.left=q*step+cw/2-1+'px';track.appendChild(s)});
strip.innerHTML='<svg class="shape" aria-hidden="true"><path/></svg><span class="sel"></span>';const have=new Set(vis.map(c=>c.dataset.letter));[...'ABCDEFGHIJKLMNOPQRSTUVWXYZ',...(have.has('#')?['#']:[])].forEach(L=>{const a=document.createElement('a');a.href='#';a.dataset.l=L;a.innerHTML='<span>'+L+'</span>';if(!have.has(L)){a.className='off';a.setAttribute('aria-disabled','true')}strip.appendChild(a)});
let i=slug?vis.findIndex(c=>c.dataset.slug===slug):0;if(i<0)i=0;
flow.style.scrollSnapType='none';flow.scrollLeft=pos[i]*step;requestAnimationFrame(()=>{flow.style.scrollSnapType=''});
cur=-1;render();sync();if(LV)lknob()}

function render(){const f=flow.scrollLeft/step;let best=0,bd=1e9;
vis.forEach((c,i)=>{const o=pos[i]-f,a=Math.abs(o),n=Math.min(a,1);
c.style.transform='translateX('+X(o).toFixed(1)+'px) perspective(1100px) translateZ('+(-n*170).toFixed(1)+'px) rotateY('+(-Math.sign(o)*n*64).toFixed(2)+'deg)';
c.style.zIndex=1000-Math.round(a*100);c.style.visibility=a>7?'hidden':'';if(a<bd){bd=a;best=i}});
marks.forEach(m=>{const o=m._p-f;m.style.transform='translateX('+X(o).toFixed(1)+'px)';m.style.opacity=Math.max(0,1-Math.abs(o)*.42).toFixed(2)});
if(!LV){const max=flow.scrollWidth-flow.clientWidth;knob.style.transform='translateX('+((max>0?flow.scrollLeft/max:0)*(bar.clientWidth-knob.offsetWidth)).toFixed(1)+'px)'}
if(best!==cur){cur=best;setWhere();ss.set('hv-pos',vis[cur].dataset.slug);if(!down&&!anim&&!bar.classList.contains('mag'))sync()}}
// counter under the covers: current letter rolls up or down as you cross into another letter
const wl=where.querySelector('.wl'),wn=where.querySelector('.wn');let wL='';
function setWhere(){const c=vis[cur];if(!c)return;wn.textContent=(cur+1)+' of '+vis.length;const L=c.dataset.letter;if(L===wL)return;
const dir=L>wL?1:-1,old=wl.lastChild,b=document.createElement('b');b.textContent=L;[...wl.children].forEach(x=>{if(x!==old)x.remove()});wl.appendChild(b);
if(old&&wL&&!reduce){old.animate([{transform:'none',opacity:1},{transform:'translateY('+(-dir*90)+'%)',opacity:0}],{duration:220,easing:'cubic-bezier(.4,0,1,1)',fill:'forwards'}).onfinish=()=>old.remove();
b.animate([{transform:'translateY('+(dir*90)+'%)',opacity:0},{transform:'none',opacity:1}],{duration:DUR,easing:EASE})}else if(old)old.remove();wL=L}
function sync(){if(!vis[cur])return;const L=vis[cur].dataset.letter;strip.querySelectorAll('a').forEach(a=>a.classList.toggle('on',a.dataset.l===L));draw()}

function refilter(){if(LV){const was=new Set(lrows);layout(vis[cur]&&vis[cur].dataset.slug);lscroll();
if(!reduce)lrows.forEach(r=>{if(!was.has(r))r.animate([{opacity:0,transform:'translateY(12px)'},{opacity:1,transform:'none'}],{duration:DUR,easing:EASE})});return}
const old=new Map(all.filter(c=>!c.hidden).map(c=>[c,{t:c.style.transform,z:c.style.zIndex}]));
all.forEach(c=>c.getAnimations().forEach(a=>a.cancel()));layout(vis[cur]&&vis[cur].dataset.slug);if(reduce)return;
const off=' translateY(46px) scale(.72)';
all.forEach(c=>{const o=old.get(c),t=c.style.transform;
if(!c.hidden&&o){if(o.t!==t)c.animate([{transform:o.t},{transform:t}],{duration:DUR,easing:EASE})}
else if(!c.hidden)c.animate([{transform:t+off,opacity:0},{transform:t,opacity:1}],{duration:DUR,delay:90,easing:EASE,fill:'backwards'});
else if(o){c.hidden=false;c.style.transform=o.t;c.style.zIndex=o.z;let gone=false;const fin=()=>{if(gone||vis.includes(c))return;gone=true;c.hidden=true;c.getAnimations().forEach(a=>a.cancel())};
c.animate([{transform:o.t,opacity:1},{transform:o.t+off,opacity:0}],{duration:220,easing:'cubic-bezier(.4,0,1,1)',fill:'forwards'}).onfinish=fin;setTimeout(fin,500)}});
marks.forEach(m=>m.animate([{opacity:0},{opacity:+m.style.opacity||0}],{duration:260,delay:120,fill:'backwards'}))}
function stop(){if(anim){cancelAnimationFrame(anim);anim=0;flow.style.scrollSnapType=''}}
function go(i,settle){if(i<0||i>=vis.length)return;const from=flow.scrollLeft,d=pos[i]*step-from;if(Math.abs(d)<.5)return;stop();
if(reduce){flow.scrollLeft=from+d;render();return}
const ms=settle?Math.min(420,200+Math.abs(d)/step*260):Math.min(700,340+Math.abs(d)/step*30),t0=performance.now();
const tick=t=>{const k=Math.min(1,(t-t0)/ms),ez=settle?1-Math.pow(1-k,3):k<.5?4*k*k*k:1-Math.pow(-2*k+2,3)/2;flow.scrollLeft=from+d*ez;render();
if(k<1)anim=requestAnimationFrame(tick);else{anim=0;flow.style.scrollSnapType='';if(!down&&!bar.classList.contains('mag'))sync()}};anim=requestAnimationFrame(tick)}
let rq=0,idle=0,touching=false;const SETTLE_WAIT=260;
function settle(){if(touching||anim||down||!vis.length)return;const f=flow.scrollLeft/step;let i=0,bd=1e9;pos.forEach((q,j)=>{const d=Math.abs(q-f);if(d<bd){bd=d;i=j}});go(i,true)}
flow.addEventListener('scroll',()=>{if(anim)return;if(!rq)rq=requestAnimationFrame(()=>{rq=0;render()});clearTimeout(idle);idle=setTimeout(settle,SETTLE_WAIT)},{passive:true});
flow.addEventListener('touchstart',()=>{touching=true;stop();clearTimeout(idle)},{passive:true});
['touchend','touchcancel'].forEach(ev=>flow.addEventListener(ev,()=>{touching=false;clearTimeout(idle);idle=setTimeout(settle,SETTLE_WAIT)},{passive:true}));
flow.addEventListener('wheel',stop,{passive:true});
addEventListener('resize',()=>{vplace();layout(vis[cur]&&vis[cur].dataset.slug);draw()});

const AMAX=30,sh={x:0,a:0,vx:0,va:0,tx:0,ta:0};let sraf=0;
function shape(w,h,bx,amp){const r=h/2,sg=48,y=x=>{const q=(x-bx)/sg;return -amp*Math.exp(-q*q)};let d='M'+r+' '+h+'C'+(r*.08)+' '+h+' '+(r*.08)+' '+y(r).toFixed(2)+' '+r+' '+y(r).toFixed(2);
for(let x=r+4;x<w-r;x+=4)d+='L'+x+' '+y(x).toFixed(2);const yr=y(w-r).toFixed(2);
return d+'L'+(w-r)+' '+yr+'C'+(w-r*.08)+' '+yr+' '+(w-r*.08)+' '+h+' '+(w-r)+' '+h+'Z'}
function draw(){const w=strip.clientWidth,h=strip.clientHeight,as=[...strip.querySelectorAll('a')],n=as.length,m=Math.max(0,sh.a/AMAX);let bx=sh.x;
if(n>1&&m>.001){const c=as.map(a=>a.offsetLeft+a.offsetWidth/2),sp=(c[n-1]-c[0])/(n-1),k=c.map(x=>{const q=(x-sh.x)/(sp*1.35);return m*Math.exp(-q*q)}),
wt=k.map(v=>1+v*1.15),U=wt.reduce((x,y)=>x+y,0);let acc=0;const t=wt.map(v=>{const p=c[0]-sp/2+(acc+v/2)/U*n*sp;acc+=v;return p});
const sel=strip.querySelector('.sel');as.forEach((a,i)=>{const sc=1+k[i]*.85,dy=-k[i]*15;a.style.transform='translate('+(t[i]-c[i]).toFixed(1)+'px,'+dy.toFixed(1)+'px) scale('+sc.toFixed(3)+')';
if(a.classList.contains('on')){sel.style.transform='translate('+t[i].toFixed(1)+'px,'+(a.offsetTop+a.offsetHeight/2+dy-(sc-1)*a.offsetHeight/2+13*(1-k[i])).toFixed(1)+'px) scale('+(.15+.85*k[i]).toFixed(3)+')';strip.classList.toggle('lit',k[i]>.55)}});
const j=Math.max(0,Math.min(n-2,Math.floor((sh.x-c[0])/sp))),f=Math.max(0,Math.min(1,(sh.x-c[j])/sp));bx=t[j]+(t[j+1]-t[j])*f}
else{as.forEach(a=>{a.style.transform=''});strip.classList.remove('lit');const on=strip.querySelector('a.on');if(on)strip.querySelector('.sel').style.transform='translate('+(on.offsetLeft+on.offsetWidth/2)+'px,'+(on.offsetTop+on.offsetHeight/2+13)+'px) scale(.15)'}
bx=Math.max(h/2+24,Math.min(w-h/2-24,bx));strip.querySelector('.shape path').setAttribute('d',shape(w,h,bx,Math.max(0,sh.a)))}
function spring(){sh.vx=sh.vx*.6+(sh.tx-sh.x)*.24;sh.x+=sh.vx;sh.va=sh.va*.62+(sh.ta-sh.a)*.2;sh.a+=sh.va;draw();
if(Math.abs(sh.tx-sh.x)+Math.abs(sh.vx)+Math.abs(sh.ta-sh.a)+Math.abs(sh.va)>.05){sraf=requestAnimationFrame(spring);return}
sraf=0;sh.x=sh.tx;sh.a=sh.ta;sh.vx=sh.va=0;if(!sh.ta){bar.classList.remove('mag');where.style.opacity='';if(!anim){sync();return}}draw()}
const kick=()=>{if(!sraf)sraf=requestAnimationFrame(spring)};
function mag(x){const on=strip.querySelector('a.on:not(.off)'),rx=on?on.offsetLeft+on.offsetWidth/2:x-edge();if(!bar.classList.contains('mag')){sh.x=rx}sh.tx=rx;sh.ta=AMAX;bar.classList.add('mag');where.style.opacity='0';kick()}
function unmag(){sh.ta=0;kick()}
function pick(x){let best=null,d=1e9;const L=edge();[...strip.querySelectorAll('a:not(.off)')].forEach(a=>{const m=Math.abs(L+a.offsetLeft+a.offsetWidth/2-x);if(m<d){d=m;best=a}});
if(best&&best.dataset.l!==picked){picked=best.dataset.l;strip.querySelectorAll('a').forEach(a=>a.classList.toggle('on',a===best));draw();jump(vis.findIndex(c=>c.dataset.letter===picked))}}
function jump(i){if(!LV){go(i);return}const r=lrows[i];if(r)list.scrollTo({top:r.offsetTop-hh(),behavior:reduce?'auto':'smooth'})}
const ax=e=>LV?e.clientY:e.clientX,edge=()=>{const r=strip.getBoundingClientRect();return LV?r.top:r.left};
// opening ripples out from the letter under the finger; closing folds the far letters in first, towards the chosen one
function ripple(opening){const as=[...strip.querySelectorAll('a')],i0=Math.max(0,as.indexOf(strip.querySelector('a.on'))),m=Math.max(i0,as.length-1-i0);
as.forEach((a,i)=>{const k=Math.abs(i-i0);a.style.setProperty('--d',(opening?k*12:(m-k)*6)+'ms')})}
bar.addEventListener('pointerdown',e=>{e.preventDefault();down=true;picked='';clearTimeout(timer);try{bar.setPointerCapture(e.pointerId)}catch(_){}pick(ax(e));
if(!bar.classList.contains('open')){ripple(true);bar.classList.add('open')}if(!reduce)mag(ax(e))});
bar.addEventListener('pointermove',e=>{if(down){pick(ax(e));if(!reduce)mag(ax(e))}});
const end=()=>{if(!down)return;down=false;unmag();clearTimeout(timer);timer=setTimeout(()=>{ripple(false);bar.classList.remove('open')},650)};
bar.addEventListener('pointerup',end);bar.addEventListener('pointercancel',end);bar.addEventListener('click',e=>e.preventDefault());

function fly(el,rect,rad,bare){const r=rect||el.getBoundingClientRect(),W=innerWidth,H=innerHeight,d=document.createElement('div');d.className='fly';
d.style.cssText='left:'+r.left+'px;top:'+r.top+'px;width:'+r.width+'px;height:'+r.height+'px;--s:'+r.width+'px';
d.innerHTML='<div class="flip"><div class="face front'+(el.classList.contains('pic')?' pic':'')+'"></div><div class="face backf"><div class="pg" style="width:'+W+'px;height:'+H+'px;transform:scale('+r.width/W+','+r.height/H+')"><div class="in"></div></div></div></div>';
const front=d.querySelector('.front');[...el.children].forEach(n=>{if(n.tagName!=='TEMPLATE'&&!(bare&&n.classList.contains('cap')))front.appendChild(n.cloneNode(true))});
d.querySelector('.in').innerHTML=el.querySelector('template').innerHTML;document.body.appendChild(d);
return{d,flip:d.firstChild,faces:[...d.querySelectorAll('.face')],r:{x:r.left,y:r.top,w:r.width,h:r.height,r:rad||18}}}
const full=()=>({x:0,y:0,w:innerWidth,h:innerHeight,r:0});
function morph(o,a,b,r0,r1,lift,done){const fr=arc(o.r,a,b,lift),opt={duration:FDUR,easing:FEASE,fill:'forwards'};
o.d.animate(fr.map(f=>({transform:f.transform,offset:f.offset})),opt);
o.faces.forEach(x=>x.animate(fr.map(f=>({borderRadius:f.borderRadius,offset:f.offset})),opt));
let fin=false;const f=()=>{if(fin)return;fin=true;done()};
o.flip.animate([{transform:'rotateY('+r0+'deg)'},{transform:'rotateY('+r1+'deg)'}],opt).onfinish=f;setTimeout(f,FDUR+400)}
function open(el){ss.set('hv-pos',el.dataset.slug);const href=el.getAttribute('href');if(reduce){location.href=href;return}
ss.set('hv-open','1');const o=fly(el);el.style.opacity='0';morph(o,o.r,full(),0,180,innerHeight*.1,()=>{location.href=href})}
function back(){const slug=ss.get('hv-back');ss.set('hv-back',null);if(!slug||reduce)return;
if(LV){const r=rowOf(slug);if(!r||r.hidden)return;const th=r.querySelector('.th'),o=fly(coverOf(slug),th.getBoundingClientRect(),10,true);th.style.opacity='0';
morph(o,full(),o.r,180,0,innerHeight*.06,()=>{th.style.opacity='';o.d.remove()});return}
const el=vis.find(c=>c.dataset.slug===slug);if(!el)return;
const o=fly(el);el.style.opacity='0';morph(o,full(),o.r,180,0,innerHeight*.06,()=>{el.style.opacity='';o.d.remove()})}
flow.addEventListener('click',e=>{if(!sheet.hidden)return;const el=document.elementsFromPoint(e.clientX,e.clientY).find(n=>n.classList&&n.classList.contains('cover'));
if(!el)return;e.preventDefault();const i=vis.indexOf(el);if(i===cur)open(el);else go(i)});
addEventListener('keydown',e=>{if(!sheet.hidden){if(e.key==='Escape')closeSheet();return}if(LV)return;
if(e.key==='ArrowRight')go(cur+1);else if(e.key==='ArrowLeft')go(cur-1);else if(e.key==='Enter'&&vis[cur]&&!e.target.closest('a,button'))open(vis[cur])});
all.forEach(c=>c.addEventListener('click',e=>{e.preventDefault();open(c)}));

/* list view */
const rowOf=s=>rows.find(r=>r.dataset.slug===s),coverOf=s=>all.find(c=>c.dataset.slug===s),
hh=()=>{const h=heads.find(x=>!x.hidden);return h?h.offsetHeight:0},
box=(r,rad)=>({x:r.left,y:r.top,w:r.width,h:r.height,r:rad}),
seen=(el,R)=>{const r=el.getBoundingClientRect();return r.bottom>R.top&&r.top<R.bottom&&r.right>R.left&&r.left<R.right};
function lknob(){const max=list.scrollHeight-list.clientHeight;knob.style.transform='translateX('+((max>0?list.scrollTop/max:0)*(bar.clientWidth-knob.offsetWidth)).toFixed(1)+'px)'}
function lscroll(){lknob();if(Math.abs(list.scrollTop-lset)<1)return;lset=-1;const y=list.scrollTop+hh()+2;let i=lrows.findIndex(r=>r.offsetTop+r.offsetHeight>y);if(i<0)i=lrows.length-1;
if(i>=0&&i!==cur){cur=i;setWhere();ss.set('hv-pos',vis[cur].dataset.slug);if(!down&&!bar.classList.contains('mag'))sync()}}
function place(slug){const r=rowOf(slug);if(!r||r.hidden)return;list.scrollTop=r.offsetTop-hh();lset=list.scrollTop;lknob()}
let lq=0;list.addEventListener('scroll',()=>{if(!lq)lq=requestAnimationFrame(()=>{lq=0;lscroll()})},{passive:true});
function openRow(row){const s=row.dataset.slug,href=row.getAttribute('href');ss.set('hv-pos',s);if(reduce){location.href=href;return}
ss.set('hv-open','1');const th=row.querySelector('.th'),o=fly(coverOf(s),th.getBoundingClientRect(),10,true);th.style.opacity='0';morph(o,o.r,full(),0,180,innerHeight*.1,()=>{location.href=href})}
list.addEventListener('click',e=>{const r=e.target.closest('.row');if(!r)return;e.preventDefault();if(sheet.hidden)openRow(r)});
function ghost(c,r){const d=document.createElement('div');d.className='ghost front'+(c.classList.contains('pic')?' pic':'');
d.style.cssText='left:'+r.left+'px;top:'+r.top+'px;width:'+r.width+'px;height:'+r.height+'px;--s:'+r.width+'px';
[...c.children].forEach(n=>{if(n.tagName!=='TEMPLATE')d.appendChild(n.cloneNode(true))});document.body.appendChild(d);return d}
function vplace(){const b=bar.style;if(!LV){b.top=b.left=b.width='';return}const t=document.querySelector('.masthead').getBoundingClientRect().bottom+12;
b.top=(t-22)+'px';b.left=(innerWidth-24)+'px';b.width=Math.max(160,innerHeight-t-76)+'px'}
function vstate(){vbtn.classList.toggle('lv',LV);vbtn.setAttribute('aria-label',LV?'Show as covers':'Show as list');document.body.classList.toggle('listing',LV);vplace()}
function geom(){const r=bar.getBoundingClientRect(),k=knob.getBoundingClientRect();
return LV?{v:1,x:r.left+r.width/2,a:r.top,b:r.bottom,k:k.top+k.height/2}:{v:0,y:r.top+r.height/2,a:r.left,b:r.right,k:k.left+k.width/2}}
// the letter bar's track and knob slide along one path: the bottom edge, round the bottom-right corner, up the right edge
let rfin=null;
function rail(g0,g1){if(reduce||g0.v===g1.v)return;const h=g0.v?g1:g0,v=g0.v?g0:g1,y=h.y,x0=h.a,xv=v.x,R=Math.max(0,Math.min(44,y-v.b,xv-h.b)),
sv=xv-R-x0+Math.PI*R/2,sH=x=>x-x0,sV=q=>sv+(y-R-q),d='M'+x0+' '+y+'H'+(xv-R)+'A'+R+' '+R+' 0 0 0 '+xv+' '+(y-R)+'V'+Math.min(v.a,y-R),
tr=[[sH(h.a)+2,sH(h.b)-2],[sV(v.b)+2,sV(v.a)-2]],kn=[sH(h.k),sV(v.k)],s=document.createElementNS('http://www.w3.org/2000/svg','svg');
s.setAttribute('class','rail');s.innerHTML='<path class="t" d="'+d+'"/><path class="k" d="'+d+'"/>';document.body.appendChild(s);
const i=g0.v?1:0,j=1-i,seg=(a,b)=>({strokeDasharray:(b-a).toFixed(1)+'px 100000px',strokeDashoffset:(-a).toFixed(1)+'px'}),o={duration:DUR+200,easing:EASE,fill:'forwards'};
bar.style.opacity='0';s.firstChild.animate([seg(...tr[i]),seg(...tr[j])],o);const an=s.lastChild.animate([seg(kn[i]-25,kn[i]+25),seg(kn[j]-25,kn[j]+25)],o);
let done=false;const f=rfin=()=>{if(done)return;done=true;rfin=null;s.remove();bar.style.opacity=''};an.onfinish=f;setTimeout(f,DUR+700)}
function setView(v){if(v===LV)return;if(vfin)vfin();if(rfin)rfin();const g0=geom();LV=v;if(LV)st.view='list';else delete st.view;save();(LV?toList:toCovers)();rail(g0,geom())}
// covers -> list: the centre cover shrinks into its row's thumbnail while the rest of the flow falls away and rows cascade in
function toList(){stop();const c=vis[cur],r0=c&&c.getBoundingClientRect(),R=stage.getBoundingClientRect(),
was=all.filter(x=>!x.hidden&&x!==c&&x.style.visibility!=='hidden'&&seen(x,R));
vstate();if(!reduce)list.classList.add('pre');stage.classList.add('lv');list.hidden=false;if(c)place(c.dataset.slug);
if(reduce||!c){stage.classList.add('lvd');return}
const row=rowOf(c.dataset.slug),th=row.querySelector('.th'),r1=th.getBoundingClientRect(),d=ghost(c,r0),cap=d.querySelector('.cap'),kill=[];
c.style.opacity='0';th.style.opacity='0';
kill.push(d.animate(arc(box(r0),box(r0,18),box(r1,10),24),{duration:DUR,easing:EASE,fill:'forwards'}));
if(cap)kill.push(cap.animate([{opacity:1},{opacity:0}],{duration:160,fill:'forwards'}));
was.forEach(x=>kill.push(x.animate([{opacity:1},{opacity:0,transform:x.style.transform+' scale(.82)'}],{duration:240,easing:'cubic-bezier(.4,0,1,1)',fill:'forwards'})));
marks.forEach(m=>kill.push(m.animate([{opacity:+m.style.opacity||0},{opacity:0}],{duration:180,fill:'forwards'})));
const LR=list.getBoundingClientRect(),ci=lrows.indexOf(row);
// dividers wait until the outgoing covers have cleared, then draw in left to right
lrows.forEach((r,i)=>{if(!seen(r,LR)){r.style.setProperty('--dd','0s');return}const me=r===row;r.style.setProperty('--dd',(200+Math.min(280,Math.abs(i-ci)*40))+'ms');
(me?r.querySelector('.tx'):r).animate([{opacity:0,transform:me?'translateX(-14px)':'translateY('+(i<ci?-18:18)+'px)'},{opacity:1,transform:'none'}],
{duration:DUR,delay:me?110:Math.min(320,50+Math.abs(i-ci)*45),easing:EASE,fill:'backwards'})});
heads.forEach(h=>{if(!h.hidden&&seen(h,LR))h.animate([{opacity:0},{opacity:1}],{duration:220,delay:230,fill:'backwards'})});
void list.offsetWidth;list.classList.remove('pre');
let done=false;const f=vfin=()=>{if(done)return;done=true;vfin=null;stage.classList.add('lvd');c.style.opacity='';th.style.opacity='';d.remove();kill.forEach(a=>a.cancel())};
kill[0].onfinish=f;setTimeout(f,DUR+400)}
// list -> covers: the top row's thumbnail grows back into the centre cover and its neighbours fan out around it
function toCovers(){const c0=vis[cur],rw=c0&&rowOf(c0.dataset.slug),th=rw&&rw.querySelector('.th'),LR=list.getBoundingClientRect(),
r0=th&&seen(th,LR)?th.getBoundingClientRect():null,out=lrows.filter(r=>seen(r,LR)),hs=heads.filter(h=>!h.hidden&&seen(h,LR));
vstate();stage.classList.remove('lvd');layout(c0&&c0.dataset.slug);
const shut=()=>{list.hidden=true;list.classList.remove('pre');stage.classList.remove('lv')};
const c=vis[cur];if(reduce||!c){shut();return}
const r1=c.getBoundingClientRect(),R=stage.getBoundingClientRect(),kill=[];let d=null;
if(r0){d=ghost(c,r1);c.style.opacity='0';th.style.opacity='0';const cap=d.querySelector('.cap');
kill.push(d.animate(arc(box(r1),box(r0,10),box(r1,18),24),{duration:DUR,easing:EASE,fill:'forwards'}));
if(cap)cap.animate([{opacity:0},{opacity:1}],{duration:220,delay:DUR*.45,fill:'backwards'})}
else c.animate([{opacity:0,transform:c.style.transform+' scale(.82)'},{opacity:1,transform:c.style.transform}],{duration:DUR,delay:80,easing:EASE,fill:'backwards'});
list.classList.add('pre');hs.forEach(h=>kill.push(h.animate([{opacity:1},{opacity:0}],{duration:120,fill:'forwards'})));
where.animate({opacity:[0,.8]},{duration:260,delay:260,fill:'backwards'});
out.forEach((r,i)=>kill.push(r.animate([{opacity:1},{opacity:0,transform:'translateY(10px) scale(.98)'}],{duration:200,delay:Math.min(i*18,120),easing:'cubic-bezier(.4,0,1,1)',fill:'forwards'})));
vis.forEach((x,i)=>{if(x===c||x.style.visibility==='hidden'||!seen(x,R))return;
x.animate([{opacity:0,transform:x.style.transform+' scale(.82)'},{opacity:1,transform:x.style.transform}],{duration:DUR,delay:140+Math.abs(i-cur)*55,easing:EASE,fill:'backwards'})});
marks.forEach(m=>m.animate([{opacity:0},{opacity:+m.style.opacity||0}],{duration:260,delay:200,fill:'backwards'}));
let done=false;const f=vfin=()=>{if(done)return;done=true;vfin=null;shut();c.style.opacity='';if(th)th.style.opacity='';if(d)d.remove();kill.forEach(a=>a.cancel())};
if(d)kill[0].onfinish=f;setTimeout(f,d?DUR+400:340)}
vbtn.addEventListener('click',()=>setView(!LV));

function apply(){const set=(k,v)=>{if(v)root.dataset[k]=v;else delete root.dataset[k]};set('accent',st.accent);set('theme',st.theme);
sheet.querySelectorAll('[data-accent]').forEach(b=>b.setAttribute('aria-pressed',String((st.accent||'')===b.dataset.accent)));
sheet.querySelectorAll('[data-mode]').forEach(b=>b.setAttribute('aria-pressed',String((st.theme||'')===b.dataset.mode)));
const F=st.filters;sheet.querySelectorAll('[data-cat]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.cat?F.includes(b.dataset.cat):!F.length)));
const had=new Set([...act.children].map(b=>b.dataset.c));act.innerHTML='';F.forEach(c=>{const b=document.createElement('button');b.className='clear';b.dataset.c=c;b.textContent=c;
b.setAttribute('aria-label','Remove '+c+' filter');act.appendChild(b);if(!had.has(c)&&!reduce)b.animate([{transform:'scale(.6)',opacity:0},{transform:'none',opacity:1}],{duration:DUR,easing:EASE})})}
function openSheet(){apply();sheet.hidden=false;gear.setAttribute('aria-expanded','true');if(reduce)return;
const g=gear.getBoundingClientRect(),s=sheet.getBoundingClientRect(),ox=s.width-22,oy=22,dx=g.left+g.width/2-(s.left+ox),dy=g.top+g.height/2-(s.top+oy),N=12,fr=[];
for(let k=0;k<=N;k++){const t=k/N,u=1-t,x=u*u*dx+2*u*t*dx*.15,y=u*u*dy+2*u*t*(dy*.9),sc=.1+.9*t;
fr.push({transform:'translate('+(x).toFixed(1)+'px,'+(y).toFixed(1)+'px) scale('+sc.toFixed(3)+')',borderRadius:(44-26*t)+'px',offset:t})}
sheet.style.transformOrigin=ox+'px '+oy+'px';sheet.animate(fr,{duration:DUR,easing:EASE});
sheet.animate([{opacity:0},{opacity:1}],{duration:140});
[...sheet.children].forEach((n,i)=>n.animate([{opacity:0,transform:'translateY(-10px)'},{opacity:1,transform:'none'}],{duration:DUR,delay:60+i*45,easing:EASE,fill:'backwards'}))}
function closeSheet(){if(sheet.hidden)return;gear.setAttribute('aria-expanded','false');if(reduce){sheet.hidden=true;return}
const g=gear.getBoundingClientRect(),s=sheet.getBoundingClientRect(),ox=s.width-22,oy=22,dx=g.left+g.width/2-(s.left+ox),dy=g.top+g.height/2-(s.top+oy);
sheet.animate([{transform:'none',opacity:1},{transform:'translate('+dx*.6+'px,'+dy*.2+'px) scale(.55)',opacity:.6,offset:.6},{transform:'translate('+dx+'px,'+dy+'px) scale(.1)',opacity:0}],
{duration:230,easing:'cubic-bezier(.4,0,.8,.4)'}).onfinish=()=>{sheet.hidden=true};setTimeout(()=>{sheet.hidden=true},400)}
gear.addEventListener('click',e=>{e.stopPropagation();sheet.hidden?openSheet():closeSheet()});
document.addEventListener('pointerdown',e=>{if(!sheet.hidden&&!sheet.contains(e.target)&&!gear.contains(e.target))closeSheet()});
let tw;function themed(fn){if(reduce){fn();return}clearTimeout(tw);root.classList.add('tween');void root.offsetWidth;fn();tw=setTimeout(()=>root.classList.remove('tween'),520)}
sheet.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
if('cat' in b.dataset){const c=b.dataset.cat,F=st.filters;st.filters=!c?[]:F.includes(c)?F.filter(x=>x!==c):[...F,c];save();apply();refilter();return}
const k='accent' in b.dataset?'accent':'theme',v='accent' in b.dataset?b.dataset.accent:b.dataset.mode;if((st[k]||'')===v)return;
themed(()=>{st[k]=v;save();apply()})});
act.addEventListener('click',e=>{const b=e.target.closest('.clear');if(!b)return;st.filters=st.filters.filter(x=>x!==b.dataset.c);save();apply();refilter()});
addEventListener('pageshow',e=>{if(e.persisted){document.querySelectorAll('.fly,.ghost').forEach(n=>n.remove());all.forEach(c=>c.style.opacity='');list.querySelectorAll('.th').forEach(t=>t.style.opacity='');
layout(ss.get('hv-pos'));if(LV)place(vis[cur]&&vis[cur].dataset.slug);back()}});
vstate();apply();if(LV){stage.classList.add('lv','lvd');list.hidden=false}layout(ss.get('hv-pos'));if(LV)place(vis[cur]&&vis[cur].dataset.slug);back();
})();
"""

MOTION_JS = (MOTION_JS.replace("%SPRING%", SPRING).replace("%DUR%", str(SPRING_MS))
             .replace("%FLIP%", FLIP).replace("%FDUR%", str(FLIP_MS)))
PAGE_JS = PAGE_JS.replace("%MOTION%", MOTION_JS)
FLOW_JS = FLOW_JS.replace("%MOTION%", MOTION_JS)


def page(r, slug, base):
    r = {"@context": "https://schema.org", **r}
    imgs = images_of(r)
    hero = ("../" + imgs[0]) if imgs and is_local(imgs[0]) else (imgs[0] if imgs else None)
    if imgs:  # JSON-LD wants absolute URLs
        r["image"] = [base + i if is_local(i) else i for i in imgs]
    header = head_html(r, hero)
    source = r.get("isBasedOn") or r.get("url")
    ld_json = json.dumps(r, indent=2, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>{e(r['name'])}</title>
<script>{THEME_JS}</script>
<script type="application/ld+json">
{ld_json}
</script>
<style>{CSS}</style>
</head><body>
<nav class="mini" aria-hidden="true"><div><a class="back" href="../" tabindex="-1">Recipes</a>{art(hero, "thumb")}<b>{e(r['name'])}</b></div></nav>
<a class="back" href="../">Recipes</a>
{header}
{content_html(r)}
{f'<p class="source">Adapted from <a href="{e(source)}">{e(source)}</a></p>' if source else ''}
<script>{PAGE_JS}</script>
</body></html>
"""


def letter_of(name):
    c = name.strip()[:1].upper()
    return c if "A" <= c <= "Z" else "#"


def gear_svg(teeth=8, ro=10.2, ri=7.7, hole=3.6):
    """A filled gear, generated so the geometry is exact."""
    pts, step = [], 2 * math.pi / teeth
    for k in range(teeth):
        b = k * step - math.pi / 2
        for rad, off in ((ri, -.34), (ro, -.2), (ro, .2), (ri, .34)):
            a = b + off * step
            pts.append(f"{12 + rad * math.cos(a):.2f} {12 + rad * math.sin(a):.2f}")
    d = "M" + " L".join(pts) + f" Z M{12 + hole} 12 A{hole} {hole} 0 1 0 {12 - hole} 12 A{hole} {hole} 0 1 0 {12 + hole} 12 Z"
    return f'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill-rule="evenodd" d="{d}"/></svg>'


GEAR_SVG = gear_svg()


def index(recipes):
    items = sorted(recipes, key=lambda x: x[1]["name"].lower())
    cats = sorted({cat_of(r) for _, r in items if cat_of(r)})

    def kicker_of(r):
        return " · ".join(x for x in (cat_of(r), fmt_duration(r.get("totalTime"))) if x) or "Recipe"

    def bg_of(i, r):
        imgs = images_of(r)
        if imgs:
            return f'<img src="{e(imgs[0])}" alt="" loading="lazy">'
        c1, c2 = COVER_COLORS[i % len(COVER_COLORS)]
        return f'<span class="ph" style="--c1:{c1};--c2:{c2}"></span>'

    def cover(i, slug, r):
        imgs = images_of(r)
        cat, kicker, bg = cat_of(r), kicker_of(r), bg_of(i, r)
        cls = "cover pic" if imgs else "cover"
        return (
            f'<a class="{cls}" href="{slug}/" data-slug="{slug}" data-letter="{letter_of(r["name"])}" '
            f'data-cat="{e(cat)}">{bg}<span class="cap"><i>{e(kicker)}</i><b>{e(r["name"])}</b></span>'
            f'<template><span class="back">Recipes</span>{head_html(r, imgs[0] if imgs else None)}{content_html(r)}</template></a>'
        )

    rows, prev = [], None
    for i, (slug, r) in enumerate(items):
        L = letter_of(r["name"])
        if L != prev:
            rows.append(f'<h4 class="lh" data-letter="{L}">{L}</h4>')
            prev = L
        rows.append(
            f'<a class="row" href="{slug}/" data-slug="{slug}" data-letter="{L}" data-cat="{e(cat_of(r))}">'
            f'<span class="th">{bg_of(i, r)}</span><span class="tx"><i>{e(kicker_of(r))}</i><b>{e(r["name"])}</b></span></a>'
        )

    swatches = "".join(
        f'<button data-accent="{k}" style="--sw:{c}" aria-label="{n}" aria-pressed="false"></button>' for k, c, n in ACCENTS
    )
    modes = "".join(f'<button data-mode="{k}" aria-pressed="false">{n}</button>' for k, n in (("", "Auto"), ("light", "Light"), ("dark", "Dark")))
    chips = '<button data-cat="" aria-pressed="false">All</button>' + "".join(
        f'<button data-cat="{e(c)}" aria-pressed="false">{e(c)}</button>' for c in cats
    )
    n = len(recipes)
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Recipes</title>
<script>{THEME_JS}</script>
<style>{CSS}</style>
</head><body class="idx">
<header class="masthead"><h1>Recipes</h1><div class="active" aria-label="Active filters"></div>
<button class="view" aria-label="Show as list"><span class="ic" aria-hidden="true"><span></span><span></span><span></span></span></button>
<button class="gear" aria-label="Settings" aria-expanded="false">{GEAR_SVG}</button></header>
<div class="stage"><span class="probe"></span>{''.join(cover(i, s, r) for i, (s, r) in enumerate(items))}
<div class="flow"><div class="track"></div></div>
<div class="list" hidden><div class="lw">{''.join(rows)}<p class="lcount"></p></div></div></div>
<div class="where"><span class="wl" aria-hidden="true"></span><span class="wn" aria-live="polite"></span></div>
<nav class="scrub" aria-label="Jump to letter"><span class="knob"></span><div class="letters"></div></nav>
<div class="sheet" hidden role="dialog" aria-label="Settings">
<section><h3>Theme colour</h3><div class="swatches">{swatches}</div></section>
<section><h3>Appearance</h3><div class="seg">{modes}</div></section>
<section><h3>Show</h3><div class="chips">{chips}</div></section>
</div>
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
