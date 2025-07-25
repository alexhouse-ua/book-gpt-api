from http.server import BaseHTTPRequestHandler
import json
import os
import firebase_admin
from firebase_admin import credentials, db
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Firebase initialization (only if not already initialized)
if not firebase_admin._apps:
    cred = credentials.Certificate({
        "type": os.environ["FIREBASE_TYPE"],
        "project_id": os.environ["FIREBASE_PROJECT_ID"],
        "private_key_id": os.environ["FIREBASE_PRIVATE_KEY_ID"],
        "private_key": os.environ["FIREBASE_PRIVATE_KEY"].replace("\\n", "\n"),
        "client_email": os.environ["FIREBASE_CLIENT_EMAIL"],
        "client_id": os.environ["FIREBASE_CLIENT_ID"],
        "auth_uri": os.environ["FIREBASE_AUTH_URI"],
        "token_uri": os.environ["FIREBASE_TOKEN_URI"],
        "auth_provider_x509_cert_url": os.environ["FIREBASE_AUTH_PROVIDER_X509_CERT_URL"],
        "client_x509_cert_url": os.environ["FIREBASE_CLIENT_CERT_URL"]
    })
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.environ["FIREBASE_DB_URL"]
    })

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        logger.info("add_book called with body: %s", body.decode("utf-8"))
        try:
            data = json.loads(body)
            # Validate required fields
            required_fields = ["goodreads_id", "title", "author_name", "status"]
            for field in required_fields:
                if not data.get(field):
                    raise ValueError(f"Missing required field: '{field}'")
            book_id = data.get("goodreads_id")

            if not book_id:
                raise ValueError("Missing 'goodreads_id'")

            logger.info("Checking existence of book_id: %s", book_id)
            ref = db.reference(f"/books/{book_id}")
            if ref.get():
                self.send_response(409)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Book already exists."}).encode())
                return

            logger.info("Writing new book record to Firebase.")
            # Initialize all expected fields to empty string if missing
            default_fields = [
                "tone", "trope", "flavor", "hype_flag",
                "availability_source",
                "library_hold_status_tuscaloosa_ebook", "library_hold_status_tuscaloosa_audio",
                "library_hold_status_camellia_ebook", "library_hold_status_camellia_audio",
                "library_hold_status_seattle_ebook", "library_hold_status_seattle_audio",
                "hoopla_ebook_available", "hoopla_audio_available",
                "ku_availability",
                "liked", "disliked",
                "rating_scale_tag", "inferred_score",
                "next_release_date", "goal_year",
                "extras", "queue_position"
            ]
            for field in default_fields:
                if field not in data:
                    data[field] = ""
            # ── Derive reflection_pending flag ──
            need_reflection = (
                data.get("status") == "Finished"
                and any(not data.get(fld) for fld in ("liked", "disliked", "extras", "notes"))
            )
            data["reflection_pending"] = need_reflection
            ref.set(data)
            logger.info("Book %s added successfully with fields:\n%s", book_id, json.dumps(data, indent=2))

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "Book added.", "book_id": book_id}).encode())
        except Exception as e:
            logger.exception("Error in add_book:")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())