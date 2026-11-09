#!/usr/bin/env python3
"""Write lang/<code>.json from tools/translations.py and check every phrase against the pages.

    python3 tools/make_lang.py

Each entry in translations.py is (English, Russian, Ukrainian). The English side may use plain
- ' " and ... ; it is matched to the exact text in setup.htm and app.htm (non-breaking hyphens,
curly quotes, ellipsis), so the keys in lang/*.json are exactly what the pages show. {} stands
for a number or a name. Phrases that no longer exist in the pages are reported.
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from translations import T  # noqa: E402

LANGS = {"ru": ("Русский", 1), "uk": ("Українська", 2)}
SRC = "".join((ROOT / f).read_text() for f in ("setup.htm", "app.htm")).replace("&amp;", "&")
ALT = {"-": "[-‑−–]", "'": "['’]", '"': '["“”]'}


def pattern(s):
    out, i = "", 0
    while i < len(s):
        if s.startswith("...", i):
            out += "(?:\\.\\.\\.|…)"; i += 3; continue
        out += ALT.get(s[i], re.escape(s[i])); i += 1
    return out


def exact(s):
    m = re.search(pattern(s), SRC)
    return m.group(0) if m else None


def main():
    out = {c: {} for c in LANGS}
    missing = []
    for row in T:
        en = row[0]
        if len(row) > 3:
            key = en
        elif "{}" in en:
            parts = []
            for p in en.split("{}"):
                x = exact(p) if p.strip() else p
                if x is None:
                    missing.append(en); x = p
                parts.append(x)
            key = "{}".join(parts)
        else:
            key = exact(en)
            if key is None:
                missing.append(en); key = en
        for c, (_, col) in LANGS.items():
            out[c][key] = row[col]
    (ROOT / "lang").mkdir(exist_ok=True)
    for c, (name, _) in LANGS.items():
        path = ROOT / "lang" / f"{c}.json"
        path.write_text(json.dumps({"code": c, "name": name, "s": out[c]}, ensure_ascii=False, indent=1) + "\n")
        print(f"lang/{c}.json: {len(out[c])} phrases")
    for m in missing:
        print("not on any page:", m)


if __name__ == "__main__":
    main()
