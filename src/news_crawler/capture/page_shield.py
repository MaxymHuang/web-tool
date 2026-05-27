from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import BrowserContext, Page

try:
    from adblock import Engine, FilterSet
except Exception:  # pragma: no cover - optional during early bootstrap
    Engine = None  # type: ignore[assignment]
    FilterSet = None  # type: ignore[assignment]

try:
    from playwright_cookie_blocker import block_cookie_dialogs
except Exception:  # pragma: no cover - optional during early bootstrap
    block_cookie_dialogs = None  # type: ignore[assignment]


FILTER_LIST_DIR = Path(__file__).resolve().parent / "filter_lists"
NETWORK_LIST_FILES = (
    "easylist.txt",
    "easyprivacy.txt",
    "fanboy-annoyance.txt",
    "easylist-japan.txt",
)
MAX_COSMETIC_SELECTORS = 2000

# Substrings that strongly indicate ad slots (token-safe; avoid bare "ad" in "address").
AD_IDENTIFIER_KEYWORDS: tuple[str, ...] = (
    "ad-slot",
    "ad_slot",
    "adslot",
    "ad-area",
    "ad_area",
    "adbox",
    "ad-box",
    "ad-wrapper",
    "ad_wrapper",
    "ad-container",
    "ad_container",
    "ad-banner",
    "ad_banner",
    "adsense",
    "adsbygoogle",
    "banner-ad",
    "sponsored",
    "outbrain",
    "taboola",
    "yjad",
    "google_ads",
    "google-ads",
    "pr-area",
    "pr_area",
    "広告",
)

FALSE_POSITIVE_TOKENS: frozenset[str] = frozenset(
    {
        "add",
        "address",
        "advance",
        "thread",
        "header",
        "read",
        "loading",
        "breadcrumb",
        "upload",
        "download",
        "shadow",
        "lead",
    }
)

_AD_BOUNDARY_RE = re.compile(
    r"(?:^|[-_])(?:ads?|advert(?:isement)?|banner|sponsor)(?:$|[-_])",
    re.IGNORECASE,
)

BLOCKED_FRAME_HOST_RE = re.compile(
    r"(?:doubleclick|googlesyndication|googleadservices|taboola|outbrain|"
    r"criteo|pubmatic|amazon-adsystem|ads\.yahoo|adnxs|rubiconproject)",
    re.IGNORECASE,
)

GENERIC_FALLBACK_CSS = """
iframe[src*="googlesyndication"],
iframe[src*="doubleclick"],
iframe[src*="googleadservices"],
iframe[src*="taboola"],
iframe[src*="outbrain"],
iframe[src*="criteo"],
[class*="ad-slot" i],
[id*="ad-slot" i],
[class*="ad_slot" i],
[id*="ad_slot" i],
[class*="ad-area" i],
[id*="ad-area" i] {
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  max-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  border: none !important;
  overflow: hidden !important;
}
"""


def looks_like_ad_identifier(text: str) -> bool:
    """Return True if class/id/data attribute name resembles an ad container."""
    if not text:
        return False
    if "広告" in text:
        return True
    lower = text.lower()
    for keyword in AD_IDENTIFIER_KEYWORDS:
        if keyword in lower:
            return True
    tokens = re.split(r"[-_.]+", lower)
    if any(token in FALSE_POSITIVE_TOKENS for token in tokens):
        return False
    return bool(_AD_BOUNDARY_RE.search(lower))


def element_attrs_suggest_ad(
    class_name: str = "",
    element_id: str = "",
    data_attrs: str = "",
) -> bool:
    return (
        looks_like_ad_identifier(class_name)
        or looks_like_ad_identifier(element_id)
        or looks_like_ad_identifier(data_attrs)
    )


def should_collapse_empty_slot(
    *,
    width: float,
    height: float,
    text_len: int,
    has_visible_media: bool,
    is_ad_identified: bool,
    only_empty_iframes: bool,
    min_area: float = 120 * 90,
) -> bool:
    """Python mirror of in-flow empty-slot heuristic (for unit tests)."""
    if has_visible_media:
        return False
    if width * height < min_area:
        return False
    if text_len >= 10:
        return False
    return is_ad_identified or only_empty_iframes


def _clean_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("!") or line.startswith("["):
            continue
        lines.append(line)
    return lines


def inject_generic_cosmetic_css(page: Page) -> None:
    try:
        page.add_style_tag(content=GENERIC_FALLBACK_CSS)
    except Exception:
        pass


