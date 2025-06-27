from http.server import BaseHTTPRequestHandler
import json
import firebase_admin
from firebase_admin import credentials, db
import os
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Initialize Firebase
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
            data = json.loads(body) if body else {}
            if not data:
                raise ValueError("Missing search filters.")
            logger.info(f"search_books filters: {data}")

            books = db.reference("/books").get() or {}
            results = []
            for book_id, book in books.items():
                match = True
                for key, value in data.items():
                    field_val = str(book.get(key, "")).lower()
                    if str(value).lower() not in field_val:
                        match = False
                        break
                if match:
                    book["goodreads_id"] = book_id
                    results.append(book)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "results": results
            }).encode())

        except Exception as e:
            logger.exception(e)
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "error",
                "message": str(e)
            }).encode())