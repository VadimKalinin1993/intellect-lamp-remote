#!/usr/bin/env python3
"""Shrink the pages so they fit on the lamp's small flash drive.

    python3 tools/build.py        -> dist/  (upload everything in it through http://LAMP-ADDRESS/edit)

The readable files in the repository root stay the source of truth, and each of them still works
on its own if uploaded. The lamp's flash drive is tiny (about 131 KB on an ESP8266, used in 4 KB
blocks), so dist/ holds the same pages, each still ONE file with the same name:
  the page minified (JavaScript through terser via npx, needs Node), gzipped and embedded as base85
  (like Ascii85, without ' \\ < so it sits safely in a script string; 25% overhead instead of base64's 33%)
  in a small loader that keeps the page's <head> (so Home Screen icons and titles work), unzips it in
  the browser and shows it. Updating a page = uploading that one file again, as before.
index.htm is optional: a tiny redirect so http://LAMP-ADDRESS/ opens the remote (and Settings when
the lamp runs its backup access point at 4.3.2.1). Without it the stock WLED page stays at /.
lang/xx.json -> lang/lang-xx.json.gz (committed; Settings -> Language downloads it from GitHub).
icon.png is committed already compressed and is copied unchanged, so the build needs no image tools.

Version: a short hash of the sources (app.htm, setup.htm, icon.png, lang/xx.json) plus the build date.
It replaces __VER__ / __DATE__ in both pages (the unbuilt sources show "dev") and goes into
dist/version.json with the size of every file. Settings -> Software reads version.json from GitHub to
offer updates; version.json itself is never uploaded to the lamp. The date only changes when the hash
does, so rebuilding unchanged sources gives the same files.

Shared scenes: Settings -> Smart home -> Siri offers the remote's scenes as commands. They are written
once, as SCENES in app.htm; the build copies that array into setup.htm's /*SCENES*/0 placeholder (the
unbuilt setup.htm reads it from app.htm next to it instead).

    python3 tools/build.py --out DIR --salt TEXT   a test build with a different version (see serve_dist.py)
"""
import argparse, datetime, gzip, hashlib, json, pathlib, re, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
PAGES = ["app.htm", "setup.htm"]
# pinned, so the same sources always give the same dist/ (a newer terser minifies a little differently)
TERSER = "terser@5.51.2"


