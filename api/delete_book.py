from http.server import BaseHTTPRequestHandler
import json
import firebase_admin
from firebase_admin import credentials, db
import os
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            logger.info(f"delete_book request body: {body.decode('utf-8')}")
            data = json.loads(body)

            book_id = data.get("goodreads_id")
            logger.info(f"Attempting to delete book: {book_id}")
            if not book_id:
                raise ValueError("Missing 'goodreads_id' in request.")

            ref = db.reference(f"/books/{book_id}")
            if ref.get():
                logger.info(f"Book {book_id} found. Deleting.")
                ref.delete()
                response = {"status": "success", "message": "Book deleted.", "book_id": book_id}
                logger.info(f"delete_book response: {response}")
            else:
                logger.info(f"Book {book_id} not found.")
                response = {"status": "error", "message": "Book not found.", "book_id": book_id}
                logger.info(f"delete_book response: {response}")

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            logger.error(f"Error in delete_book: {e}")
            logger.exception(e)
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "error",
                "message": str(e)
            }).encode())