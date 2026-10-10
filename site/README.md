# site/ — Page Generation

The HTML page in this folder is **not written by hand; it is generated.**
You edit the source, not the output.

## Files

| File | Role |
|---|---|
| `template.html` | **Source.** The skeleton of the page; all visible text is replaced by `{{key}}` placeholders. This is the only hand-edited HTML. |
| `strings.en.json` | English text (a plain `{"key": "value"}` map). |
| `index.html` | **Generated output.** This is the file the READMEs link to and the one you share. |
| `build-cache/` | Downloads Three.js once and caches it during the build only (in `.gitignore`). Not committed. |

> `index.html` is a **generated** file. Do not edit it by hand — it will be
> overwritten on the next build. To change it, edit `template.html` and
> `strings.en.json` and rebuild.

## Build

```bash
python3 tools/build_site.py            # generates site/index.html
python3 tools/build_site.py --check    # does not generate; validates keys and the output
```

`build_site.py` uses only the Python 3.9+ standard library; no external package
is needed. The script runs from any directory (the paths are resolved through
`__file__`).

The first build downloads Three.js from the network once and writes it into
`site/build-cache/`. If there is no network and the cache is empty too, the build
stops with a clear error saying what to do — it does not silently fall back to a
CDN link.

`--check` is suitable for CI: it validates the key set and compares the output
on disk with a freshly regenerated one, catching a stale or hand-edited output.

## Key validation

On every run, and especially under `--check`, `build_site.py` rejects:

- a key that is present in `strings.en.json` but not used anywhere in the template;
- a key that appears in the template as `{{key}}` but has no value in `strings.en.json`.

In either case the script stops with a non-zero exit code and an explanatory
message.

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
that, and the four SVGs are embedded in the same way. The output ends up around
**1.1 MB**. This is a deliberate price paid for single-file portability; using
external files instead of embedding would shrink the page but would remove the
"single file" property.

## English

The site is built in a single language, English. `index.html` is the only
generated page; it is produced from `template.html` and `strings.en.json`.
