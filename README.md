# HomeView Recipes

Your own recipes in **Start Cooking** mode on Apple HomeView: step-by-step
instructions, ingredient tracking and hands-free timers.

Safari on HomeView builds that view from [schema.org Recipe](https://schema.org/Recipe)
JSON-LD embedded in a web page. This repo keeps each recipe as a JSON file and
uses GitHub Actions to publish a page per recipe to GitHub Pages for free.

```
recipes/deviled-eggs.json  →  https://<you>.github.io/homeview-recipes/deviled-eggs/
```

## Set up your own (5 minutes)

1. **Copy this repo.** Fork it, or create a new **public** repo and upload these
   files. Delete the example recipes in `recipes/` and `images/` if you like.
2. **Turn on Pages.** Go to **Settings → Pages → Source** and pick **GitHub Actions**.
3. **Run it once.** Go to **Actions**, open the latest run and choose **Re-run all
   jobs**. Your index is then live at `https://<you>.github.io/<repo>/`.
4. **Cook.** Open a recipe page in Safari on HomeView, or open it on iPhone and
   hand it off, then tap **Start Cooking**.

## Add recipes

**With Claude (easiest).** Connect the repo to Claude and send it a link,
pasted text or a photo of a cookbook page with "add this to my recipes".
`CLAUDE.md` tells Claude the format, how to check it and how to publish it, and
it replies with the URL.

**By hand.**

1. Add `recipes/<lowercase-kebab-name>.json`. Copy an existing recipe as a
   template.
2. Optional photo: `python3 add_image.py <name> photo.jpg`. This resizes the photo
   and strips location data. Needs `pip install pillow`, plus `pillow-heif` for
   HEIC.
3. Run `python3 build.py --check` to validate, then commit and push.

## Tips

- Write durations into step text ("simmer 10 to 15 minutes"). HomeView sets
  timers from them.
- Times use ISO 8601: `PT15M`, `PT1H20M`.
- Every page also imports cleanly into Paprika, Mela and other recipe apps.
- To preview locally, run `python3 build.py` and then
  `python3 -m http.server -d _site`.
