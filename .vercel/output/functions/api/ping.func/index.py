import json
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def _resp(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode())
    do_GET  = _resp
    do_POST = _resp
