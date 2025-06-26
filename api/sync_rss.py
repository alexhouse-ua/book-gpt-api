from http.server import BaseHTTPRequestHandler
import feedparser
import json
import os
import logging
import firebase_admin
from firebase_admin import credentials, db

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Firebase Setup
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
                logger.info("Firebase initialized successfully.")

            # Fetch RSS Feed
            RSS_URL = "https://www.goodreads.com/review/list_rss/175732651?key=pieaUmxpwAFnXedFdGNPvOcgxfZ_Eme21zt09hpH0zzCVl7s&shelf=read"
            feed = feedparser.parse(RSS_URL)
            new_books = []

            for entry in feed.entries:
                try:
                    book_id = entry.id.split("book/show/")[-1].split("?")[0]
                    full_title = entry.title
                    title_split = full_title.split(" (")
                    book_title = title_split[0].strip()
                    series_name = None
                    series_number = None

                    if len(title_split) > 1 and "#" in title_split[1]:
                        series_info = title_split[1].rstrip(")")
                        parts = series_info.rsplit(" #", 1)
                        if len(parts) == 2:
                            series_name = parts[0].rstrip(",").strip()
                            series_number = parts[1].strip()

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
                        "user_read_at": entry.get("user_read_at", ""),
                        "user_date_added": entry.get("user_date_added", ""),
                        "user_date_created": entry.get("user_date_created", ""),
                        "user_shelves": entry.get("user_shelves", ""),
                        "user_review": entry.get("user_review", ""),
                        "average_rating": entry.get("average_rating", ""),
                        "book_published": entry.get("book_published", ""),
                        "description_html": entry.get("description", ""),
                        "status": "Finished",
                        "updated_at": entry.get("updated", "")
                    }

                    ref = db.reference(f"/books/{book_id}")
                    if not ref.get():
                        ref.set(book_data)
                        new_books.append(book_title)
                except Exception as entry_error:
                    logger.error(f"Error processing entry: {entry.get('title', 'Unknown')}")
                    logger.exception(entry_error)

            # Respond
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "books_added": new_books
            }).encode())

        except Exception as e:
            logger.error("Critical error in sync_rss function.")
            logger.exception(e)
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "error",
                "message": str(e)
            }).encode())