def collapse_empty_ad_slots(page: Page) -> None:
    """Hide in-flow ad wrappers and empty iframes left after network blocking."""
    keywords_json = list(AD_IDENTIFIER_KEYWORDS)
    false_positives_json = list(FALSE_POSITIVE_TOKENS)
    blocked_hosts = (
        "doubleclick",
        "googlesyndication",
        "googleadservices",
        "taboola",
        "outbrain",
        "criteo",
        "pubmatic",
        "amazon-adsystem",
        "ads.yahoo",
    )
    page.evaluate(
        """
        ({ keywords, falsePositives, blockedHosts }) => {
          const MIN_AREA = 120 * 90;
          const MIN_BAR_WIDTH_RATIO = 0.05;
          const falsePositiveSet = new Set(falsePositives);

          const collapseEl = (el) => {
            if (!el || el === document.body || el === document.documentElement) return;
            el.style.setProperty("display", "none", "important");
            el.style.setProperty("height", "0", "important");
            el.style.setProperty("min-height", "0", "important");
            el.style.setProperty("max-height", "0", "important");
            el.style.setProperty("margin", "0", "important");
            el.style.setProperty("padding", "0", "important");
            el.style.setProperty("border", "none", "important");
            el.style.setProperty("overflow", "hidden", "important");
          };

          const tokens = (value) =>
            String(value || "")
              .toLowerCase()
              .split(/[-_.]+/)
              .filter(Boolean);

          const hasFalsePositiveToken = (value) => {
            for (const token of tokens(value)) {
              if (falsePositiveSet.has(token)) return true;
            }
            return false;
          };

          const looksLikeAd = (text) => {
            const raw = String(text || "");
            if (!raw) return false;
            if (raw.includes("広告")) return true;
            const lower = raw.toLowerCase();
            if (hasFalsePositiveToken(lower)) return false;
            for (const kw of keywords) {
              if (lower.includes(kw)) return true;
            }
            return /(?:^|[-_])(?:ads?|advert(?:isement)?|banner|sponsor)(?:$|[-_])/i.test(lower);
          };

          const attrBlob = (el) => {
            const parts = [el.id, el.className];
            for (const attr of el.attributes || []) {
              if (attr.name.startsWith("data-")) parts.push(attr.value);
            }
            return parts.join(" ");
          };

          const isBlockedFrameSrc = (src) => {
            const s = String(src || "").toLowerCase();
            if (!s) return false;
            return blockedHosts.some((h) => s.includes(h));
          };

          const hasVisibleMedia = (el) => {
            for (const node of el.querySelectorAll("img, video, canvas, picture")) {
              const rect = node.getBoundingClientRect();
              if (rect.width >= 40 && rect.height >= 40) return true;
            }
            return false;
          };

          const onlyEmptyIframes = (el) => {
            const children = Array.from(el.children);
            if (!children.length) return false;
            return children.every((child) => {
              if (child.tagName !== "IFRAME") return false;
              const rect = child.getBoundingClientRect();
              return rect.width * rect.height < 4;
            });
          };

          const isLargeEnough = (rect) => {
            const area = rect.width * rect.height;
            if (area >= MIN_AREA) return true;
            const vw = window.innerWidth || 1;
            return rect.width >= vw * MIN_BAR_WIDTH_RATIO && rect.height >= 50;
          };

          const isGreyPlaceholder = (style) => {
            const bg = style.backgroundColor || "";
            if (!bg || bg === "transparent" || bg === "rgba(0, 0, 0, 0)") return false;
            const m = bg.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)/i);
            if (!m) return bg.includes("#f") || bg.includes("#e");
            const r = Number(m[1]);
            const g = Number(m[2]);
            const b = Number(m[3]);
            return r >= 220 && g >= 220 && b >= 220;
          };

          const shouldCollapseInFlow = (el, style, rect) => {
            if (style.display === "none" || style.visibility === "hidden") return false;
            if (style.position === "fixed" || style.position === "sticky") return false;
            if (!isLargeEnough(rect)) return false;
            const textLen = (el.innerText || "").trim().length;
            if (textLen >= 10) return false;
            if (hasVisibleMedia(el)) return false;
            const adLike = looksLikeAd(attrBlob(el));
            const emptyFrames = onlyEmptyIframes(el);
            const greyBox = isGreyPlaceholder(style) && (adLike || emptyFrames);
            return adLike || emptyFrames || greyBox;
          };

          // Pass 1: ad-shaped containers
          for (const el of document.querySelectorAll("[id], [class], [data-ad], [data-ad-slot]")) {
            if (!looksLikeAd(attrBlob(el))) continue;
            const rect = el.getBoundingClientRect();
            if (rect.width < 40 || rect.height < 40) continue;
            collapseEl(el);
          }

          // Pass 2: empty / blocked iframes (+ parent wrapper when ad-like)
          for (const frame of document.querySelectorAll("iframe")) {
            const rect = frame.getBoundingClientRect();
            if (rect.width < 40 || rect.height < 40) continue;
            const src = frame.getAttribute("src") || "";
            const empty = !src.trim() || isBlockedFrameSrc(src);
            let emptyInside = false;
            try {
              emptyInside = !frame.contentDocument || !frame.contentDocument.body;
            } catch (_) {
              emptyInside = true;
            }
            if (!empty && !emptyInside) continue;
            collapseEl(frame);
            const parent = frame.parentElement;
            if (parent && looksLikeAd(attrBlob(parent))) collapseEl(parent);
          }

          // Pass 3: large empty in-flow blocks
          for (const el of document.querySelectorAll("div, section, aside, article, ins")) {
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            if (!shouldCollapseInFlow(el, style, rect)) continue;
            collapseEl(el);
          }

          // Trigger reflow
          void document.body.offsetHeight;
        }
        """,
        {
            "keywords": keywords_json,
            "falsePositives": false_positives_json,
            "blockedHosts": blocked_hosts,
        },
    )


