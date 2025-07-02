# api/print_firebase_books.py

from dotenv import load_dotenv
load_dotenv()
import os
import csv
from firebase_admin import credentials, db, initialize_app

# Firebase initialization
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

books = db.reference("/books").get() or {}

fieldnames = [
    "guid", "goodreads_id", "pubdate", "title", "link",
    "book_image_url", "book_small_image_url", "book_medium_image_url", "book_large_image_url",
    "book_description", "author_name", "isbn", "user_name", "user_rating", "user_read_at",
    "user_date_added", "user_date_created", "user_shelves", "user_review", "average_rating",
    "book_published", "description_html", "status", "updated_at", "book_title", "series_name", "series_number",
    "tone", "flavor", "trope", "library_hold_status_tuscaloosa", "library_hold_status_seattle",
    "library_hold_status_camellia", "ku_availability", "hoopla_audio_available", "hoopla_ebook_available",
    "availability_source", "ku_expires_on", "pages_source", "next_release_date", "hype_flag",
    "queue_position", "queue_priority", "liked", "disliked", "extras", "notes", "rating_scale_tag",
    "inferred_score", "goal_year"
]

with open("firebase_books_full_dump.csv", "w", newline='', encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for book_id, book in books.items():
        row = {key: book.get(key, "") for key in fieldnames}
        row["goodreads_id"] = book_id  # Ensure ID is always filled
        writer.writerow(row)

print("✅ Exported to firebase_books_full_dump.csv")
