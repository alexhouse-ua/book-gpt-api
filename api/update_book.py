from http.server import BaseHTTPRequestHandler
import json
import firebase_admin
from firebase_admin import credentials, db
import os
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from .utils.dates import to_yyyy_mm_dd

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        logger.info("update_book: Received request with headers: %s", dict(self.headers))
        try:
            # Initialize Firebase
            logger.info("update_book: Initializing Firebase app")
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

            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body)
            logger.info("update_book: Raw body: %s", body.decode("utf-8"))
            logger.info("update_book: Parsed data: %s", data)

            book_id = data.get("goodreads_id")
            updates = data.get("updates")

            # Normalise date fields in updates
            for fld in ("updated_at", "user_date_added", "user_date_created"):
                if fld in updates:
                    updates[fld] = to_yyyy_mm_dd(updates[fld])
            if "user_read_at" in updates:
                clean = to_yyyy_mm_dd(updates["user_read_at"])
                if clean:
                    updates["user_read_at"] = clean
                    updates["goal_year"] = int(clean[:4])

            if not updates:
                updates = {k: v for k, v in data.items() if k != "goodreads_id"}

            if not book_id or not updates:
                logger.warning("update_book: Missing required fields. book_id: %s, updates: %s", book_id, updates)
                raise ValueError("Missing 'goodreads_id' or updates in request.")

            ref = db.reference(f"/books/{book_id}")
            if ref.get():
                current_data = ref.get()
                logger.info("update_book: Current values: %s", json.dumps(current_data, indent=2))
                logger.info("update_book: Applying updates: %s", json.dumps(updates, indent=2))
                logger.info("update_book: Book %s found, applying updates: %s", book_id, updates)
                ref.update(updates)
                updated_data = ref.get()
                logger.info("update_book: Updated values: %s", json.dumps(updated_data, indent=2))
                response = {"status": "success", "message": "Book updated.", "book_id": book_id}
            else:
                logger.warning("update_book: Book %s not found in database", book_id)
                response = {"status": "error", "message": "Book not found.", "book_id": book_id}

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            logger.error("update_book: Exception occurred", exc_info=True)
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "error",
                "message": str(e)
            }).encode())

    def do_PATCH(self):
        logger.info("update_book: do_PATCH called, delegating to do_POST")
        self.do_POST()