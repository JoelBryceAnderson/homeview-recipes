# Recipes repo — instructions for Claude

This repo turns recipes into web pages that Safari on Apple HomeView can open in
its "Start Cooking" mode. HomeView reads schema.org `Recipe` JSON-LD from the page,
so each recipe lives as one JSON file and `build.py` wraps it in HTML.

## Adding a recipe

When Joel sends a recipe (a URL, pasted text, or a photo):

1. Write `recipes/<slug>.json`. The slug is lowercase-kebab-case from the dish name
   (`cabernet-cranberry-sauce`). It becomes the URL: `/<slug>/`.
2. Use schema.org Recipe:
   - Required: `@context`, `@type: "Recipe"`, `name`, `recipeIngredient` (array of
     strings, one ingredient per line, amounts included), `recipeInstructions`.
   - `recipeInstructions` is an array of `HowToStep` objects with a short `name`
     and full `text`. Use `HowToSection` for multi-part recipes and `HowToTip` for
     notes (storage, make-ahead, substitutions).
   - The first time a step uses an ingredient, restate its quantity
     ("whisk 1/2 cup mayonnaise and 2 teaspoons mustard"), so the cook never
     has to flip back to the ingredient list. Later mentions can just name it
     ("the filling", "the cranberries").
   - Put explicit durations in step text ("simmer 10 to 15 minutes"). HomeView
     picks up timers from the step text.
   - Times are ISO 8601: `PT15M`, `PT1H20M`. Include `prepTime`, `cookTime` and
     `totalTime` when known, plus `recipeYield`, `description` and `recipeCategory`.
   - If adapted from a web page, set `isBasedOn` to its URL. Don't copy the
     page's headnote or story; write a short `description` in your own words.
   - Images: when Joel sends a photo, run `python3 add_image.py <slug> <photo>`.
     It resizes the photo, strips EXIF/GPS, saves `images/<slug>.jpg` and sets
     `image`. Otherwise `image` may be the source page's own image URL. Never
     invent one or pull in unrelated stock photos.
3. Run `python3 build.py --check`. It must pass.
4. Commit as `Add <dish name>` and push to `main`. GitHub Actions deploys to Pages.
5. Give Joel the link: `https://<owner>.github.io/<repo>/<slug>/`.

## Editing

Change the JSON, not the HTML. `_site/` is generated and git-ignored.
