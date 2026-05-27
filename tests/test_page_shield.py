from news_crawler.capture.page_shield import (
    PageShield,
    element_attrs_suggest_ad,
    looks_like_ad_identifier,
    should_collapse_empty_slot,
)


class _FakeFrame:
    def __init__(self, url: str) -> None:
        self.url = url


class _FakeRequest:
    def __init__(self, url: str, frame_url: str, resource_type: str) -> None:
        self.url = url
        self.frame = _FakeFrame(frame_url)
        self.resource_type = resource_type


class _FakeRoute:
    def __init__(self, request: _FakeRequest) -> None:
        self.request = request
        self.aborted = False
        self.continued = False

    def abort(self) -> None:
        self.aborted = True

    def continue_(self) -> None:
        self.continued = True


class _FakeContext:
    def __init__(self) -> None:
        self.handler = None

    def route(self, _pattern: str, handler) -> None:
        self.handler = handler


def test_looks_like_ad_identifier_matches_common_slots():
    assert looks_like_ad_identifier("ad-wrapper")
    assert looks_like_ad_identifier("sidebar-ad-slot")
    assert looks_like_ad_identifier("広告バナー")
    assert looks_like_ad_identifier("yjAdContainer")


def test_looks_like_ad_identifier_rejects_false_positives():
    assert not looks_like_ad_identifier("address-book")
    assert not looks_like_ad_identifier("thread-list")
    assert not looks_like_ad_identifier("breadcrumb")


def test_element_attrs_suggest_ad_combines_id_and_class():
    assert element_attrs_suggest_ad(class_name="content", element_id="ad-leaderboard")
    assert not element_attrs_suggest_ad(class_name="article-body", element_id="main")


def test_should_collapse_empty_slot_for_ad_like_box():
    assert should_collapse_empty_slot(
        width=300,
        height=250,
        text_len=0,
        has_visible_media=False,
        is_ad_identified=True,
        only_empty_iframes=False,
    )


def test_should_collapse_empty_slot_skips_article_media():
    assert not should_collapse_empty_slot(
        width=300,
        height=250,
        text_len=0,
        has_visible_media=True,
        is_ad_identified=True,
        only_empty_iframes=False,
    )


def test_should_collapse_empty_slot_for_empty_iframe_wrapper():
    assert should_collapse_empty_slot(
        width=728,
        height=90,
        text_len=0,
        has_visible_media=False,
        is_ad_identified=False,
        only_empty_iframes=True,
    )


def test_page_shield_blocks_known_ad_host():
    shield = PageShield()
    context = _FakeContext()
    shield.attach_to_context(context)
    assert context.handler is not None
    route = _FakeRoute(
        _FakeRequest(
            "https://googleads.g.doubleclick.net/pagead/ads.js",
            "https://example.com/news",
            "script",
        )
    )
    context.handler(route)
    assert route.aborted is True
    assert route.continued is False


def test_page_shield_collects_cosmetic_selectors():
    shield = PageShield()
    assert shield._engine is not None
    resources = shield._engine.url_cosmetic_resources("https://example.com")
    assert any("cookie" in selector for selector in resources.hide_selectors)
