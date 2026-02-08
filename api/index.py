# -*- coding: utf-8 -*-
"""Vercel serverless function - Zuup Forge status API."""
from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime, timezone


def _json_data(status, data):
    return (
        status,
        {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        data,
    )


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/api/health", "/health"):
            status, headers, data = _json_data(
                200, {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
            )
        elif path in ("/api/status", "/status"):
            status, headers, data = _json_data(
                200,
                {
                    "forge_version": "0.1.0",
                    "trl": 3,
                    "platforms_defined": 1,
                    "platforms_functional": 0,
                    "compiler_status": "operational",
                    "last_compile_test": "see CI badge",
                    "next_milestone": "Gate 1 - Technical Credibility",
                },
            )
        else:
            status, headers, data = _json_data(404, {"error": "not found"})
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass
