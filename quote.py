from __future__ import annotations

import html
import re
from urllib.request import Request, urlopen

from paths import DAILY_QUOTE_URL

def html_to_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]*>", " ", value)
    unescaped = html.unescape(without_tags)
    return re.sub(r"\s+", " ", unescaped).strip()


def fetch_daily_quote() -> str:
    request = Request(
        DAILY_QUOTE_URL,
        headers={
            "User-Agent": "ConcentrateOn/1.0",
        },
    )
    with urlopen(request, timeout=5) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        content = response.read().decode(charset, errors="replace")
    quote = html_to_text(content)
    if not quote:
        raise ValueError("Daily quote response is empty.")
    return quote
