# tests/test_api.py
"""
Integration-style tests for the Shelf Help Custom GPT backend.

By default the suite targets a local Vercel dev server (`vercel dev`)
running on http://localhost:3000.  Override with
    BASE_URL=<your-preview-url> pytest -v
"""

import os
import uuid
import time
import requests
import pytest

BASE_URL = os.getenv("BASE_URL", "http://localhost:3000")

# ---- Helpers ---------------------------------------------------------------

def _post(path: str, payload: dict):
    return requests.post(f"{BASE_URL}{path}", json=payload)

def _get(path: str):
    return requests.get(f"{BASE_URL}{path}")

@pytest.fixture(scope="module")
def sample_book():
    """Create a unique book we can manipulate during the run."""
    book_id = str(uuid.uuid4())[:8]
    payload = {
        "goodreads_id": book_id,
        "title": f"Test Book {book_id}",
        "author_name": "Unit Tester",
        "status": "TBR"
    }
    resp = _post("/api/add_book", payload)
    assert resp.status_code == 200, resp.text
    yield payload  # give tests the payload / id
    # tidy up
    _post("/api/delete_book", {"goodreads_id": book_id})

# ---- /api/add_book ----------------------------------------------------------

def test_add_book_conflict(sample_book):
    """Adding the same book twice should 409/conflict."""
    r = _post("/api/add_book", sample_book)
    assert r.status_code in (200, 409)       # vercel edge vs local dev
    assert "already exists" in r.text

# ---- /api/fetch_books -------------------------------------------------------

def test_fetch_books_unfiltered():
    """Unfiltered fetch via POST returns a list of books."""
    r = _post("/api/fetch_books", {})
    assert r.status_code == 200
    data = r.json()
    assert "books" in data and isinstance(data["books"], list)

def test_fetch_books_filtered(sample_book):
    """Filtered fetch via POST should return the sample book."""
    r = _post("/api/fetch_books", {"title": "Test Book"})
    assert r.status_code == 200
    books = r.json()["books"]
    assert any(b["goodreads_id"] == sample_book["goodreads_id"] for b in books)

# ---- /api/search_books ------------------------------------------------------

def test_search_books_post(sample_book):
    r = _post("/api/search_books", {"author_name": "Unit Tester"})
    assert r.status_code == 200
    results = r.json()["results"]
    assert any(b["goodreads_id"] == sample_book["goodreads_id"] for b in results)

# ---- /api/update_book -------------------------------------------------------

def test_update_book(sample_book):
    updates = {"status": "Finished", "tone": "Light"}
    r = _post("/api/update_book", {"goodreads_id": sample_book["goodreads_id"],
                                   "updates": updates})
    assert r.status_code == 200
    # allow propagation
    time.sleep(1)
    r2 = _get(f"/api/fetch_books?goodreads_id={sample_book['goodreads_id']}")
    updated = r2.json()["books"][0]
    for k, v in updates.items():
        assert updated[k] == v

# ---- /api/check_library_holds ----------------------------------------------
@pytest.mark.slow
def test_check_library_holds_get_runs():
    """
    We can’t guarantee outside sources in CI, so just assert the endpoint
    returns 200 and a well-formed payload.
    """
    r = _post("/api/check_library_holds", {"title": "Shatter Me"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") in ("complete", "error")

# ---- /api/delete_book -------------------------------------------------------

def test_delete_book_archives(sample_book):
    r = _post("/api/delete_book", {"goodreads_id": sample_book["goodreads_id"]})
    assert r.status_code == 200
    # ensure it’s now archived
    r2 = _get(f"/api/fetch_books?goodreads_id={sample_book['goodreads_id']}")
    book = r2.json()["books"][0]
    assert book["status"] == "Archived"
