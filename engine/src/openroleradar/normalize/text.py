"""Text normalization and whitespace canonicalization."""

from __future__ import annotations

import re
import unicodedata

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HTML_TAGS = re.compile(r"<[^>]+>")
_WHITESPACE_RUN = re.compile(r"\s+")
_SMART_QUOTES = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u00a0": " ",
    }
)


def normalize_whitespace(text: str | None) -> str:
    """Collapse runs of whitespace and trim edges."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text).translate(_SMART_QUOTES)
    normalized = _CONTROL_CHARS.sub("", normalized)
    normalized = _WHITESPACE_RUN.sub(" ", normalized)
    return normalized.strip()


def strip_html(text: str | None) -> str:
    """Remove HTML tags and decode common entities via NFKC normalization."""
    if not text:
        return ""
    without_tags = _HTML_TAGS.sub(" ", text)
    without_tags = without_tags.replace("&nbsp;", " ")
    without_tags = without_tags.replace("&amp;", "&")
    without_tags = without_tags.replace("&lt;", "<")
    without_tags = without_tags.replace("&gt;", ">")
    return normalize_whitespace(without_tags)


def canonicalize_text(text: str | None, *, lowercase: bool = True) -> str:
    """Deterministic canonical form for matching and hashing."""
    cleaned = strip_html(text)
    if lowercase:
        cleaned = cleaned.casefold()
    return normalize_whitespace(cleaned)
