from __future__ import annotations

import io
import pandas as pd

from cfi.models import review_id

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 5000
MAX_TEXT = 12000


def read_csv(raw: bytes) -> pd.DataFrame:
    if len(raw) > MAX_BYTES:
        raise ValueError('CSV must be at most 5 MB')
    try:
        # All values remain strings; literal NA and leading zeros are preserved.
        frame = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False, encoding='utf-8-sig')
    except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
        raise ValueError('Expected a UTF-8 comma-separated CSV with a header') from exc
    if frame.empty or len(frame) > MAX_ROWS:
        raise ValueError('CSV must contain between 1 and 5,000 rows')
    return frame


def map_rows(frame: pd.DataFrame, text_col: str, date_col=None, rating_col=None):
    for col in [text_col, date_col, rating_col]:
        if col is not None and col not in frame.columns:
            raise ValueError('Mapped column does not exist')
    accepted, rejected, seen = [], [], set()
    for i, row in frame.iterrows():
        text = str(row[text_col])
        reason = None
        if not text.strip():
            reason = 'empty_text'
        elif len(text) > MAX_TEXT:
            reason = 'text_too_long'
        rid = review_id(text)
        if not reason and rid in seen:
            reason = 'duplicate_text'
        date = None
        if date_col and row[date_col]:
            parsed = pd.to_datetime(row[date_col], errors='coerce', utc=True)
            if pd.isna(parsed):
                reason = reason or 'invalid_date'
            else:
                date = parsed.isoformat()
        rating = str(row[rating_col]) if rating_col else None
        if reason:
            rejected.append({'source_row': int(i) + 2, 'reason': reason})
        else:
            seen.add(rid)
            accepted.append({'review_id': rid, 'text': text, 'date': date, 'rating': rating, 'source_row': int(i) + 2})
    return accepted, rejected
