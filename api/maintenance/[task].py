"""
ONE Serverless Function that handles any path like
  /internal/backfill_empty_fields
  /internal/backfill_enrichment
  /internal/print_firebase_books
  /internal/ping
"""
import json, os, logging, importlib
from http.server import BaseHTTPRequestHandler

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "change-me")  # set in Vercel dashboard
logger = logging.getLogger(__name__)

def _resp(h: BaseHTTPRequestHandler, code: int, payload: dict):
    h.send_response(code)
    h.send_header("Content-Type", "application/json")
    h.end_headers()
    h.wfile.write(json.dumps(payload).encode())

def run_task(task: str, body: dict):
    mod = importlib.import_module("maintenance_tasks")
    fn = getattr(mod, task, None)
    if fn is None:
        raise ValueError(f"Unknown maintenance task '{task}'")
    return fn(body)

class handler(BaseHTTPRequestHandler):
    def _auth(self):
        return self.headers.get("X-Admin-Secret") == ADMIN_SECRET

    def _handle(self):
        if not self._auth():
            _resp(self, 401, {"error": "unauthorized"}); return

        task = self.path.rsplit("/", 1)[-1]
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or "{}")

        try:
            result = run_task(task, body)
            _resp(self, 200, {"status": "ok", "task": task, "result": result})
        except Exception as exc:
            logger.exception(exc)
            _resp(self, 500, {"status": "error", "message": str(exc)})

    def do_POST(self): self._handle()
    def do_GET(self):  self._handle()
