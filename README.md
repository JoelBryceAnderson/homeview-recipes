# Recipes

Personal recipe pages built for **Safari's Start Cooking mode on Apple HomeView**.

Each recipe is a [schema.org Recipe](https://schema.org/Recipe) JSON file in
`recipes/`. On every push, GitHub Actions runs `build.py`, which validates the
files and turns each one into a page with the recipe embedded as JSON-LD. The
result is deployed to GitHub Pages.

```
recipes/deviled-eggs.json  →  https://<owner>.github.io/<repo>/deviled-eggs/
```

Open a page in Safari on HomeView, or on iPhone and hand it off, then tap
**Start Cooking**. The same pages also import cleanly into Paprika, Mela,
and other recipe apps.

## Add a recipe

Send Claude a link, pasted recipe or photo and ask it to add the recipe to this
repo. `CLAUDE.md` describes the format. To do it by hand:

1. Add `recipes/<lowercase-kebab-name>.json`.
2. `python3 build.py` builds the site into `_site/` locally (standard library only).
3. Commit and push to `main`.

## One-time setup

**Settings → Pages → Build and deployment → Source: GitHub Actions.**
