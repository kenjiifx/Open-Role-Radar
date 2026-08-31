"""Unit tests for HTTP safety and URL utilities."""

from __future__ import annotations

import ipaddress
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from openroleradar.config import ProjectConfig, find_repo_root
from openroleradar.http.client import HTTPClientError, SafeHTTPClient
from openroleradar.http.url import URLValidationError, canonicalize_url, validate_http_url
from openroleradar.security.first_party import is_denied_url, load_aggregator_denylist
from openroleradar.security.ssrf import SSRFError, is_blocked_ip, is_private_or_reserved_ip


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("HTTPS://Example.COM/Jobs/?b=2&a=1", "https://example.com/Jobs?a=1&b=2"),
        ("http://example.com:80/path", "http://example.com/path"),
        ("https://example.com:443/careers", "https://example.com/careers"),
    ],
)
def test_canonicalize_url_normalizes_components(url: str, expected: str) -> None:
    assert canonicalize_url(url) == expected


def test_validate_http_url_rejects_non_http_schemes() -> None:
    with pytest.raises(URLValidationError):
        validate_http_url("ftp://example.com/file")


def test_validate_http_url_rejects_embedded_credentials() -> None:
    with pytest.raises(URLValidationError):
        validate_http_url("https://user:pass@example.com/jobs")


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "10.0.0.1",
        "192.168.1.10",
        "169.254.169.254",
        "::1",
        "fc00::1",
    ],
)
def test_is_blocked_ip_detects_private_and_metadata_addresses(ip: str) -> None:
    assert is_blocked_ip(ip)


def test_is_blocked_ip_allows_public_addresses() -> None:
    assert not is_blocked_ip("8.8.8.8")
    assert not is_private_or_reserved_ip(ipaddress.ip_address("1.1.1.1"))


@pytest.mark.asyncio
async def test_resolve_host_blocks_localhost() -> None:
    from openroleradar.security.ssrf import resolve_host_ips

    with pytest.raises(SSRFError, match="localhost"):
        await resolve_host_ips("localhost")


def test_aggregator_denylist_blocks_known_domains() -> None:
    root = find_repo_root(Path(__file__).resolve())
    denylist = load_aggregator_denylist(root)
    assert is_denied_url("https://www.linkedin.com/jobs/view/123", denylist)
    assert not is_denied_url("https://boards.greenhouse.io/stripe/jobs/1", denylist)


@pytest.mark.asyncio
@respx.mock
async def test_safe_http_client_blocks_private_redirect_target() -> None:
    config = ProjectConfig(user_agent="OpenRoleRadar-Test/1.0")
    client = SafeHTTPClient(config=config, retry_max_attempts=1)

    respx.get("https://example.com/start").mock(
        return_value=httpx.Response(302, headers={"Location": "http://127.0.0.1/internal"})
    )

    with pytest.raises(HTTPClientError, match="Blocked IP literal"):
        await client.get("https://example.com/start")

    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_safe_http_client_follows_valid_redirect() -> None:
    config = ProjectConfig(user_agent="OpenRoleRadar-Test/1.0")
    client = SafeHTTPClient(config=config, retry_max_attempts=1)

    respx.get("https://example.com/start").mock(
        return_value=httpx.Response(302, headers={"Location": "/final"})
    )
    respx.get("https://example.com/final").mock(return_value=httpx.Response(200, text="ok"))

    with patch(
        "openroleradar.http.client.validate_url_target",
        new=AsyncMock(return_value=None),
    ):
        response = await client.get("https://example.com/start")

    assert response.status_code == 200
    assert response.text == "ok"
    assert response.url == "https://example.com/final"
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_safe_http_client_sends_conditional_headers() -> None:
    config = ProjectConfig(user_agent="OpenRoleRadar-Test/1.0")
    client = SafeHTTPClient(config=config, retry_max_attempts=1)

    route = respx.get("https://example.com/jobs").mock(
        return_value=httpx.Response(
            304,
            headers={"ETag": '"abc123"', "Last-Modified": "Mon, 01 Jan 2024 00:00:00 GMT"},
        )
    )

    with patch(
        "openroleradar.http.client.validate_url_target",
        new=AsyncMock(return_value=None),
    ):
        response = await client.get(
            "https://example.com/jobs",
            etag='"abc123"',
            if_modified_since="Mon, 01 Jan 2024 00:00:00 GMT",
        )

    assert response.is_not_modified
    assert route.calls.last.request.headers["If-None-Match"] == '"abc123"'
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_safe_http_client_enforces_max_response_size() -> None:
    config = ProjectConfig(user_agent="OpenRoleRadar-Test/1.0")
    client = SafeHTTPClient(config=config, max_response_bytes=16, retry_max_attempts=1)

    respx.get("https://example.com/big").mock(return_value=httpx.Response(200, content=b"x" * 32))

    with (
        patch(
            "openroleradar.http.client.validate_url_target",
            new=AsyncMock(return_value=None),
        ),
        pytest.raises(HTTPClientError, match="exceeded max size"),
    ):
        await client.get("https://example.com/big")

    await client.aclose()