def css(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s*([{};,>])\s*", r"\1", s)
    s = re.sub(r":\s+", ":", s)
    return s.replace(";}", "}").strip()


def js(s):
    out = subprocess.run(
        ["npx", "-y", TERSER, "--compress", "--mangle", "--ecma", "2020"],
        input=s, capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


def page(h):
    h = re.sub(r"<style>(.*?)</style>", lambda m: "<style>" + css(m.group(1)) + "</style>", h, flags=re.S)
    h = re.sub(r"<script>(.*?)</script>", lambda m: "<script>" + js(m.group(1)) + "</script>", h, flags=re.S)
    h = re.sub(r"<!--.*?-->", "", h, flags=re.S)
    h = re.sub(r">\s+<", "><", h)
    return h.strip() + "\n"


LOADER = """<!DOCTYPE html><html lang="en"><head>{head}<meta name="version" content="{ver}"><style>html{{background:#16131d}}</style></head><body><script>{inflate}
window.gunzip=b=>{{const u=new Uint8Array(b),n=u.length,o=new Uint8Array((u[n-4]|u[n-3]<<8|u[n-2]<<16|u[n-1]<<24)>>>0);let p=10;const f=u[3];if(f&4)p+=2+(u[10]|u[11]<<8);if(f&8)while(u[p++]);if(f&16)while(u[p++]);if(f&2)p+=2;tinf(u.subarray(p,n-8),o);return o}};
window.b85=s=>{{const m=[],n=s.length,o=new Uint8Array(n*4/5|0);let c=33,p=0;for(let k=0;k<85;c++)if(c!=39&&c!=60&&c!=92)m[c]=k++;for(let i=0;i<n;i+=5){{let v=0;for(let j=0;j<5;j++)v=v*85+(i+j<n?m[s.charCodeAt(i+j)]:84);for(let j=0;j<4&&p<o.length;j++)o[p++]=v>>>24-8*j&255}}return o}};
{{const h=new TextDecoder().decode(gunzip(b85('{payload}')));document.open();document.write(h);document.close()}}
</script></body></html>
"""


INDEX = """<!DOCTYPE html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><script>location.replace((location.hostname=='4.3.2.1'?'setup':'app')+'.htm'+location.search)</script>
"""


B85 = [chr(c) for c in range(33, 127) if chr(c) not in "'<\\"][:85]


def b85(data):
    """4 bytes -> 5 characters; a last group of n bytes -> n+1 characters (decoded in LOADER)."""
    out = []
    for i in range(0, len(data), 4):
        g = data[i:i + 4]
        v = int.from_bytes(g.ljust(4, b"\0"), "big")
        d = []
        for _ in range(5):
            v, r = divmod(v, 85)
            d.append(B85[r])
        out.append("".join(reversed(d))[:len(g) + 1])
    return "".join(out)


def loader(src_html, payload, inflate, ver):
    head = re.search(r"<head>(.*?)<style>", src_html, flags=re.S).group(1)
    head = re.sub(r">\s+<", "><", head.strip())
    return LOADER.format(head=head, inflate=inflate, payload=payload, ver=ver)


def scenes():
    """app.htm's SCENES array, as written there (setup.htm gets the same list)."""
    m = re.search(r"const SCENES = (\[.*?\n\]);", (ROOT / "app.htm").read_text(), flags=re.S)
    if not m:
        sys.exit("app.htm: no `const SCENES = [ ... ];` to share with setup.htm")
    return m.group(1)


def version(dist, salt):
    """(hash, date): the hash of the sources, and the date it first appeared (kept from version.json)."""
    h = hashlib.sha256(salt.encode())
    srcs = [ROOT / n for n in PAGES + ["icon.png"]] + sorted((ROOT / "lang").glob("[a-z][a-z].json"))
    for f in srcs:
        h.update(f.name.encode() + b"\0" + f.read_bytes() + b"\0")
    v = h.hexdigest()[:8]
    try:
        old = json.loads((dist / "version.json").read_text())
        if old.get("v") == v and old.get("date"):
            return v, old["date"]
    except (OSError, ValueError):
        pass
    return v, datetime.date.today().isoformat()


def main():
    ap = argparse.ArgumentParser(description="Build dist/ from the readable sources.")
    ap.add_argument("--out", default=str(DIST), help="output folder (default: dist)")
    ap.add_argument("--salt", default="", help="mix TEXT into the version: a test build that differs only in version")
    args = ap.parse_args()
    dist = pathlib.Path(args.out).resolve()
    dist.mkdir(parents=True, exist_ok=True)
    ver, date = version(dist, args.salt)
    for old in dist.iterdir():
        old.unlink()
    inflate = js((ROOT / "tools" / "vendor" / "tiny-inflate.js").read_text())
    inflate = "/*tiny-inflate MIT (c) Devon Govett*/" + inflate
    for name in PAGES:
        src = ROOT / name
        text = src.read_text()
        if "__VER__" not in text or "__DATE__" not in text:
            sys.exit(f"{name}: no __VER__ / __DATE__ placeholder")
        text = text.replace("__VER__", ver).replace("__DATE__", date)
        if name == "setup.htm":
            if "/*SCENES*/0" not in text:
                sys.exit("setup.htm: no /*SCENES*/0 placeholder")
            text = text.replace("/*SCENES*/0", scenes())
        full = page(text).encode()
        gz = gzip.compress(full, 9, mtime=0)
        shell = loader(text, b85(gz), inflate, ver)
        (dist / name).write_text(shell)
        print(f"{name}: {src.stat().st_size:,} bytes -> dist/{name} {len(shell.encode()):,} (gzip {len(gz):,} inside)")
    (dist / "index.htm").write_text(INDEX)
    icon = dist / "icon.png"
    shutil.copy(ROOT / "icon.png", icon)
    print(f"icon.png: {(ROOT / 'icon.png').stat().st_size:,} -> {icon.stat().st_size:,} bytes")
    # language files: lang/xx.json -> lang/lang-xx.json.gz (committed: Settings -> Language downloads it)
    for src in sorted((ROOT / "lang").glob("[a-z][a-z].json")):
        data = json.dumps(json.loads(src.read_text()), ensure_ascii=False, separators=(",", ":")).encode()
        gz = ROOT / "lang" / f"lang-{src.stem}.json.gz"
        gz.write_bytes(gzip.compress(data, 9, mtime=0))
        print(f"{gz.name}: {len(data):,} -> {gz.stat().st_size:,} bytes")
    # version.json: what Settings -> Software compares with (only on GitHub, never on the lamp)
    files = {f.name: f.stat().st_size for f in sorted(dist.iterdir())}
    files.update({f.name: f.stat().st_size for f in sorted((ROOT / "lang").glob("lang-*.json.gz"))})
    (dist / "version.json").write_text(json.dumps({"v": ver, "date": date, "files": files}, indent=1) + "\n")
    print(f"version.json: {ver} ({date})")


if __name__ == "__main__":
    sys.exit(main())
