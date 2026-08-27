"""ローカルWeb：Amazon URL を貼って利益率 / 仕入上限を出す。"""

from __future__ import annotations

import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deca.service import research

HOST = "127.0.0.1"
PORT = 8765
STATIC = Path(__file__).resolve().parent / "static"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            html = (STATIC / "index.html").read_bytes()
            self._send(200, html, "text/html; charset=utf-8")
            return
        self._send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/research":
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send(400, json.dumps({"ok": False, "error": "JSONが読めない"}).encode(), "application/json; charset=utf-8")
            return

        def num(key):
            v = data.get(key)
            if v is None or v == "":
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        yuan = num("yuan")
        domestic = num("domestic")
        result = research(
            (data.get("url") or "").strip() or None,
            yuan=yuan,
            rate=num("rate") or 22.0,
            price=num("price"),
            length=num("length"),
            width=num("width"),
            height=num("height"),
            weight=num("weight"),
            domestic=int(domestic) if domestic is not None else None,
            keepa_length=num("keepa_length"),
            keepa_width=num("keepa_width"),
            keepa_height=num("keepa_height"),
            keepa_weight_kg=num("keepa_weight"),
        )
        body = json.dumps(result, ensure_ascii=False, default=str).encode("utf-8")
        self._send(200, body, "application/json; charset=utf-8")


def main(argv: list[str] | None = None) -> int:
    no_open = "--no-open" in (argv or sys.argv[1:])
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}/"
    print(f"開く: {url}", flush=True)
    if not no_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n停止")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
