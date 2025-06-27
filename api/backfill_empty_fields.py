from dotenv import load_dotenv
load_dotenv()

import firebase_admin
from firebase_admin import credentials, db
import os

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

ref = db.reference("/books")
books = ref.get() or {}

for book_id, data in books.items():
    updates = {}
    for field in default_fields:
        if field not in data:
            updates[field] = ""
    if updates:
        print(f"Updating {book_id} with missing fields: {list(updates.keys())}")
        ref.child(book_id).update(updates)

print("Backfill complete.")