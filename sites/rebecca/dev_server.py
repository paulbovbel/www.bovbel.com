#!/usr/bin/env python3
import base64
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from bovbel_site.sites import SITES_BY_NAME, build_site
from sites.rebecca.api import catalog, checkout


SITE_DIR = Path(__file__).parent
BUILD_DIR = SITE_DIR / "build"
HOST = "127.0.0.1"
PORT = 8000


def lambda_event(method, body=None):
    event = {"requestContext": {"http": {"method": method}}}
    if body is not None:
        event["body"] = body
        event["isBase64Encoded"] = False
    return event


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/catalog":
            self.send_lambda(catalog.handler(lambda_event("GET"), None))
            return

        self.send_static()

    def do_POST(self):
        if self.path != "/api/checkout":
            self.send_json(404, {"error": "Not found"})
            return

        length = int(self.headers.get("content-length", "0"))
        body = self.rfile.read(length).decode() if length else ""
        self.send_lambda(checkout.handler(lambda_event("POST", body), None))

    def send_lambda(self, result):
        body = result.get("body", "")
        if result.get("isBase64Encoded"):
            body = base64.b64decode(body)
        elif isinstance(body, str):
            body = body.encode()

        self.send_response(result.get("statusCode", 200))
        for name, value in result.get("headers", {}).items():
            self.send_header(name, value)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status_code, body):
        payload = json.dumps(body).encode()
        self.send_response(status_code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_static(self):
        path = unquote(self.path.split("?", 1)[0]).lstrip("/")
        file_path = (BUILD_DIR / path).resolve() if path else BUILD_DIR / "index.html"
        if file_path.is_dir():
            file_path = file_path / "index.html"
        status_code = 200
        if not file_path.is_relative_to(BUILD_DIR.resolve()) or not file_path.exists():
            file_path = BUILD_DIR / "404.html"
            status_code = 404

        content = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        self.send_response(status_code)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")


def serve(host=HOST, port=PORT):
    build_site(SITES_BY_NAME["rebecca"])
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Serving Rebecca site at http://{host}:{port}")
    print("Set SQUARE_ACCESS_TOKEN for local /api/catalog and /api/checkout calls.")
    server.serve_forever()


def main():
    serve()


if __name__ == "__main__":
    main()
