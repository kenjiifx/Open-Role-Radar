"""Text normalization and whitespace canonicalization."""

from __future__ import annotations

import html
import re
import unicodedata

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HTML_TAGS = re.compile(r"<[^>]+>", re.DOTALL)
_BLOCK_BREAK = re.compile(
    r"(?is)</(?:p|div|li|h[1-6]|tr|section|article|br)|<br\s*/?>"
)
_WHITESPACE_RUN = re.compile(r"[^\S\n]+")
_NEWLINE_RUN = re.compile(r"\n{3,}")
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

SUMMARY_MAX_CHARS = 2000


def normalize_whitespace(text: str | None) -> str:
    """Collapse runs of whitespace and trim edges (single-line friendly)."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text).translate(_SMART_QUOTES)
    normalized = _CONTROL_CHARS.sub("", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _decode_entities(text: str) -> str:
    """Unescape HTML entities, including Greenhouse double-encoding."""
    value = text
    for _ in range(4):
        decoded = html.unescape(value)
        if decoded == value:
            break
        value = decoded
    return value


def html_to_plaintext(text: str | None) -> str:
    """Decode entities, strip tags, and preserve light paragraph structure."""
    if not text:
        return ""
    value = _decode_entities(text)
    value = _BLOCK_BREAK.sub("\n", value)
    value = _HTML_TAGS.sub(" ", value)
    # Second pass: entity-decoded leftovers that still look like tags.
    if "<" in value and ">" in value:
        value = _decode_entities(value)
        value = _BLOCK_BREAK.sub("\n", value)
        value = _HTML_TAGS.sub(" ", value)
    value = unicodedata.normalize("NFKC", value).translate(_SMART_QUOTES)
    value = _CONTROL_CHARS.sub("", value)
    value = _WHITESPACE_RUN.sub(" ", value)
    value = _NEWLINE_RUN.sub("\n\n", value)
    lines = [line.strip() for line in value.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def strip_html(text: str | None) -> str:
    """Remove HTML tags and decode entities into compact single-line text."""
    return normalize_whitespace(html_to_plaintext(text))


def truncate_summary(text: str | None, *, limit: int = SUMMARY_MAX_CHARS) -> str | None:
    """Hard-cap summary length for public export without mid-word cut when possible."""
    if not text:
        return None
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    clipped = cleaned[: limit - 1].rstrip()
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped + "…"


def canonicalize_text(text: str | None, *, lowercase: bool = True) -> str:
    """Deterministic canonical form for matching and hashing."""
    cleaned = strip_html(text)
    if lowercase:
        cleaned = cleaned.casefold()
    return normalize_whitespace(cleaned)
