#!/usr/bin/env python3
"""Moli-Tutor 用ミニ HTTP サーバ（shell + 教材を同一オリジンで配信）。"""
from __future__ import annotations

import argparse
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


def _safe_child(root: Path, rel: str) -> Path | None:
    rel = rel.replace("\\", "/").lstrip("/")
    if ".." in rel.split("/"):
        return None
    target = (root / rel).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError:
        return None
    return target


def make_handler(static_root: Path, material_root: Path | None) -> type[BaseHTTPRequestHandler]:
    static_root = static_root.resolve()
    material_root = material_root.resolve() if material_root else None

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            return

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path or "/"
            if path in ("/", ""):
                path = "/shell.html"

            if material_root and path.startswith("/material/"):
                rel = unquote(path[len("/material/") :])
                file_path = _safe_child(material_root, rel)
            else:
                rel = unquote(path.lstrip("/"))
                file_path = _safe_child(static_root, rel)

            if not file_path or not file_path.is_file():
                self.send_error(404)
                return

            ctype = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
            data = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            if file_path.suffix.lower() in (".html", ".js", ".css"):
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                self.send_header("Pragma", "no-cache")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


def serve(
    static_root: Path,
    material_root: Path | None,
    host: str,
    port: int,
) -> ThreadingHTTPServer:
    handler = make_handler(static_root, material_root)
    server = ThreadingHTTPServer((host, port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Moli-Tutor HTTP server (standalone)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8777)
    parser.add_argument("--static", type=Path, required=True)
    parser.add_argument("--material", type=Path, default=None)
    args = parser.parse_args()
    server = serve(args.static.resolve(), args.material.resolve() if args.material else None, args.host, args.port)
    print(f"[moli-tutor] http://{args.host}:{args.port}/shell.html", flush=True)
    if args.material:
        print(f"[moli-tutor] material http://{args.host}:{args.port}/material/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
