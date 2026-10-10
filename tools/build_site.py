#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Produce single-file, fully self-contained HTML outputs from the
site/template.html template.

Usage:
    python3 build_site.py                 # produce both (en + tr)
    python3 build_site.py --lang en       # English only
    python3 build_site.py --check         # do not build, verify

Outputs:
    site/index.html      (English, canonical)
    site/index.tr.html   (Turkish)

Each output is a single file: Three.js and the four SVGs are embedded as base64
`data:` URIs, so the page opens offline and on its own.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple

# --- Paths: resolved via __file__ so it runs from any directory. ---
ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT / "site"
TEMPLATE_PATH = SITE_DIR / "template.html"
CACHE_DIR = SITE_DIR / "build-cache"
THREE_CACHE = CACHE_DIR / "three.min.js"

# Three.js, downloaded once and cached during the build.
THREE_URL = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"

# Language -> output file mapping.  English is the canonical output and keeps
# index.html (the path READMEs link to); Turkish lives beside it as
# index.tr.html.
OUTPUTS: Dict[str, str] = {"en": "index.html", "tr": "index.tr.html"}
ALL_LANGS: Tuple[str, ...] = ("tr", "en")

# SVGs to embed (relative to the repository root).  Key: the path after
# "../hardware/" in the template.
SVG_FILES: Tuple[str, ...] = (
    "hardware/pcb/pcb-layout-top.svg",
    "hardware/pcb/pcb-layout-bottom.svg",
    "hardware/diagrams/case-exploded.svg",
    "hardware/schematic/pocket-reader-schematic.svg",
)

# Placeholder and asset patterns.
PLACEHOLDER = re.compile(r"\{\{([a-z0-9_.]+)\}\}")
SCRIPT_SRC = re.compile(r'src="https://cdnjs\.cloudflare\.com/[^"]*three\.min\.js"')
SVG_SRC = re.compile(r'src="\.\./hardware/([^"]+\.svg)"')
ANY_URL = re.compile(r"https?://")
SRC_OR_HREF = re.compile(r'(?:src|href)="([^"]*)"')


def read_text(path: Path) -> str:
    """Read a text file as UTF-8."""
    return path.read_text(encoding="utf-8")


def load_strings(lang: str) -> Dict[str, str]:
    """Load a language's string map (flat JSON)."""
    path = SITE_DIR / ("strings.%s.json" % lang)
    if not path.exists():
        raise SystemExit("ERROR: string file not found: %s" % path)
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise SystemExit("ERROR: %s must be the root object (flat JSON)." % path)
    return {str(k): str(v) for k, v in data.items()}


def collect_template_keys(template: str) -> List[str]:
    """Return all placeholder keys in the template (with repetitions)."""
    return PLACEHOLDER.findall(template)


def validate_strings(template: str, maps: Dict[str, Dict[str, str]]) -> None:
    """Key-set validation: looks for missing/extra/unused keys.

    Rules:
      * the two language files must have exactly the same key set;
      * every key used in the template must have a value in every language;
      * no key may remain unused.
    """
    langs = sorted(maps)
    key_sets = {lang: set(maps[lang]) for lang in langs}

    # 1) Key-set equality between the language files.
    base_lang = langs[0]
    for lang in langs[1:]:
        missing = sorted(key_sets[base_lang] - key_sets[lang])
        extra = sorted(key_sets[lang] - key_sets[base_lang])
        if missing or extra:
            parts = []
            if missing:
                parts.append("%s is missing: %s" % (lang, ", ".join(missing)))
            if extra:
                parts.append("%s has extra: %s" % (lang, ", ".join(extra)))
            raise SystemExit("ERROR: the language files' key sets differ — " + "; ".join(parts))

    used = set(collect_template_keys(template))
    if not used:
        raise SystemExit("ERROR: no placeholder was found in the template.")

    # 2) A key with no value (that cannot be filled in).
    for lang in langs:
        no_value = sorted(used - key_sets[lang])
        if no_value:
            raise SystemExit(
                "ERROR: the following keys in the template have no value in strings.%s.json: %s"
                % (lang, ", ".join(no_value))
            )

    # 3) An unused key.
    for lang in langs:
        unused = sorted(key_sets[lang] - used)
        if unused:
            raise SystemExit(
                "ERROR: key(s) in strings.%s.json not used in the template: %s"
                % (lang, ", ".join(unused))
            )


