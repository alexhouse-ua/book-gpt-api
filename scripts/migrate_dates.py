"""
One-off migration: normalise date strings (YYYY-MM-DD) and derive goal_year.
Run locally once.  Safe to rerun: only updates records that need it.
"""
import sys, os
# Add the repository root (parent of the *scripts* folder) to PYTHONPATH
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from api.utils.dates import to_yyyy_mm_dd
import firebase_admin
from firebase_admin import credentials, db

SERVICE_JSON = "scripts/service-account.json"          # path to your Firebase key
DB_URL = "https://book-gpt-bf59c-default-rtdb.firebaseio.com/"            # your Realtime DB URL

cred = credentials.Certificate(SERVICE_JSON)
firebase_admin.initialize_app(cred, {"databaseURL": DB_URL})

ref = db.reference("/books")
books = ref.get() or {}

fixed = 0
for bid, bk in books.items():
    patch = {}

    # Normalise date fields
    for fld in ("updated_at", "user_date_added", "user_date_created", "user_read_at"):
        norm = to_yyyy_mm_dd(bk.get(fld))
        if norm and norm != bk.get(fld):
            patch[fld] = norm

    # Derive goal_year from user_read_at
    read_date = patch.get("user_read_at") or bk.get("user_read_at")
    if read_date and int(read_date[:4]) != bk.get("goal_year"):
        patch["goal_year"] = int(read_date[:4])

    if patch:
        ref.child(bid).update(patch)
        fixed += 1
        print("updated", bid, patch)

print(f"✅  Migration complete — {fixed} books updated")