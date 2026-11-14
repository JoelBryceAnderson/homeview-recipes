#!/usr/bin/env python3
"""Build a static recipe site from recipes/*.json (schema.org Recipe).

Each recipe becomes _site/<slug>/index.html with the JSON-LD embedded, so
Safari on Apple HomeView (and Paprika, Mela, Google, etc.) can parse it.
Standard library only. Usage: python3 build.py [--check]
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "recipes"
OUT = ROOT / "_site"
REQUIRED = ["name", "recipeIngredient", "recipeInstructions"]
DURATION = re.compile(r"^P(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+S)?)?$")

CSS = """
:root{color-scheme:light dark;--accent:#b3263a}
*{box-sizing:border-box}
body{font:17px/1.55 -apple-system,BlinkMacSystemFont,system-ui,sans-serif;max-width:680px;margin:0 auto;padding:32px 20px 64px}
a{color:var(--accent)}
h1{font-size:1.9em;line-height:1.15;margin:0 0 .35em}
h2{font-size:.95em;text-transform:uppercase;letter-spacing:.07em;opacity:.65;margin:2.2em 0 .6em}
.meta{opacity:.65;font-size:.9em}
li{margin:.5em 0}
.tip{border-left:3px solid var(--accent);padding-left:12px;opacity:.85}
.back{font-size:.9em;text-decoration:none}
.list{list-style:none;padding:0}
.list li{padding:14px 0;border-bottom:1px solid color-mix(in srgb,currentColor 15%,transparent)}
.list a{font-size:1.15em;font-weight:600;text-decoration:none}
.list p{margin:.2em 0 0;opacity:.7;font-size:.9em}
img.hero{width:100%;border-radius:12px;margin:.5em 0 1em}
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
    return errs


def page(r, slug):
    r = {"@context": "https://schema.org", **r}
    meta = []
    if r.get("recipeYield"):
        y = r["recipeYield"]
        meta.append("Yield: " + e(y[0] if isinstance(y, list) else y))
    for label, k in (("Prep", "prepTime"), ("Cook", "cookTime"), ("Total", "totalTime")):
        d = fmt_duration(r.get(k))
        if d:
            meta.append(f"{label} {d}")

    body, ol_open = [], False
    for kind, name, text in steps_of(r):
        if kind == "section":
            if ol_open:
                body.append("</ol>")
                ol_open = False
            body.append(f"<h3>{e(name)}</h3>")
        elif kind == "step":
            if not ol_open:
                body.append("<ol>")
                ol_open = True
            label = f"<strong>{e(name)}.</strong> " if name else ""
            body.append(f"<li>{label}{e(text)}</li>")
        else:
            if ol_open:
                body.append("</ol>")
                ol_open = False
            body.append(f"<p class='tip'>{e(text)}</p>")
    if ol_open:
        body.append("</ol>")

    img = r.get("image")
    if isinstance(img, list):
        img = img[0] if img else None
    if isinstance(img, dict):
        img = img.get("url")
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
<a class="back" href="../">← All recipes</a>
<h1>{e(r['name'])}</h1>
{f'<img class="hero" src="{e(img)}" alt="">' if img else ''}
{f"<p>{e(r['description'])}</p>" if r.get('description') else ''}
<p class="meta">{' · '.join(meta)}</p>
<h2>Ingredients</h2>
<ul>{''.join(f'<li>{e(i)}</li>' for i in r['recipeIngredient'])}</ul>
<h2>Instructions</h2>
{''.join(body)}
{f'<p class="meta">Adapted from <a href="{e(source)}">{e(source)}</a></p>' if source else ''}
</body></html>
"""


def index(recipes):
    items = "".join(
        f'<li><a href="{slug}/">{e(r["name"])}</a>'
        + (f'<p>{e(r.get("description", ""))}</p>' if r.get("description") else "")
        + "</li>"
        for slug, r in sorted(recipes, key=lambda x: x[1]["name"].lower())
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Recipes</title>
<style>{CSS}</style>
</head><body>
<h1>Recipes</h1>
<ul class="list">{items}</ul>
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
    (OUT / "index.html").write_text(index(recipes))
    for slug, r in recipes:
        (OUT / slug).mkdir()
        (OUT / slug / "index.html").write_text(page(r, slug))
    print(f"Built {len(recipes)} recipe(s) into {OUT}/")


if __name__ == "__main__":
    main()
