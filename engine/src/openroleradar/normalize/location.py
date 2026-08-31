"""Location parsing with pycountry and disambiguation rules."""

from __future__ import annotations

import re
from dataclasses import dataclass

import pycountry

from openroleradar.models.enums import RemoteScope, WorkplaceType
from openroleradar.models.job import Location
from openroleradar.normalize.text import canonicalize_text, normalize_whitespace

_US_STATES: dict[str, str] = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
}

_CANADIAN_PROVINCES: dict[str, str] = {
    "AB": "Alberta",
    "BC": "British Columbia",
    "MB": "Manitoba",
    "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador",
    "NS": "Nova Scotia",
    "NT": "Northwest Territories",
    "NU": "Nunavut",
    "ON": "Ontario",
    "PE": "Prince Edward Island",
    "QC": "Quebec",
    "SK": "Saskatchewan",
    "YT": "Yukon",
}

_COUNTRY_CONTINENT: dict[str, str] = {
    "US": "North America",
    "CA": "North America",
    "MX": "North America",
    "GB": "Europe",
    "FR": "Europe",
    "DE": "Europe",
    "IE": "Europe",
    "NL": "Europe",
    "ES": "Europe",
    "IT": "Europe",
    "SE": "Europe",
    "NO": "Europe",
    "DK": "Europe",
    "FI": "Europe",
    "CH": "Europe",
    "AT": "Europe",
    "BE": "Europe",
    "PT": "Europe",
    "PL": "Europe",
    "IN": "Asia",
    "SG": "Asia",
    "JP": "Asia",
    "CN": "Asia",
    "KR": "Asia",
    "AU": "Oceania",
    "NZ": "Oceania",
    "BR": "South America",
    "AR": "South America",
}

_REMOTE_KEYWORDS = re.compile(
    r"\b(remote|work from home|wfh|hybrid|distributed|anywhere|telecommute)\b",
    re.I,
)
_WORLDWIDE = re.compile(r"\b(worldwide|global(?:ly)?|anywhere in the world)\b", re.I)
_COUNTRY_LIMITED = re.compile(
    r"\b(?:remote\s+(?:in|within|across)\s+(?:the\s+)?)?"
    r"(?P<country>united states|usa|u\.s\.a?|canada|uk|united kingdom|india|germany|france|australia)\b"
    r"|\b(?P<code>US|CA|GB|DE|FR|IN|AU)\s+only\b",
    re.I,
)
_REGION_LIMITED = re.compile(
    r"\b(?:remote\s+(?:in|within|across)\s+)?"
    r"(?:the\s+)?(?P<region>eu|europe|emea|apac|latam|north america|namer)\b",
    re.I,
)
_TIMEZONE_LIMITED = re.compile(
    r"\b(?P<tz>pst|pdt|mst|mdt|cst|cdt|est|edt|utc|gmt|cet|ist|jst|aest|bst)\b.*\b(?:timezone|hours?)\b"
    r"|\b(?:within|overlap)\s+(?P<tz2>pst|pdt|mst|mdt|cst|cdt|est|edt|utc|gmt|cet|ist|jst|aest|bst)\b",
    re.I,
)

_COUNTRY_ALIASES: dict[str, str] = {
    "united states": "US",
    "usa": "US",
    "u.s.": "US",
    "u.s.a.": "US",
    "us": "US",
    "canada": "CA",
    "united kingdom": "GB",
    "uk": "GB",
    "great britain": "GB",
    "france": "FR",
    "germany": "DE",
    "india": "IN",
    "australia": "AU",
    "ireland": "IE",
    "netherlands": "NL",
    "spain": "ES",
    "italy": "IT",
    "japan": "JP",
    "singapore": "SG",
}

_REGION_ALIASES: dict[str, str] = {
    "eu": "EU",
    "europe": "EU",
    "emea": "EMEA",
    "apac": "APAC",
    "latam": "LATAM",
    "north america": "North America",
    "namer": "North America",
}


@dataclass(frozen=True)
class RemoteInfo:
    workplace_type: WorkplaceType
    remote_scope: RemoteScope
    remote_allowed_countries: list[str]
    remote_allowed_regions: list[str]


def _lookup_country(name: str) -> str | None:
    key = canonicalize_text(name)
    if key in _COUNTRY_ALIASES:
        return _COUNTRY_ALIASES[key]
    try:
        country = pycountry.countries.lookup(name)
        return str(country.alpha_2)
    except LookupError:
        return None


