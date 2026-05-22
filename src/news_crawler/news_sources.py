"""Top regional news outlets per market for optional source filtering."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

@dataclass(frozen=True)
class RegionalSources:
    domains: tuple[str, ...]
    media_aliases: tuple[str, ...]


# 20 domains + display-name aliases per market (curated for host + source field matching)
REGIONAL_SOURCES: dict[str, RegionalSources] = {
    "en": RegionalSources(
        domains=(
            "reuters.com",
            "apnews.com",
            "nytimes.com",
            "cnn.com",
            "bbc.com",
            "wsj.com",
            "washingtonpost.com",
            "bloomberg.com",
            "npr.org",
            "theguardian.com",
            "usatoday.com",
            "nbcnews.com",
            "abcnews.go.com",
            "foxnews.com",
            "cnbc.com",
            "politico.com",
            "latimes.com",
            "news.yahoo.com",
            "huffpost.com",
            "time.com",
        ),
        media_aliases=(
            "reuters",
            "associated press",
            "ap news",
            "new york times",
            "nytimes",
            "cnn",
            "bbc",
            "wall street journal",
            "wsj",
            "washington post",
            "bloomberg",
            "npr",
            "the guardian",
            "guardian",
            "usa today",
            "nbc news",
            "abc news",
            "fox news",
            "cnbc",
            "politico",
            "los angeles times",
            "la times",
            "yahoo news",
            "huffpost",
            "huffington post",
            "time",
        ),
    ),
    "ja": RegionalSources(
        domains=(
            "nhk.or.jp",
            "yahoo.co.jp",
            "asahi.com",
            "mainichi.jp",
            "yomiuri.co.jp",
            "nikkei.com",
            "sankei.com",
            "jiji.com",
            "kyodo.co.jp",
            "tokyo-np.co.jp",
            "fnn.jp",
            "news.tv-asahi.co.jp",
            "j-cast.com",
            "livedoor.com",
            "encount.press",
            "nikkan-gendai.com",
            "sponichi.co.jp",
            "chunichi.co.jp",
            "hokkaido-np.co.jp",
            "nishinippon.co.jp",
        ),
        media_aliases=(
            "nhk",
            "yahoo!ニュース",
            "yahoo japan",
            "yahoo news japan",
            "朝日新聞",
            "asahi shimbun",
            "毎日新聞",
            "mainichi",
            "読売新聞",
            "yomiuri",
            "日本経済新聞",
            "nikkei",
            "産経新聞",
            "sankei",
            "時事通信",
            "jiji press",
            "共同通信",
            "kyodo news",
            "東京新聞",
            "テレビ朝日",
            "tv asahi",
            "livedoor news",
            "日刊ゲンダイ",
            "スポニチ",
            "中日新聞",
            "北海道新聞",
            "西日本新聞",
        ),
    ),
    "zh_tw": RegionalSources(
        domains=(
            "udn.com",
            "ltn.com.tw",
            "cna.com.tw",
            "chinatimes.com",
            "storm.mg",
            "ettoday.net",
            "setn.com",
            "tvbs.com.tw",
            "tw.news.yahoo.com",
            "nownews.com",
            "cmmedia.com.tw",
            "mirrormedia.mg",
            "upmedia.mg",
            "newtalk.tw",
            "ftvnews.com.tw",
            "pts.org.tw",
            "technews.tw",
            "cw.com.tw",
            "bnext.com.tw",
            "msn.com",
        ),
        media_aliases=(
            "聯合報",
            "udn",
            "自由時報",
            "liberty times",
            "中央社",
            "cna",
            "中時新聞網",
            "china times",
            "風傳媒",
            "storm media",
            "ettoday",
            "三立新聞",
            "setn",
            "tvbs",
            "yahoo新聞",
            "yahoo 新聞",
            "nownews",
            "信傳媒",
            "鏡週刊",
            "mirror media",
            "上報",
            "newtalk",
            "民視新聞",
            "ftv news",
            "公視",
            "pts",
            "科技新報",
            "天下雜誌",
            "數位時代",
            "bnext",
        ),
    ),
}


def _normalize_host(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _host_matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith(f".{domain}")


def _media_matches(media: str, alias: str) -> bool:
    media_lower = media.lower().strip()
    alias_lower = alias.lower().strip()
    if not media_lower or not alias_lower:
        return False
    return alias_lower in media_lower or media_lower in alias_lower


def is_regional_top_source(url: str, media: str, market_id: str) -> bool:
    """True when URL host or media name matches a top-20 regional outlet."""
    sources = REGIONAL_SOURCES.get(market_id)
    if not sources:
        return False

    host = _normalize_host(url)
    for domain in sources.domains:
        if _host_matches(host, domain):
            return True

    media_stripped = (media or "").strip()
    if media_stripped:
        for alias in sources.media_aliases:
            if _media_matches(media_stripped, alias):
                return True
    return False
