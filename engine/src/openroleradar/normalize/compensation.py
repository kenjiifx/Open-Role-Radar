"""Compensation parsing from free-text salary strings."""

from __future__ import annotations

import re

from openroleradar.models.enums import CompensationPeriod
from openroleradar.models.job import Compensation
from openroleradar.normalize.text import normalize_whitespace

_CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "C$": "CAD",
    "A$": "AUD",
}

_PERIOD_PATTERNS: list[tuple[re.Pattern[str], CompensationPeriod]] = [
    (re.compile(r"\b(?:per\s+)?hour(?:ly)?\b", re.I), CompensationPeriod.HOUR),
    (re.compile(r"\b(?:per\s+)?day(?:ly)?\b", re.I), CompensationPeriod.DAY),
    (re.compile(r"\b(?:per\s+)?week(?:ly)?\b", re.I), CompensationPeriod.WEEK),
    (re.compile(r"\b(?:per\s+)?month(?:ly)?\b", re.I), CompensationPeriod.MONTH),
    (
        re.compile(r"\b(?:per\s+)?year(?:ly)?\b|\bannually\b|\bpa\b|\bp\.a\.\b", re.I),
        CompensationPeriod.YEAR,
    ),
    (re.compile(r"\binternship\b|\bstipend\b", re.I), CompensationPeriod.INTERNSHIP),
]

_AMOUNT_TOKEN = re.compile(
    r"(?P<currency>[$€£¥]|C\$|A\$|USD|EUR|GBP|CAD|AUD|JPY)?\s*"
    r"(?P<amount>\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?P<suffix>[kKmM])?",
    re.I,
)

_RANGE_SPLIT = re.compile(r"\s*(?:-|–|—|to)\s*", re.I)


def _parse_amount(token: str) -> float | None:
    match = _AMOUNT_TOKEN.search(token.strip())
    if not match:
        return None
    raw_amount = match.group("amount").replace(",", "")
    value = float(raw_amount)
    suffix = (match.group("suffix") or "").upper()
    if suffix == "K":
        value *= 1_000
    elif suffix == "M":
        value *= 1_000_000
    return value


def _detect_currency(text: str) -> str | None:
    upper = text.upper()
    for code in ("USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF", "SGD"):
        if code in upper:
            return code
    for symbol, code in _CURRENCY_SYMBOLS.items():
        if symbol in text:
            return code
    return None


def _detect_period(text: str) -> CompensationPeriod:
    for pattern, period in _PERIOD_PATTERNS:
        if pattern.search(text):
            return period
    if re.search(r"/\s*hr\b|/\s*h\b", text, re.I):
        return CompensationPeriod.HOUR
    if re.search(r"/\s*yr\b|/\s*y\b", text, re.I):
        return CompensationPeriod.YEAR
    return CompensationPeriod.UNKNOWN


def parse_compensation(raw: str | None) -> Compensation | None:
    """Parse a compensation string into structured min/max/currency/period."""
    if not raw:
        return None

    cleaned = normalize_whitespace(raw)
    if not cleaned:
        return None

    currency = _detect_currency(cleaned)
    period = _detect_period(cleaned)

    parts = _RANGE_SPLIT.split(cleaned)
    amounts: list[float] = []
    for part in parts:
        amount = _parse_amount(part)
        if amount is not None:
            amounts.append(amount)

    if not amounts:
        return Compensation(raw=cleaned, currency=currency, period=period)

    min_amount = min(amounts)
    max_amount = max(amounts) if len(amounts) > 1 else None
    if max_amount is not None and max_amount == min_amount:
        max_amount = None

    return Compensation(
        min_amount=min_amount,
        max_amount=max_amount,
        currency=currency,
        period=period,
        raw=cleaned,
    )