def _continent_for(code: str | None) -> str | None:
    if not code:
        return None
    return _COUNTRY_CONTINENT.get(code.upper())


def _is_california_context(parts: list[str]) -> bool:
    joined = ", ".join(parts).lower()
    if "canada" in joined:
        return False
    if any(prov.lower() in joined for prov in _CANADIAN_PROVINCES.values()):
        return False
    for part in parts:
        token = part.strip().upper()
        if token == "CA" and len(parts) >= 2:
            return True
        if token in _US_STATES and token != "CA":
            return True
        if "california" in part.lower():
            return True
        if re.search(r"\b\d{5}(?:-\d{4})?\b", part):
            return True
    if re.search(r"\b(united states|usa|u\.s\.)\b", joined):
        return "ca" in joined.split(",")[-1].strip().lower() or "california" in joined
    return False


def _is_canada_context(parts: list[str], raw: str) -> bool:
    joined = raw.lower()
    if "canada" in joined:
        return True
    for part in parts:
        token = part.strip().upper()
        if token in _CANADIAN_PROVINCES:
            return True
        if part.strip().lower() in {p.lower() for p in _CANADIAN_PROVINCES.values()}:
            return True
    return False


def _resolve_ca_ambiguity(parts: list[str], raw: str) -> tuple[str | None, str | None]:
    """Return (region_name, country_code) when CA token is present."""
    has_ca_token = any(p.strip().upper() == "CA" for p in parts)
    if not has_ca_token:
        return None, None

    if _is_canada_context(parts, raw):
        for part in parts:
            token = part.strip().upper()
            if token in _CANADIAN_PROVINCES:
                return _CANADIAN_PROVINCES[token], "CA"
        return None, "CA"

    if _is_california_context(parts):
        return "California", "US"

    return None, None


def _resolve_paris(parts: list[str]) -> tuple[str | None, str | None, str | None]:
    """Disambiguate Paris TX vs Paris FR."""
    city = None
    region = None
    country_code = None
    lower_parts = [p.strip().lower() for p in parts]
    if not any("paris" in p for p in lower_parts):
        return city, region, country_code

    city = "Paris"
    if any(p in {"tx", "texas"} for p in lower_parts):
        return city, "Texas", "US"
    if any(p in {"fr", "france"} for p in lower_parts):
        return city, None, "FR"
    if "france" in " ".join(lower_parts):
        return city, None, "FR"
    if "texas" in " ".join(lower_parts):
        return city, "Texas", "US"
    return city, region, country_code


def parse_location(raw: str | None) -> Location:
    """Parse a single location string into structured fields."""
    if not raw:
        return Location()

    cleaned = normalize_whitespace(raw)
    if not cleaned:
        return Location()

    if _REMOTE_KEYWORDS.search(cleaned) and not re.search(r",\s*\w", cleaned):
        return Location(raw=cleaned)

    parts = [p.strip() for p in cleaned.split(",") if p.strip()]
    city: str | None = None
    region: str | None = None
    country: str | None = None
    country_code: str | None = None

    paris_city, paris_region, paris_country = _resolve_paris(parts)
    if paris_city:
        city, region, country_code = paris_city, paris_region, paris_country
        if country_code == "FR":
            country = "France"
        elif country_code == "US":
            country = "United States"

    ca_region, ca_country = _resolve_ca_ambiguity(parts, cleaned)
    if ca_region or ca_country:
        if ca_region:
            region = ca_region
        if ca_country:
            country_code = ca_country
            country = "Canada" if ca_country == "CA" else "United States"

    if len(parts) >= 1 and not city:
        city = parts[0]

    if len(parts) >= 2 and not region:
        second = parts[1]
        token = second.upper()
        if token in _US_STATES:
            region = _US_STATES[token]
            country_code = country_code or "US"
            country = country or "United States"
        elif token in _CANADIAN_PROVINCES:
            region = _CANADIAN_PROVINCES[token]
            country_code = country_code or "CA"
            country = country or "Canada"
        else:
            region = second

    if len(parts) >= 3:
        last = parts[-1]
        code = _lookup_country(last)
        if code:
            country_code = code
            country_obj = pycountry.countries.get(alpha_2=code)
            country = country_obj.name if country_obj is not None else country
        elif not country:
            country = last
    elif len(parts) == 2:
        last = parts[-1]
        code = _lookup_country(last)
        if code:
            country_code = code
            country_obj = pycountry.countries.get(alpha_2=code)
            country = country_obj.name if country_obj is not None else country
            if city == last:
                city = parts[0]
                region = None

    if country_code == "CA" and region == "California":
        region = None
        country_code = "US"
        country = "United States"
        region = "California"

    return Location(
        raw=cleaned,
        city=city,
        region=region,
        country=country,
        country_code=country_code,
        continent=_continent_for(country_code),
    )


