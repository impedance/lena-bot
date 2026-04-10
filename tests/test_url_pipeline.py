from lena_bot.utils.url_tools import extract_direct_url_from_query, is_catalog_url, normalize_url


def test_normalize_url_strips_tracking_and_fragment():
    url = "https://example.com/path?utm_source=google&gclid=abc&id=42#section"
    assert normalize_url(url) == "https://example.com/path?id=42"


def test_extract_direct_url_from_query_uses_embedded_url():
    wrapped = "https://example.com/redirect?url=https%3A%2F%2Ftarget.com%2Fad%3Futm_medium%3Dcpc%26id%3D7"
    assert extract_direct_url_from_query(wrapped) == "https://target.com/ad?id=7"


def test_is_catalog_url_detects_homepage_and_search_path():
    assert is_catalog_url("https://pap.fr/") is True
    assert is_catalog_url("https://bienici.com/recherche/achat/lille") is True
    assert is_catalog_url("https://leboncoin.fr/ad/ventes_immobilieres/123456789") is False