def fetch_three() -> bytes:
    """Read Three.js from the cache; if absent, download it once and write it to the cache.

    If there is no network and the cache is empty too, it stops with a clear error;
    it does not silently fall back to the CDN connection.
    """
    if THREE_CACHE.exists():
        return THREE_CACHE.read_bytes()
    try:
        request = urllib.request.Request(THREE_URL, headers={"User-Agent": "pocket-reader-build/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
    except Exception as exc:  # noqa: BLE001 - to give the user a clear message
        raise SystemExit(
            "ERROR: Three.js could not be downloaded and is not in the cache either.\n"
            "       %s\n"
            "       Please run once in an environment with an internet connection:\n"
            "           python3 tools/build_site.py\n"
            "       Cache path: %s\n"
            "       Detail: %s" % (THREE_URL, THREE_CACHE, exc)
        )
    if not data:
        raise SystemExit("ERROR: Three.js was downloaded but the content is empty.")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    THREE_CACHE.write_bytes(data)
    return data


def load_svg_payloads() -> Dict[str, bytes]:
    """Return the raw bytes of the SVGs to embed, keyed by relative path."""
    payloads: Dict[str, bytes] = {}
    for rel in SVG_FILES:
        path = ROOT / rel
        if not path.exists():
            raise SystemExit("ERROR: SVG not found: %s" % path)
        # The reference in the template is "../hardware/<rel>"; the key must be rel.
        payloads[rel.split("hardware/", 1)[-1]] = path.read_bytes()
    return payloads


def to_data_uri(mime: str, data: bytes) -> str:
    """Turn bytes into a base64 `data:` URI."""
    return "data:%s;base64,%s" % (mime, base64.b64encode(data).decode("ascii"))


def render(template: str, mapping: Dict[str, str]) -> str:
    """Fill the {{key}} placeholders in the template with the values."""
    return PLACEHOLDER.sub(lambda match: mapping[match.group(1)], template)


def inline_assets(html: str, three_uri: str, svg_uris: Dict[str, str]) -> str:
    """Turn the Three.js <script> source and the SVG <img> sources into data: URIs."""
    html, count = SCRIPT_SRC.subn(lambda _m: 'src="%s"' % three_uri, html)
    if count == 0:
        raise SystemExit("ERROR: no three.js <script src> tag was found in the template.")

    def replace_svg(match: re.Match[str]) -> str:
        rel = match.group(1)
        if rel not in svg_uris:
            raise SystemExit("ERROR: SVG reference in the template that is not embedded: %s" % rel)
        return 'src="%s"' % svg_uris[rel]

    html, count = SVG_SRC.subn(replace_svg, html)
    if count == 0:
        raise SystemExit("ERROR: no SVG <img src> reference was found in the template.")
    return html


def assert_structure(template: str, html_by_lang: Dict[str, str], maps: Dict[str, Dict[str, str]]) -> None:
    """Verify that each output is the template with only its placeholders filled
    in. Thus the two outputs are identical apart from the text substitutions.
    """
    parts = PLACEHOLDER.split(template)
    keys = parts[1::2]
    literals = parts[0::2]

    for lang, html in html_by_lang.items():
        pos = 0
        got: List[str] = []
        for i, literal in enumerate(literals):
            if html[pos:pos + len(literal)] != literal:
                raise SystemExit(
                    "ERROR: the %s output does not have the same structure as the template (literal text #%d)." % (lang, i)
                )
            pos += len(literal)
            if i < len(keys):
                nxt = literals[i + 1]
                j = html.find(nxt, pos) if nxt else pos
                if j < 0:
                    raise SystemExit(
                        "ERROR: in the %s output the literal text expected after the %s key is missing."
                        % (lang, keys[i])
                    )
                got.append(html[pos:j])
                pos = j
        if pos != len(html):
            raise SystemExit("ERROR: the %s output has leftover data not from the template." % lang)
        expected = [maps[lang][key] for key in keys]
        if got != expected:
            for index, (a, b) in enumerate(zip(got, expected)):
                if a != b:
                    raise SystemExit(
                        "ERROR: in the %s output the value of '%s' differs from the expected one." % (lang, keys[index])
                    )
            raise SystemExit("ERROR: the number of values in the %s output does not match." % lang)


def verify_self_contained(html: str, lang: str) -> None:
    """Verify that the output is a single file: no external URL and no sibling file."""
    match = ANY_URL.search(html)
    if match:
        ctx = html[max(0, match.start() - 40):match.start() + 40]
        raise SystemExit("ERROR: the %s output has an external URL other than base64: ...%s..." % (lang, ctx))
    for match in SRC_OR_HREF.finditer(html):
        value = match.group(1)
        if value.startswith("data:") or value.startswith("#"):
            continue
        raise SystemExit("ERROR: the %s output has a sibling file reference: %s" % (lang, value))
    if PLACEHOLDER.search(html):
        raise SystemExit("ERROR: the %s output still has an unfilled {{...}} placeholder." % lang)


def build_outputs(template: str, maps: Dict[str, Dict[str, str]], langs: Tuple[str, ...]) -> Dict[str, str]:
    """Produce the full output texts for the requested languages.

    First the template is filled in (the structure validation runs on that state),
    then the assets — with the same bytes in every language — are embedded.
    """
    rendered = {lang: render(template, maps[lang]) for lang in langs}
    assert_structure(template, rendered, {lang: maps[lang] for lang in langs})

    three_uri = to_data_uri("text/javascript", fetch_three())
    svg_uris = {rel: to_data_uri("image/svg+xml", data) for rel, data in load_svg_payloads().items()}
    return {lang: inline_assets(rendered[lang], three_uri, svg_uris) for lang in langs}


def size_kb(text: str) -> float:
    """Return the UTF-8 size of the text in KB."""
    return len(text.encode("utf-8")) / 1024.0


def run_build(langs: Tuple[str, ...]) -> int:
    """Produce the outputs, verify them and write them to disk."""
    template = read_text(TEMPLATE_PATH)
    maps = {lang: load_strings(lang) for lang in ALL_LANGS}
    validate_strings(template, maps)

    outputs = build_outputs(template, maps, langs)
    for lang in langs:
        verify_self_contained(outputs[lang], lang)

    for lang in langs:
        path = SITE_DIR / OUTPUTS[lang]
        path.write_text(outputs[lang], encoding="utf-8")
        print("wrote: %-22s %8.1f KB  (lang: %s)" % (path.name, size_kb(outputs[lang]), lang))
    return 0


def run_check() -> int:
    """Does not build; runs key validation + comparison with the files on disk."""
    template = read_text(TEMPLATE_PATH)
    maps = {lang: load_strings(lang) for lang in ALL_LANGS}
    validate_strings(template, maps)

    outputs = build_outputs(template, maps, ALL_LANGS)
    for lang in ALL_LANGS:
        verify_self_contained(outputs[lang], lang)

    problems: List[str] = []
    for lang in ALL_LANGS:
        path = SITE_DIR / OUTPUTS[lang]
        if not path.exists():
            problems.append("%s is missing (not built)." % path.name)
            continue
        on_disk = read_text(path)
        if on_disk != outputs[lang]:
            problems.append("%s is stale (does not match a rebuild)." % path.name)
    if problems:
        raise SystemExit(
            "ERROR: --check failed:\n  - " + "\n  - ".join(problems)
            + "\nFix: python3 tools/build_site.py"
        )

    print("--check: OK. %d keys, %d languages, outputs up to date."
          % (len(next(iter(maps.values()))), len(ALL_LANGS)))
    for lang in ALL_LANGS:
        print("  %-16s %8.1f KB" % (OUTPUTS[lang], size_kb(outputs[lang])))
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Produce single-file site outputs from the site/template.html template."
    )
    parser.add_argument(
        "--lang", choices=list(ALL_LANGS), default=None,
        help="produce only this language (default: both).",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="do not build; verify the key set and the outputs on disk.",
    )
    args = parser.parse_args(argv)

    if args.check:
        if args.lang:
            raise SystemExit("ERROR: --check and --lang cannot be used together.")
        return run_check()

    langs: Tuple[str, ...] = (args.lang,) if args.lang else ALL_LANGS
    return run_build(langs)


if __name__ == "__main__":
    sys.exit(main())
