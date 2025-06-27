from http.server import BaseHTTPRequestHandler
import json
import os
import logging
import firebase_admin
from firebase_admin import credentials, db

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Initialize Firebase on first cold-start
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
                logger.info("Firebase initialized in fetch_books.py")

            # Read request body (filters)
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                filters = json.loads(body) if body else {}
            except json.JSONDecodeError:
                filters = {}

            # Retrieve all books
            ref = db.reference("/books")
            all_books = ref.get() or {}
            results = []

            # Apply filters
            for book_id, book_data in all_books.items():
                match = True
                for key, value in filters.items():
                    if str(book_data.get(key, "")).lower() != str(value).lower():
                        match = False
                        break
                if match:
                    book_data["goodreads_id"] = book_id
                    results.append(book_data)

            # Return filtered results
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"books": results}).encode())

        except Exception as e:
            logger.error("Error in fetch_books")
            logger.exception(e)
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "error",
                "message": str(e)
            }).encode())
