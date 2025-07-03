"""Goodreads RSS → Firebase sync

▸ Runs as a Vercel Python Serverless Function (handler class expected)
▸ Called hourly by GitHub Actions (curl) or manually via HTTP GET/POST.
▸ For each RSS entry it *upserts* a record in `/books/<goodreads_id>`:
    • Inserts new books.
    • Promotes existing `TBR` → `Finished` and refreshes metadata.
    • Sets `reflection_pending = True` so Shelf Help can prompt the user.
▸ Adds/updates an ISO `updated_at` timestamp for auditing.
"""

from http.server import BaseHTTPRequestHandler
import json
import logging
import os
from datetime import datetime, timezone

import feedparser
import firebase_admin
from firebase_admin import credentials, db
from utils.dates import to_yyyy_mm_dd

# ───────────────────── Logging ──────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ───────────────── Firebase bootstrap ───────────────

def _init_firebase():
    """Initialise the default Firebase app once per cold‑start."""
    if firebase_admin._apps:
        return  # already initialised

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
    logger.info("Firebase initialised ✅")


# ───────────────── RSS helpers ──────────────────────

RSS_URL = (
    "https://www.goodreads.com/review/list_rss/175732651?"
    "key=pieaUmxpwAFnXedFdGNPvOcgxfZ_Eme21zt09hpH0zzCVl7s&shelf=read"
)


def _parse_series(full_title: str):
    """Extract series name & number from titles like 'Book (Series, #2)'."""
    base_parts = full_title.split(" (")
    book_title = base_parts[0].strip()
    series_name = None
    series_number = None
    if len(base_parts) > 1 and "#" in base_parts[1]:
        series_info = base_parts[1].rstrip(")")
        # e.g. "Series Name, #3"
        if ", #" in series_info:
            series_name, number = series_info.split(", #", 1)
            series_name = series_name.strip()
            series_number = number.strip()
    return book_title, series_name, series_number


# ─────────────── Goodreads → Firebase upsert ─────────

def _upsert_entry(entry):
    book_id = entry.get("book_id") or entry.id.rsplit("/", 1)[-1]
    full_title = entry.title
    book_title, series_name, series_number = _parse_series(full_title)

    # Build a complete data object
    book_data = {
        "goodreads_id": book_id,
        "guid": entry.get("guid", ""),
        "pubdate": entry.get("published", ""),
        "title": full_title,
        "book_title": book_title,
        "series_name": series_name,
        "series_number": series_number,
        "link": entry.get("link", ""),
        "book_image_url": entry.get("book_image_url", ""),
        "book_small_image_url": entry.get("book_small_image_url", ""),
        "book_medium_image_url": entry.get("book_medium_image_url", ""),
        "book_large_image_url": entry.get("book_large_image_url", ""),
        "book_description": entry.get("book_description", ""),
        "author_name": entry.get("author_name", ""),
        "isbn": entry.get("isbn", ""),
        "user_name": entry.get("user_name", ""),
        "user_rating": entry.get("user_rating", ""),
        "user_read_at": to_yyyy_mm_dd(entry.get("user_read_at")),
        "user_date_added": to_yyyy_mm_dd(entry.get("user_date_added")),
        "user_date_created": to_yyyy_mm_dd(entry.get("user_date_created")),
        "user_shelves": entry.get("user_shelves", ""),
        "user_review": entry.get("user_review", ""),
        "average_rating": entry.get("average_rating", ""),
        "book_published": entry.get("book_published", ""),
        "description_html": entry.get("description", ""),
        # ‑‑ Derived / sync fields ‑‑
        "status": "Finished",  # Always finished in the read‑shelf feed
        "reflection_pending": True,
        "updated_at": datetime.utcnow().date().isoformat(),
    }

    # Derive goal_year from user_read_at (if present)
    if book_data.get("user_read_at"):
        book_data["goal_year"] = int(book_data["user_read_at"][:4])

    ref = db.reference(f"/books/{book_id}")
    existing = ref.get()

    if existing:
        # Prepare a diff‑only update dict to avoid overwriting user edits
        update_data = {k: v for k, v in book_data.items() if existing.get(k) != v and v}
        # If user_read_at changed or goal_year missing, patch goal_year
        if "user_read_at" in update_data or ("goal_year" not in existing and book_data.get("goal_year")):
            update_data["goal_year"] = book_data["goal_year"]
        if update_data:
            ref.update(update_data)
            logger.info("Updated existing book %s (%s) → %s fields", book_title, book_id, len(update_data))
            return "updated"
        logger.debug("No changes for %s (%s)", book_title, book_id)
        return "unchanged"

    # Insert new book
    ref.set(book_data)
    logger.info("Added new book %s (%s)", book_title, book_id)
    return "inserted"


# ────────────────── HTTP handler ────────────────────

class handler(BaseHTTPRequestHandler):
    """Vercel entry‑point (maps GET and POST to the same logic)."""

    def _run(self):
        _init_firebase()
        feed = feedparser.parse(RSS_URL)
        logger.info("Fetched %d Goodreads entries", len(feed.entries))

        counts = {"inserted": 0, "updated": 0, "unchanged": 0}
        for entry in feed.entries:
            try:
                result = _upsert_entry(entry)
                counts[result] += 1
            except Exception as entry_err:  # noqa: BLE001
                logger.exception("Failed processing entry: %s", getattr(entry, "title", "<unknown>"))

        # Respond JSON
        payload = {"status": "success", **counts}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    # GitHub Action uses GET; Curl/others might POST — support both
    def do_GET(self):  # noqa: N802
        try:
            self._run()
        except Exception as err:  # noqa: BLE001
            logger.exception("sync_rss fatal error")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(err)}).encode())

    def do_POST(self):  # noqa: N802
        self.do_GET()  # Delegate to GET logic for simplicity
