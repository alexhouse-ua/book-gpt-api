"""Flexible book fetch endpoint used by Shelf Help

POST JSON payload allows simple field-equality filtering so GPT can retrieve:
  • Specific books by goodreads_id or title.
  • All books with status = "Finished" / "TBR", etc.
  • Pending reflections → {"reflection_pending": true}

Example curl:
    curl -X POST \
      -H "Content-Type: application/json" \
      -d '{"reflection_pending": true}' \
      https://book-gpt-api.vercel.app/api/fetch_books

Returns a JSON object: {"books": [ ... ]}
"""

from http.server import BaseHTTPRequestHandler
import json
import logging
import os
import io
from typing import Dict, Any, List

import firebase_admin
from firebase_admin import credentials, db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ───────────── Firebase bootstrap (shared) ──────────────

def _init_firebase():
    if firebase_admin._apps:
        return
    cred = credentials.Certificate(
        {
            "type": os.environ["FIREBASE_TYPE"],
            "project_id": os.environ["FIREBASE_PROJECT_ID"],
            "private_key_id": os.environ["FIREBASE_PRIVATE_KEY_ID"],
            "private_key": os.environ["FIREBASE_PRIVATE_KEY"].replace("\\n", "\n"),
            "client_email": os.environ["FIREBASE_CLIENT_EMAIL"],
            "client_id": os.environ["FIREBASE_CLIENT_ID"],
            "auth_uri": os.environ["FIREBASE_AUTH_URI"],
            "token_uri": os.environ["FIREBASE_TOKEN_URI"],
            "auth_provider_x509_cert_url": os.environ["FIREBASE_AUTH_PROVIDER_X509_CERT_URL"],
            "client_x509_cert_url": os.environ["FIREBASE_CLIENT_CERT_URL"],
        }
    )
    firebase_admin.initialize_app(cred, {"databaseURL": os.environ["FIREBASE_DB_URL"]})
    logger.info("Firebase initialised ✅ (fetch_books)")


# ────────────── Core filtering logic ───────────────────

ALLOWED_FIELDS = {
    "goodreads_id",
    "book_title",
    "title",
    "status",
    "reflection_pending",
}


def _matches(book: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    """Return True iff *all* provided filters match exactly (case-insensitive for strings)."""
    for k, v in filters.items():
        if k not in ALLOWED_FIELDS:
            continue  # ignore unsupported keys silently
        if v is None:
            continue
        actual = book.get(k)
        if isinstance(actual, str) and isinstance(v, str):
            if actual.lower() != str(v).lower():
                return False
        else:
            if actual != v:
                return False
    return True


def _filter_books(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    ref = db.reference("/books")
    all_books: Dict[str, Any] = ref.get() or {}
    return [bk for bk in all_books.values() if _matches(bk, filters)]


# ───────────────── HTTP handler ────────────────────────

class handler(BaseHTTPRequestHandler):
    """Vercel entry-point for /api/fetch_books"""

    def _run(self):
        _init_firebase()

        # Parse JSON body (empty → {})
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw_body.decode())
        except json.JSONDecodeError:
            body = {}

        filters: Dict[str, Any] = {k: body.get(k) for k in ALLOWED_FIELDS if k in body}
        results = _filter_books(filters)
        logger.info("fetch_books filters=%s → %d matches", filters, len(results))

        # Respond JSON object with books list (tests expect this wrapper)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"books": results}).encode())

    def do_POST(self):  # noqa: N802
        try:
            self._run()
        except Exception as err:  # noqa: BLE001
            logger.exception("fetch_books error")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(err)}).encode())

    # Allow GET with ?reflection_pending=true for quick dev checks
    def do_GET(self):  # noqa: N802
        from urllib.parse import parse_qs, urlparse

        qs = parse_qs(urlparse(self.path).query)
        filters = {}
        for k, v in qs.items():
            if k not in ALLOWED_FIELDS:
                continue
            val = v[0]
            if k == "reflection_pending":
                val = val.lower() == "true"
            filters[k] = val

        # Mimic POST by serialising into rfile
        payload = json.dumps(filters).encode()
        self.headers["Content-Length"] = str(len(payload))
        self.rfile = io.BytesIO(payload)  # type: ignore
        self.do_POST()