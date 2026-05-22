from urllib.parse import urlparse


def media_from_url(url: str) -> str:
    """Derive organization name from URL host when API source is missing."""
    host = urlparse(url).netloc.strip()
    if host.startswith("www."):
        host = host[4:]
    return host


def resolve_media(item: dict, url: str) -> str:
    """News organization from search API or URL domain."""
    source = (item.get("source") or "").strip()
    if source:
        return source
    return media_from_url(url)
