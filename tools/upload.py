#!/usr/bin/env python3
"""Upload the remote from dist/ to a lamp in one command (Python standard library only).

    python3 tools/upload.py LAMP-ADDRESS                 setup.htm, app.htm and icon.png (and index.htm
                                                         if the lamp already has one)
    python3 tools/upload.py LAMP-ADDRESS --with-index    first install of index.htm (/ opens the remote)
    python3 tools/upload.py LAMP-ADDRESS --remove-index  delete index.htm (/ shows the stock WLED page)

The computer has to be on the same Wi-Fi as the lamp. It does the same thing as uploading the files
by hand through http://LAMP-ADDRESS/edit, carefully:
  - one request at a time with a short pause (the ESP8266 stalls on parallel requests);
  - every file is read back and compared byte for byte, and uploaded again (up to 3 tries) if it
    differs (an upload can occasionally leave an empty file);
  - setup.htm goes first and app.htm after it, so a working page exists if something fails midway;
  - leftovers of an older layout (app.htm.gz, setup.htm.gz) are removed, because the lamp would
    serve them instead of the new files;
  - free space on the lamp is checked before anything is written, and again before each file: when
    there is less room than the new file needs, the old copy is deleted first (LittleFS may need room
    for the new copy before it frees the old one, so an overwrite could fail).
Running it again is always safe: it uploads the same files and checks them again.
"""
import argparse, json, math, pathlib, sys, time, urllib.error, urllib.parse, urllib.request, uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
PAGES = ["setup.htm", "app.htm", "icon.png"]   # order matters: setup.htm first, app.htm after it
LEFTOVERS = ["app.htm.gz", "setup.htm.gz"]
BLOCK = 4096          # the lamp's flash drive stores files in 4 KB blocks
PAUSE = 1.0           # seconds between requests
TRIES = 3


class Lamp:
    def __init__(self, host, timeout=60):
        host = host.strip()
        if "://" not in host:
            host = "http://" + host
        self.base = host.rstrip("/")
        self.timeout = timeout
        self._last = 0.0

    def request(self, method, path, body=None, headers=None):
        wait = self._last + PAUSE - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(self.base + path, data=body, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
        finally:
            self._last = time.monotonic()

    def json(self, path):
        status, body = self.request("GET", path)
        if status != 200:
            raise RuntimeError(f"GET {path} answered {status}")
        return json.loads(body.decode("utf-8", "replace"))

    def files(self):
        """{name without leading slash: size} of the files on the lamp."""
        return {str(f.get("name", "")).lstrip("/"): int(f.get("size", 0)) for f in self.json("/edit?list=/")}

    def upload(self, name, data):
        boundary = "----lamp" + uuid.uuid4().hex
        body = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="data"; filename="/{name}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
        return self.request("POST", "/upload", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})

    def download(self, name):
        return self.request("GET", "/" + urllib.parse.quote(name))

    def delete(self, name):
        body = urllib.parse.urlencode({"path": "/" + name}).encode()
        return self.request("DELETE", "/edit", body, {"Content-Type": "application/x-www-form-urlencoded"})


def blocks_kb(size):
    return math.ceil(size / BLOCK) * BLOCK // 1024


def tight(lamp, name, data, on_lamp):
    """True if the lamp has too little free space to overwrite `name` in place."""
    if name not in on_lamp:
        return False
    fs = lamp.json("/json/info").get("fs") or {}
    if "u" not in fs or "t" not in fs:
        return False
    return int(fs["t"]) - int(fs["u"]) < blocks_kb(len(data)) + BLOCK // 1024


def put(lamp, name, data, on_lamp):
    """Upload one file, read it back, retry if it differs. Returns (ok, message)."""
    why, first = "", ""
    for attempt in range(1, TRIES + 1):
        try:
            if tight(lamp, name, data, on_lamp):
                status, _ = lamp.delete(name)
                if status == 200:
                    on_lamp.pop(name, None)
                    first = ", old copy removed first for space"
            on_lamp[name] = len(data)   # from here on a (maybe partial) copy is on the lamp
            status, _ = lamp.upload(name, data)
            if status != 200:
                why = f"upload answered {status}"
                continue
            status, back = lamp.download(name)
            if status != 200:
                why = f"reading it back answered {status}"
            elif back != data:
                why = f"read back {len(back):,} bytes instead of {len(data):,}"
            else:
                tries = "" if attempt == 1 else f" (attempt {attempt})"
                return True, f"{name:<10} {len(data):>7,} bytes  uploaded and verified{tries}{first}"
        except (OSError, urllib.error.URLError, ValueError, RuntimeError) as e:
            why = f"no answer ({e})"
    return False, f"{name:<10} FAILED after {TRIES} tries: {why}"


