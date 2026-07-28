#!/usr/bin/env python3
import argparse
import base64
import json
import mimetypes
import runpy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

from bovbel_site.sites import SITES_BY_NAME, build_site


def lambda_event(method, body=None):
    event = {"requestContext": {"http": {"method": method}}}
    if body is not None:
        event["body"] = body
        event["isBase64Encoded"] = False
    return event


def serve_site(site, host, port):
    build_site(site)
    output_dir = site.output_dir.resolve()
    lambda_routes = {
        f"/{config.path_pattern}": runpy.run_path(
            str(config.asset_path / f"{config.handler.rsplit('.', 1)[0].replace('.', '/')}.py")
        )[config.handler.rsplit(".", 1)[1]]
        for config in site.lambda_functions
    }

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.handle_request()

        def do_HEAD(self):
            self.handle_request()

        def do_POST(self):
            self.handle_request()

        def handle_request(self):
            path = unquote(self.path.split("?", 1)[0])
            if path in lambda_routes:
                length = int(self.headers.get("content-length", "0"))
                body = self.rfile.read(length).decode() if length else None
                self.send_lambda(lambda_routes[path](lambda_event(self.command, body), None))
                return

            if self.command not in {"GET", "HEAD"}:
                self.send_json(404, {"error": "Not found"})
                return

            self.send_static()

        def send_static(self):
            path = unquote(self.path.split("?", 1)[0]).lstrip("/")
            file_path = (output_dir / path).resolve() if path else output_dir / "index.html"
            if file_path.is_dir():
                file_path = file_path / "index.html"
            status_code = 200
            if not file_path.is_relative_to(output_dir) or not file_path.exists():
                file_path = output_dir / "404.html"
                status_code = 404

            content = file_path.read_bytes()
            content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
            self.send_response(status_code)
            self.send_header("content-type", content_type)
            self.send_header("content-length", str(len(content)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(content)

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

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Serving {site.name} site at http://{host}:{port}")
    if lambda_routes:
        print("Local Lambda routes: " + ", ".join(sorted(lambda_routes)))
    server.serve_forever()


def site_arg(parser):
    parser.add_argument(
        "--site",
        choices=sorted(SITES_BY_NAME),
        default="paul",
        help="Static site to build or serve",
    )


def serve_main():
    parser = argparse.ArgumentParser(description="Build and serve a static site locally")
    site_arg(parser)
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    args = parser.parse_args()

    serve_site(SITES_BY_NAME[args.site], args.host, args.port)


if __name__ == "__main__":
    serve_main()
