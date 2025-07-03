from datetime import datetime
from typing import Optional
import dateutil.parser  # pip install python-dateutil

def to_yyyy_mm_dd(raw: str | None) -> Optional[str]:
    """Return YYYY-MM-DD or None if parsing fails."""
    if not raw:
        return None
    try:
        dt = dateutil.parser.parse(raw)
        return dt.date().isoformat()          # e.g. '2025-02-26'
    except (ValueError, TypeError):
        return None