def parse_locations(raw_locations: list[str]) -> list[Location]:
    """Parse multiple location strings, skipping empty entries."""
    locations: list[Location] = []
    for raw in raw_locations:
        loc = parse_location(raw)
        if loc.raw or loc.city or loc.country_code:
            locations.append(loc)
    return locations


def parse_workplace_type(
    locations_raw: list[str],
    description: str | None = None,
) -> WorkplaceType:
    """Infer onsite/hybrid/remote from location strings and description."""
    corpus = " ".join(locations_raw)
    if description:
        corpus = f"{corpus} {description}"
    corpus_lower = corpus.lower()

    has_remote = bool(_REMOTE_KEYWORDS.search(corpus_lower))
    has_onsite = bool(
        re.search(r"\b(on[- ]site|in[- ]office|office based)\b", corpus_lower)
        or any(
            loc.raw and not _REMOTE_KEYWORDS.search(loc.raw.lower())
            for loc in parse_locations(locations_raw)
            if loc.city or loc.country_code
        )
    )

    if has_remote and has_onsite:
        return WorkplaceType.HYBRID
    if has_remote:
        return WorkplaceType.REMOTE
    if has_onsite or locations_raw:
        return WorkplaceType.ONSITE
    return WorkplaceType.UNKNOWN


def parse_remote_info(
    locations_raw: list[str],
    description: str | None = None,
) -> RemoteInfo:
    """Parse remote scope and geographic limits from location text and description."""
    corpus = " ".join(locations_raw)
    if description:
        corpus = f"{corpus} {description}"
    corpus_lower = corpus.lower()

    workplace = parse_workplace_type(locations_raw, description)
    if workplace not in {WorkplaceType.REMOTE, WorkplaceType.HYBRID}:
        return RemoteInfo(
            workplace_type=workplace,
            remote_scope=RemoteScope.UNKNOWN,
            remote_allowed_countries=[],
            remote_allowed_regions=[],
        )

    if _WORLDWIDE.search(corpus_lower):
        return RemoteInfo(
            workplace_type=workplace,
            remote_scope=RemoteScope.WORLDWIDE,
            remote_allowed_countries=[],
            remote_allowed_regions=[],
        )

    countries: list[str] = []
    for match in _COUNTRY_LIMITED.finditer(corpus_lower):
        token = match.group("country") or match.group("code")
        if token:
            code = _lookup_country(token) or token.upper()
            if code not in countries:
                countries.append(code)

    if countries:
        return RemoteInfo(
            workplace_type=workplace,
            remote_scope=RemoteScope.COUNTRY_LIMITED,
            remote_allowed_countries=countries,
            remote_allowed_regions=[],
        )

    regions: list[str] = []
    for match in _REGION_LIMITED.finditer(corpus_lower):
        token = (match.group("region") or "").lower()
        region = _REGION_ALIASES.get(token, token.upper())
        if region not in regions:
            regions.append(region)

    if regions:
        return RemoteInfo(
            workplace_type=workplace,
            remote_scope=RemoteScope.REGION_LIMITED,
            remote_allowed_countries=[],
            remote_allowed_regions=regions,
        )

    if _TIMEZONE_LIMITED.search(corpus_lower):
        return RemoteInfo(
            workplace_type=workplace,
            remote_scope=RemoteScope.TIMEZONE_LIMITED,
            remote_allowed_countries=[],
            remote_allowed_regions=[],
        )

    if workplace == WorkplaceType.REMOTE and locations_raw:
        return RemoteInfo(
            workplace_type=workplace,
            remote_scope=RemoteScope.LOCATION_LIMITED,
            remote_allowed_countries=[],
            remote_allowed_regions=[],
        )

    return RemoteInfo(
        workplace_type=workplace,
        remote_scope=RemoteScope.UNKNOWN,
        remote_allowed_countries=[],
        remote_allowed_regions=[],
    )