def remove(lamp, name):
    try:
        status, _ = lamp.delete(name)
    except (OSError, urllib.error.URLError) as e:
        return False, f"{name:<10} could not be removed: no answer ({e})"
    if status != 200:
        return False, f"{name:<10} could not be removed: the lamp answered {status}"
    return True, f"{name:<10} removed"


def main():
    ap = argparse.ArgumentParser(
        description="Upload the remote from dist/ to a WLED lamp (same as uploading through /edit by hand).")
    ap.add_argument("lamp", metavar="LAMP-ADDRESS", help="the lamp's address, e.g. 192.168.1.133")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--with-index", action="store_true",
                   help="also upload index.htm, so / opens the remote (only needed the first time: "
                        "an index.htm already on the lamp is updated anyway)")
    g.add_argument("--remove-index", action="store_true", help="delete index.htm, so / shows the stock WLED page")
    ap.add_argument("--force", action="store_true", help="upload even if the files look too big for the free space")
    args = ap.parse_args()

    names = list(PAGES)
    if not DIST.is_dir():
        print(f"No {DIST} folder. Download the repository again, or run: python3 tools/build.py")
        return 2
    missing = [n for n in names if not (DIST / n).is_file()]
    if missing:
        print(f"Missing in {DIST}: {', '.join(missing)}. Run: python3 tools/build.py")
        return 2

    lamp = Lamp(args.lamp)
    try:
        info = lamp.json("/json/info")
        on_lamp = lamp.files()
    except (OSError, urllib.error.URLError, ValueError, RuntimeError) as e:
        print(f"Can't reach a WLED lamp at {lamp.base}: {e}")
        print("Check the address and that this computer is on the same Wi-Fi as the lamp.")
        return 1
    print(f"{info.get('name', 'Lamp').strip() or 'Lamp'} at {lamp.base}, WLED {info.get('ver', '?')}")

    if args.with_index or ("index.htm" in on_lamp and not args.remove_index):
        if not (DIST / "index.htm").is_file():
            print(f"Missing in {DIST}: index.htm. Run: python3 tools/build.py")
            return 2
        if not args.with_index:
            print("index.htm  is on the lamp, so it gets updated too")
        names.append("index.htm")   # last: it sends visitors to app.htm / setup.htm, which exist by then
    data = {n: (DIST / n).read_bytes() for n in names}

    drop = [n for n in LEFTOVERS if n in on_lamp]
    if args.remove_index and "index.htm" in on_lamp:
        drop.append("index.htm")
    elif args.remove_index:
        print("index.htm  is not on the lamp, nothing to remove")

    fs = info.get("fs") or {}
    if "u" in fs and "t" in fs:
        free = int(fs["t"]) - int(fs["u"])
        need = sum(blocks_kb(len(d)) - (blocks_kb(on_lamp[n]) if n in on_lamp else 0) for n, d in data.items())
        need -= sum(blocks_kb(on_lamp[n]) for n in drop)
        print(f"Space: {free} KB free of {fs['t']} KB, these files need about {max(need, 0)} KB more")
        if need > free:
            print("Warning: the files probably won't fit. Remove a language you don't use "
                  "(Settings > Language) or other files through /edit, then try again.")
            if not args.force:
                print("Nothing was changed. Use --force to try anyway.")
                return 1
    else:
        print("Space: the lamp doesn't report its free space, skipping the check")

    ok = True
    for n in drop:   # first, so the lamp doesn't serve an old .gz instead of the new file
        good, msg = remove(lamp, n)
        print(msg)
        ok &= good
        if good:
            on_lamp.pop(n, None)
    for n in names:
        good, msg = put(lamp, n, data[n], on_lamp)
        print(msg)
        ok &= good
        if not good and n == "setup.htm":
            # a half-written setup.htm would open as an empty page; without it the Settings button
            # of the remote opens the stock WLED settings instead
            print(remove(lamp, n)[1])
            print("Stopped before app.htm, so the remote already on the lamp keeps working.")
            break

    print("Done: every file verified." if ok else "Something failed: see above. Running the command again is safe.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
