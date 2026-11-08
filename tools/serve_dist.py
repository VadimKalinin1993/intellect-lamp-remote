#!/usr/bin/env python3
"""Serve dist/ to the lamp's Settings -> Software, as if it were GitHub (for testing the phone update).

    python3 tools/serve_dist.py            serves dist/ and lang/ on this computer's Wi-Fi address
    python3 tools/serve_dist.py --test     first builds a copy that differs only in its version, so a
                                           lamp that already has dist/ sees an update
    python3 tools/serve_dist.py --port N   another port (default 8800)

Then open on the phone: http://LAMP-ADDRESS/setup.htm?updsrc=<printed address>, and Settings ->
Software -> Check for updates. The page remembers the address; http://LAMP-ADDRESS/setup.htm?updsrc=
goes back to GitHub. Only dist/ and lang/ are served (read only), with the CORS header browsers need.
"""
import argparse, functools, pathlib, socket, subprocess, sys, tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Handler(SimpleHTTPRequestHandler):
    dist = ROOT / "dist"

    def translate_path(self, path):
        path = path.split("?", 1)[0].split("#", 1)[0]
        for prefix, base in (("/dist/", self.dist), ("/lang/", ROOT / "lang")):
            if path.startswith(prefix):
                name = path[len(prefix):]
                if name and "/" not in name and not name.startswith("."):
                    return str(base / name)
        return str(ROOT / "nonexistent")

    def list_directory(self, path):
        self.send_error(404)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))   # picks the Wi-Fi interface; nothing is sent
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    ap = argparse.ArgumentParser(description="Serve dist/ as an update source for Settings -> Software.")
    ap.add_argument("--port", type=int, default=8800)
    ap.add_argument("--test", action="store_true", help="serve a build that differs only in its version")
    ap.add_argument("--bind", default="0.0.0.0", help="address to listen on (default: all)")
    args = ap.parse_args()
    if args.test:
        out = pathlib.Path(tempfile.mkdtemp(prefix="lamp-dist-"))
        subprocess.run([sys.executable, str(ROOT / "tools" / "build.py"), "--out", str(out), "--salt", "test"], check=True)
        Handler.dist = out
    if not (Handler.dist / "version.json").is_file():
        print(f"No {Handler.dist / 'version.json'}. Run: python3 tools/build.py")
        return 2
    try:
        server = ThreadingHTTPServer((args.bind, args.port), Handler)
    except OSError as e:
        print(f"Can't listen on port {args.port} ({e.strerror}). Try another: --port 8810")
        return 1
    host = lan_ip() if args.bind == "0.0.0.0" else args.bind
    url = f"http://{host}:{args.port}/dist/"
    print(f"Serving {Handler.dist} as {url}  (lang/ next to it)")
    print(f"On the phone: http://LAMP-ADDRESS/setup.htm?updsrc={url}")
    print("Afterwards:   http://LAMP-ADDRESS/setup.htm?updsrc=   (back to GitHub)")
    print("Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(main())
