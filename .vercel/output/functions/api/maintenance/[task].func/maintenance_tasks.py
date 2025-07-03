"""
Pure-Python helpers called by api/maintenance/[task].py
"""
# --- shared imports ---------------------------------------------------------
from dotenv import load_dotenv
load_dotenv()
import os, csv, logging, json, requests
import firebase_admin
from firebase_admin import credentials, db
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- Firebase init (one-time) ---------------------------------------------
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

# ---------------------------------------------------------------------------
def ping(_body):            # /internal/ping
    return "pong"

# ---------------------------------------------------------------------------
def backfill_empty_fields(_body):   # /internal/backfill_empty_fields
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
    updated = 0
    for book_id, data in books.items():
        updates = {f: "" for f in default_fields if f not in data}
        if updates:
            ref.child(book_id).update(updates)
            updated += 1
    return {"books_updated": updated}

# ---------------------------------------------------------------------------
def backfill_enrichment(_body):    # /internal/backfill_enrichment
    def scrape_trope_and_tone(title, author):
        base_query = f"{title} {author} book trope"
        sources = [
            "site:bookriot.com", "site:goodreads.com", "site:romance.io",
            "site:smartbitchestrashybooks.com", "site:booktriggerwarnings.com",
            "site:accio-books.com"
        ]
        url = "https://www.google.com/search?q=" + requests.utils.quote(
            f"{base_query} " + " OR ".join(sources)
        )
        headers = {"User-Agent": "Mozilla/5.0"}
        soup = BeautifulSoup(requests.get(url, headers=headers, timeout=10).text, "html.parser")
        links = [a['href'] for a in soup.select("a[href]") if 'http' in a['href']][:3]

        text = ""
        for link in links:
            try:
                text += BeautifulSoup(requests.get(link, headers=headers, timeout=10).text,
                                      "html.parser").get_text(" ", strip=True)
            except Exception as e:
                logger.warning(f"skip {link}: {e}")
        text = text.lower()

        known_tropes = ["enemies to lovers", "friends to lovers", "grumpy sunshine",
                        "forced proximity", "second chance", "slow burn", "fake dating",
                        "found family"]
        known_tones  = ["emotional", "dark", "lighthearted", "funny",
                        "intense", "angsty", "heartwarming", "steamy"]

        tropes = [t for t in known_tropes if t in text]
        tones  = [t for t in known_tones  if t in text]
        return { "trope": ", ".join(tropes), "tone": ", ".join(tones) }

    books_ref = db.reference("/books")
    all_books = books_ref.get() or {}
    updated = 0
    for book_id, book in all_books.items():
        if book.get("status") != "Finished": continue
        if book.get("trope") or book.get("tone"): continue
        title  = book.get("book_title") or book.get("title")
        author = book.get("author_name")
        if not title or not author: continue
        scraped = scrape_trope_and_tone(title, author)
        if scraped["trope"] or scraped["tone"]:
            books_ref.child(book_id).update(scraped)
            updated += 1
    return {"books_updated": updated}

# ---------------------------------------------------------------------------
def print_firebase_books(_body):    # /internal/print_firebase_books
    books = db.reference("/books").get() or {}
    path  = "firebase_books_full_dump.csv"
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
    with open(path, "w", newline='', encoding="utf-8") as f:
        import csv
        w = csv.DictWriter(f, fieldnames=fieldnames); w.writeheader()
        for book_id, book in books.items():
            row = {k: book.get(k, "") for k in fieldnames}
            row["goodreads_id"] = book_id
            w.writerow(row)
    return {"exported_to": path}

# ---------------------------------------------------------------------------
def backfill_reflection_pending(_: dict):
    """
    Set reflection_pending on ALL finished books that still have blank reflection
    fields. Safe to run repeatedly – does only the necessary updates.
    """
    from firebase_admin import db          # imported lazily to keep cold-start small

    ref = db.reference("/books")
    books = ref.get() or {}
    updated = 0

    for bid, bk in books.items():
        if bk.get("status") != "Finished":
            continue
        liked     = bk.get("liked", "")
        disliked  = bk.get("disliked", "")
        extras    = bk.get("extras", "")
        notes     = bk.get("notes", "")

        need_flag = any(not fld for fld in (liked, disliked, extras, notes))
        if bk.get("reflection_pending") == need_flag:
            continue  # already correct

        ref.child(bid).update({"reflection_pending": need_flag})
        updated += 1

    return {"updated_records": updated}