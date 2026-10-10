# site/ — Page Generation

The HTML pages in this folder are **not written by hand; they are generated.**
You edit the source, not the output.

## Files

| File | Role |
|---|---|
| `template.html` | **Source.** The skeleton of the page; all visible text is replaced by `{{key}}` placeholders. This is the only hand-edited HTML. |
| `strings.tr.json` | Turkish text (a plain `{"key": "value"}` map). |
| `strings.en.json` | English text. The key set is **exactly the same** as `tr`. |
| `index.html` | **Generated output (English, canonical).** This is the file the READMEs link to and the one you share. |
| `index.tr.html` | **Generated output (Turkish).** |
| `build-cache/` | Downloads Three.js once and caches it during the build only (in `.gitignore`). Not committed. |

> `index.html` and `index.tr.html` are **generated** files. Do not edit them by
> hand — they will be overwritten on the next build. To change them, edit
> `template.html` and the `strings.*.json` files and rebuild.

## Build

```bash
python3 tools/build_site.py            # generates both (en + tr)
python3 tools/build_site.py --lang en  # English only
python3 tools/build_site.py --check    # does not generate; validates keys and outputs
```

`build_site.py` uses only the Python 3.9+ standard library; no external package
is needed. The script runs from any directory (the paths are resolved through
`__file__`).

The first build downloads Three.js from the network once and writes it into
`site/build-cache/`. If there is no network and the cache is empty too, the build
stops with a clear Turkish error saying what to do — it does not silently fall
back to a CDN link.

`--check` is suitable for CI: it validates the key set and compares the outputs
on disk with freshly regenerated ones, catching a stale or hand-edited output.

## Key validation

On every run, and especially under `--check`, `build_site.py` rejects:

- a key missing from one language file (the key sets of the two files must match);
- a key that is present in `strings.*.json` but not used anywhere in the template;
- a key that appears in the template as `{{key}}` but has no value in any language file.

In these three cases the script stops with a non-zero exit code and an
explanatory message.

## Adding a new language

1. Create `site/strings.xx.json`; copy an existing file and translate the values.
   **The key set must not change.**
2. Add the language to the `OUTPUTS` and `ALL_LANGS` definitions in
   `tools/build_site.py` (`OUTPUTS["xx"] = "index.xx.html"`).
3. Run `python3 tools/build_site.py`.

The `<html lang="…">` value for the page language also comes from the `page.lang`
key in `strings.xx.json`; update that too.

## Why is every asset embedded as base64?

The format the page has to be delivered in is **a single file**: an HTML file you
can email to someone, that opens and works offline. To achieve this, during the
build:

- Three.js, as `<script src="data:text/javascript;base64,…">`,
- the four technical drawings (SVG), as `<img src="data:image/svg+xml;base64,…">`

are inlined. This way neither an external URL nor a sibling-file reference
remains in the output; the page needs no CDN access or CORS when opened directly
with `file://`. These are additionally validated after the build.

**The price is size.** Three.js minified is ~590 KB; base64 encoding adds ~33% to
that, and the four SVGs are embedded in the same way. Each output ends up around
**1.1 MB**. This is a deliberate price paid for single-file portability; using
external files instead of embedding would shrink the page but would remove the
"single file" property.

## Turkish and English

- `index.html` → **English** (canonical; the file people share).
- `index.tr.html` → **Turkish**.

Both pages are generated from the same template; apart from the text
substitutions they are identical, so the 3D scene, the timeline, the
cross-section view, part selection and the labels behave the same in both
languages.
