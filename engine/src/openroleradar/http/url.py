"""URL canonicalization and validation helpers."""

from __future__ import annotations

from urllib.parse import parse_qsl, quote, unquote, urlencode, urljoin, urlparse, urlunparse

ALLOWED_SCHEMES = frozenset({"http", "https"})
DEFAULT_PORTS = {"http": 80, "https": 443}


class URLValidationError(ValueError):
    """Raised when a URL fails HTTP(S) validation rules."""


def is_allowed_scheme(scheme: str) -> bool:
    """Return True for HTTP and HTTPS schemes."""
    return scheme.lower() in ALLOWED_SCHEMES


def extract_hostname(url: str) -> str | None:
    """Extract hostname from a URL string."""
    parsed = urlparse(url)
    return parsed.hostname


def _normalize_path(path: str) -> str:
    if not path:
        return "/"
    segments = [unquote(segment) for segment in path.split("/")]
    stack: list[str] = []
    for segment in segments:
        if segment in ("", "."):
            continue
        if segment == "..":
            if stack:
                stack.pop()
            continue
        stack.append(segment)
    return "/" + "/".join(quote(segment, safe=":@&=+$,;~*'()!") for segment in stack)


def _normalize_query(query: str) -> str:
    if not query:
        return ""
    pairs = parse_qsl(query, keep_blank_values=True)
    pairs.sort(key=lambda item: (item[0], item[1]))
    return urlencode(pairs, doseq=True)


def canonicalize_url(url: str, *, base: str | None = None) -> str:
    """Canonicalize a URL for stable comparison and storage."""
    absolute = urljoin(base, url) if base else url
    parsed = urlparse(absolute.strip())

    scheme = parsed.scheme.lower()
    if not scheme:
        raise URLValidationError(f"URL missing scheme: {url}")

    hostname = (parsed.hostname or "").lower().rstrip(".")
    if not hostname:
        raise URLValidationError(f"URL missing hostname: {url}")

    port = parsed.port
    if port is not None and DEFAULT_PORTS.get(scheme) == port:
        port = None

    netloc = hostname
    if port is not None:
        netloc = f"{hostname}:{port}"
    if parsed.username:
        userinfo = parsed.username
        if parsed.password:
            userinfo = f"{userinfo}:{parsed.password}"
        netloc = f"{userinfo}@{netloc}"

    path = _normalize_path(parsed.path)
    query = _normalize_query(parsed.query)
    fragment = ""

    return urlunparse((scheme, netloc, path, "", query, fragment))


def validate_http_url(url: str, *, base: str | None = None) -> str:
    """Validate and canonicalize an HTTP or HTTPS URL."""
    canonical = canonicalize_url(url, base=base)
    parsed = urlparse(canonical)
    if not is_allowed_scheme(parsed.scheme):
        raise URLValidationError(f"Unsupported URL scheme: {parsed.scheme}")
    if parsed.username or parsed.password:
        raise URLValidationError("Embedded credentials are not allowed in URLs")
    if not parsed.hostname:
        raise URLValidationError(f"URL missing hostname: {url}")
    return canonical


def build_url(
    scheme: str,
    host: str,
    path: str = "/",
    *,
    query: dict[str, str] | None = None,
    port: int | None = None,
) -> str:
    """Build a canonical HTTP(S) URL from components."""
    normalized_scheme = scheme.lower()
    if not is_allowed_scheme(normalized_scheme):
        raise URLValidationError(f"Unsupported URL scheme: {scheme}")

    hostname = host.lower().strip().rstrip(".")
    netloc = hostname if port is None else f"{hostname}:{port}"
    query_string = urlencode(query or {}, doseq=True)
    candidate = urlunparse(
        (
            normalized_scheme,
            netloc,
            path if path.startswith("/") else f"/{path}",
            "",
            query_string,
            "",
        )
    )
    return validate_http_url(candidate)
