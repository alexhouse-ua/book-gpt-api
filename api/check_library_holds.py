import json
import os
import requests
from http.server import BaseHTTPRequestHandler
from firebase_admin import credentials, db, initialize_app
from bs4 import BeautifulSoup
import firebase_admin
import time

# Firebase initialization
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
    initialize_app(cred, {
        'databaseURL': os.environ["FIREBASE_DB_URL"]
    })

# Helper Functions
def is_english(text):
    return True  # Placeholder, or use langdetect

def clean_wait_time(text):
    if not text or "unknown" in text.lower():
        return "Not available"
    return text.strip()

def check_hoopla(title, author):
    url = f"https://www.hoopladigital.com/search?query={title.replace(' ', '+')}+{author.replace(' ', '+')}&scope=everything"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(response.text, "html.parser")

    cards = soup.select(".card")
    ebook = False
    audio = False

    for card in cards:
        format_tag = card.select_one(".format-badge")
        lang_tag = card.select_one(".thumbnail-link")
        if not format_tag or not lang_tag:
            continue

        format_text = format_tag.get_text(strip=True).lower()
        if "english" not in lang_tag.get("href", "").lower():
            continue

        if "ebook" in format_text:
            ebook = True
        elif "audiobook" in format_text:
            audio = True

    return ebook, audio

def check_kindle_unlimited(title, author):
    url = f"https://www.amazon.com/s?k={'+'.join(title.split())}+{'+'.join(author.split())}+kindle+unlimited"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    for span in soup.find_all("span"):
        if span.get_text(strip=True).lower() == "read for free":
            return True
    return False

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        request_data = json.loads(body)
        filter_title = request_data.get("title")

        books_ref = db.reference("/books")
        all_books = books_ref.get() or {}
        updated_books = {}

        for book_id, book_data in all_books.items():
            title = book_data.get("book_title", "")
            author = book_data.get("author_name", "")
            if filter_title and filter_title.lower() not in title.lower():
                continue

            if not is_english(title):
                continue

            try:
                hoopla_ebook, hoopla_audio = check_hoopla(title, author)
                ku_available = check_kindle_unlimited(title, author)

                update_data = {
                    "hoopla_ebook_available": "Yes" if hoopla_ebook else "No",
                    "hoopla_audio_available": "Yes" if hoopla_audio else "No",
                    "ku_availability": "Yes" if ku_available else "No"
                }

                books_ref.child(book_id).update(update_data)
                updated_books[book_id] = update_data

            except Exception as e:
                updated_books[book_id] = {"error": str(e)}

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "complete", "updates": updated_books}).encode())