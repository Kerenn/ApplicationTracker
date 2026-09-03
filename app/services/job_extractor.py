from __future__ import annotations

import ipaddress
import json
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


@dataclass
class ExtractionResult:
    job_url: str
    company: str | None = None
    role: str | None = None
    location: str | None = None
    application_url: str | None = None
    source: str | None = None
    employment_type: str | None = None
    warning: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


def _safe_public_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    hostname = parsed.hostname.casefold()
    if hostname == "localhost" or hostname.endswith(".local"):
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return True
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
    )


def _meta(soup: BeautifulSoup, *names: str) -> str | None:
    for name in names:
        tag = soup.find("meta", attrs={"property": name}) or soup.find(
            "meta", attrs={"name": name}
        )
        if tag and tag.get("content"):
            return str(tag["content"]).strip() or None
    return None


def _job_postings(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for child in value for item in _job_postings(child)]
    if not isinstance(value, dict):
        return []
    found = []
    item_type = value.get("@type")
    types = item_type if isinstance(item_type, list) else [item_type]
    if "JobPosting" in types:
        found.append(value)
    for key in ("@graph", "mainEntity", "itemListElement"):
        found.extend(_job_postings(value.get(key)))
    return found


def _location(value: Any) -> str | None:
    if isinstance(value, list):
        locations = [item for item in (_location(entry) for entry in value) if item]
        return "; ".join(dict.fromkeys(locations)) or None
    if not isinstance(value, dict):
        return str(value).strip() if value else None
    address = value.get("address", value)
    if not isinstance(address, dict):
        return str(address).strip() if address else None
    parts = [
        address.get("addressLocality"),
        address.get("addressRegion"),
        address.get("addressCountry"),
    ]
    country = parts[-1]
    if isinstance(country, dict):
        parts[-1] = country.get("name")
    return ", ".join(str(part).strip() for part in parts if part) or None


def parse_job_html(url: str, html: str) -> ExtractionResult:
    soup = BeautifulSoup(html, "html.parser")
    parsed = urlparse(url)
    result = ExtractionResult(job_url=url, source=parsed.hostname)

    postings: list[dict[str, Any]] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            postings.extend(_job_postings(json.loads(script.get_text(strip=True))))
        except (json.JSONDecodeError, TypeError):
            continue

    if postings:
        posting = postings[0]
        organization = posting.get("hiringOrganization")
        result.company = (
            organization.get("name") if isinstance(organization, dict) else None
        )
        result.role = posting.get("title")
        result.location = _location(posting.get("jobLocation"))
        employment = posting.get("employmentType")
        result.employment_type = (
            ", ".join(str(item) for item in employment)
            if isinstance(employment, list)
            else employment
        )
        posting_url = posting.get("url")
        if posting_url and str(posting_url) != url:
            result.application_url = urljoin(url, str(posting_url))

    result.company = result.company or _meta(
        soup, "og:site_name", "application-name"
    )
    result.role = result.role or _meta(soup, "og:title", "twitter:title")
    result.location = result.location or _meta(soup, "job:location")

    if not result.role and soup.title and soup.title.string:
        result.role = soup.title.string.strip()

    if not result.application_url:
        for link in soup.find_all("a", href=True):
            label = " ".join(link.get_text(" ", strip=True).casefold().split())
            if label in {"apply", "apply now", "jetzt bewerben", "bewerben"}:
                result.application_url = urljoin(url, str(link["href"]))
                break

    return result


async def extract_job(url: str) -> ExtractionResult:
    url = url.strip()
    if not _safe_public_url(url):
        return ExtractionResult(
            job_url=url,
            warning="Only public http(s) job URLs can be inspected. You can still save it manually.",
        )
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=8.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) JobTracker/1.0",
                "Accept": "text/html,application/xhtml+xml",
            },
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "html" not in content_type:
                raise ValueError("The URL did not return an HTML page.")
            if len(response.content) > 2_000_000:
                raise ValueError("The page is too large to inspect safely.")
            return parse_job_html(str(response.url), response.text)
    except (httpx.HTTPError, ValueError) as exc:
        return ExtractionResult(
            job_url=url,
            source=urlparse(url).hostname,
            warning=f"Automatic extraction was unavailable: {exc}. Fill in the missing fields manually.",
        )
