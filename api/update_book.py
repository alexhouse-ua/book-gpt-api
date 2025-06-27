from http.server import BaseHTTPRequestHandler
import json
import firebase_admin
from firebase_admin import credentials, db
import os

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
            data = json.loads(body)

            book_id = data.get("goodreads_id")
            updates = data.get("updates")

            if not book_id or not updates:
                raise ValueError("Missing 'goodreads_id' or 'updates' in request.")

            ref = db.reference(f"/books/{book_id}")
            if ref.get():
                ref.update(updates)
                response = {"status": "success", "message": "Book updated.", "book_id": book_id}
            else:
                response = {"status": "error", "message": "Book not found.", "book_id": book_id}

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "error",
                "message": str(e)
            }).encode())