class PageShield:
    def __init__(self) -> None:
        self._engine = self._build_engine()

    def _build_engine(self):
        if Engine is None or FilterSet is None:
            return None
        entries: list[str] = []
        for filename in NETWORK_LIST_FILES:
            entries.extend(_clean_lines(FILTER_LIST_DIR / filename))
        if not entries:
            return None
        try:
            filter_set = FilterSet(False)
            filter_set.add_filters(entries, "standard", False, "all")
            return Engine(filter_set, True)
        except Exception:
            return None

    def attach_to_context(self, context: BrowserContext) -> None:
        if self._engine is None:
            return

        def handle_route(route) -> None:
            request = route.request
            url = request.url
            source_url = request.frame.url or source_from_request(url)
            try:
                result = self._engine.check_network_urls(url, source_url, request.resource_type)
                should_block = bool(result.matched)
            except Exception:
                should_block = False
            if should_block:
                route.abort()
            else:
                route.continue_()

        context.route("**/*", handle_route)

    def prepare_page(self, page: Page) -> None:
        if block_cookie_dialogs is None:
            return
        try:
            block_cookie_dialogs(page)
        except Exception:
            return

    def apply_cosmetic(self, page: Page, page_url: str) -> None:
        inject_generic_cosmetic_css(page)
        if self._engine is not None:
            try:
                resources = self._engine.url_cosmetic_resources(page_url)
                selectors = set(resources.hide_selectors)
                dom = page.evaluate(
                    """
                    () => {
                      const classes = new Set();
                      const ids = new Set();
                      for (const node of document.querySelectorAll('[class], [id]')) {
                        if (node.id) ids.add(node.id);
                        for (const cls of node.classList || []) classes.add(cls);
                      }
                      return { classes: Array.from(classes), ids: Array.from(ids) };
                    }
                    """
                )
                dynamic_selectors = self._engine.hidden_class_id_selectors(
                    dom.get("classes", []),
                    dom.get("ids", []),
                    set(resources.exceptions),
                )
                selectors.update(dynamic_selectors)
                css_rules: list[str] = []
                for selector in list(selectors)[:MAX_COSMETIC_SELECTORS]:
                    css_rules.append(f"{selector} {{ display: none !important; }}")
                for selector, style in resources.style_selectors.items():
                    css_rules.append(f"{selector} {{ {style} }}")
                if css_rules:
                    page.add_style_tag(content="\n".join(css_rules))
            except Exception:
                pass
        try:
            collapse_empty_ad_slots(page)
        except Exception:
            pass
        page.evaluate(
            """
            () => {
              const maxRatio = 0.30;
              const viewportArea = Math.max(window.innerWidth * window.innerHeight, 1);

              const looksLikeAd = (text) => {
                const raw = String(text || "");
                if (!raw) return false;
                if (raw.includes("広告")) return true;
                const lower = raw.toLowerCase();
                return /(?:^|[-_])(?:ads?|advert|banner|sponsor|ad[-_]?slot|ad[-_]?area)(?:$|[-_])/i.test(lower)
                  || lower.includes("ad-slot") || lower.includes("ad_slot")
                  || lower.includes("outbrain") || lower.includes("taboola");
              };

              const nodes = document.querySelectorAll("*");
              for (const node of nodes) {
                const el = node;
                const style = window.getComputedStyle(el);
                if (style.display === "none" || style.visibility === "hidden") continue;
                const rect = el.getBoundingClientRect();
                const area = Math.max(rect.width * rect.height, 0);
                if (area / viewportArea < maxRatio) continue;
                const isOverlay = style.position === "fixed" || style.position === "sticky";
                const zIndex = Number.parseInt(style.zIndex || "0", 10);
                const highZ = Number.isFinite(zIndex) && zIndex >= 20;
                const adLike = looksLikeAd(el.id + " " + el.className);
                if (isOverlay && (highZ || adLike)) {
                  el.style.setProperty("display", "none", "important");
                }
              }
            }
            """
        )


def source_from_request(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return "https://example.com/"
    return f"{parsed.scheme}://{parsed.netloc}/"
