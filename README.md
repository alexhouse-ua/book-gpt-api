[![Python tests](https://github.com/alexhouse-ua/book-gpt-api/actions/workflows/python-tests.yml/badge.svg)](https://github.com/alexhouse-ua/book-gpt-api/actions/workflows/python-tests.yml)

# 📚 Shelf Help API

Welcome to the API backend for **Shelf Help**, your personalized romance reading companion. This API powers all book data interactions with Firebase and supports your Custom GPT’s ability to track, update, and recommend books based on your reading habits.

---

## 🔗 Live API Endpoint

**Base URL:**  
`https://book-gpt-api.vercel.app`

---

## 🚀 Endpoints Overview

### 📥 Add Book
`POST /api/add_book`  
Add a new book to Firebase. Requires at least a `goodreads_id`. Accepts any valid Firebase fields.

### ✏️ Update Book
`PATCH /api/update_book`  
Update one or more fields for an existing book. Must include `goodreads_id`.

### 🗑 Delete Book
`DELETE /api/delete_book`  
Delete a book entirely from Firebase using its `goodreads_id`.

### 🔎 Fetch Books
`POST /api/fetch_books`  
Fetch all books or filter using any field (e.g., `status`, `tone`, `series_name`).

### 🔍 Search Books
`POST /api/search_books`  
Search books by `title`, `author_name`, or any other matching field.

### 🔄 Sync Goodreads RSS
`POST /api/sync_rss`  
Pulls new finished books from Goodreads RSS and updates their status in Firebase.

### 📚 Check Library Holds
`POST /api/check_library_holds`  
Checks for availability on Kindle Unlimited, Hoopla, and supported library systems.  
Can be run for a specific title or a filtered group.  
**Note:** Currently uses placeholder data for Libby libraries until API access is granted.

---

## 🧠 Integration with Shelf Help GPT

This API is designed to work exclusively with the **Shelf Help** Custom GPT and should be used for:

- Managing a reading queue
- Tracking reading progress
- Backfilling metadata (tone, trope, source)
- Scheduling reports and alerts
- Prioritizing free reading access

The GPT **must always use these endpoints** rather than attempting to write directly to Firebase.

---

## 🛠 Technologies

- 🔥 Firebase Realtime Database
- ⚙️ Vercel Serverless Functions (Python)
- 📡 Goodreads RSS Integration
- 🔍 Web scraping (Hoopla, KU)  
- 🧠 Custom GPT integration (via Actions)

---

## 🧪 Status

✅ Core CRUD  
✅ Goodreads Sync  
✅ API-based Queue & Report Tools  
⚠️ Library holds limited until OverDrive access is approved  
🚧 Future: Backfill enrichment & series tracking

---

## 📖 License

MIT – Use it, remix it, enjoy it.

---

_Developed with ❤️ by [alexhouse-ua](https://github.com/alexhouse-ua)_
