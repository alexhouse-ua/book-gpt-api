from dotenv import load_dotenv
load_dotenv()
from http.server import BaseHTTPRequestHandler
import json
import os
import logging

import firebase_admin
from firebase_admin import credentials, db
from bs4 import BeautifulSoup
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Firebase init
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

def scrape_trope_and_tone(title, author):
    try:
        base_query = f"{title} {author} book trope"
        sources = [
            "site:bookriot.com",
            "site:goodreads.com",
            "site:romance.io",
            "site:smartbitchestrashybooks.com",
            "site:booktriggerwarnings.com",
            "site:accio-books.com"
        ]
        combined_query = f"{base_query} " + " OR ".join(sources)
        url = f"https://www.google.com/search?q={requests.utils.quote(combined_query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        links = [a['href'] for a in soup.select("a[href]") if 'http' in a['href']]
        result_text = ""
        for link in links[:3]:  # Limit to top 3 external pages
            try:
                article = requests.get(link, headers=headers, timeout=10)
                article_soup = BeautifulSoup(article.text, "html.parser")
                result_text += article_soup.get_text(separator=" ", strip=True)
            except Exception as sub_error:
                logger.warning(f"Failed to scrape {link}: {sub_error}")
                continue

        result_text = result_text.lower()
        logger.info(f"Scraped text sample for '{title}' by {author}: {result_text[:1000]}")

        tropes = []
        tones = []

        known_tropes = ["enemies to lovers", "friends to lovers", "grumpy sunshine", "forced proximity", "second chance", "slow burn", "fake dating", "found family"]
        known_tones = ["emotional", "dark", "lighthearted", "funny", "intense", "angsty", "heartwarming", "steamy"]

        for trope in known_tropes:
            if trope in result_text:
                tropes.append(trope)

        for tone in known_tones:
            if tone in result_text:
                tones.append(tone)

        return {
            "trope": ", ".join(tropes),
            "tone": ", ".join(tones)
        }
    except Exception as e:
        logger.error(f"Scraping error for '{title}' by {author}: {e}")
        return {"trope": "", "tone": ""}

def enrich_finished_books():
    books_ref = db.reference("/books")
    all_books = books_ref.get() or {}
    updated = 0

    for book_id, book in all_books.items():
        if book.get("status") != "Finished":
            continue
        if book.get("trope") or book.get("tone"):
            continue

        title = book.get("book_title") or book.get("title")
        author = book.get("author_name")
        if not title or not author:
            continue

        logger.info(f"Enriching: {title} by {author}")
        scraped = scrape_trope_and_tone(title, author)

        if scraped["trope"] or scraped["tone"]:
            books_ref.child(book_id).update(scraped)
            logger.info(f"Updated {book_id} with {scraped}")
            updated += 1

    logger.info(f"Finished enrichment pass. Total books updated: {updated}")

if __name__ == "__main__":
    enrich_finished_books()
