"""HTTP client and URL utilities."""

from openroleradar.http.client import HTTPResponse, SafeHTTPClient
from openroleradar.http.url import (
    URLValidationError,
    build_url,
    canonicalize_url,
    extract_hostname,
    is_allowed_scheme,
    validate_http_url,
)

__all__ = [
    "HTTPResponse",
    "SafeHTTPClient",
    "URLValidationError",
    "build_url",
    "canonicalize_url",
    "extract_hostname",
    "is_allowed_scheme",
    "validate_http_url",
]
