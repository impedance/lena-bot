from lena_bot.utils.url_tools import (
    city_presence,
    domain_of,
    extract_direct_url_from_query,
    is_catalog_url,
    is_known_direct_url,
    normalize_url,
)


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


# --- domain_of() ---


def test_domain_of_strips_www():
    assert domain_of("https://www.logic-immo.com/detail-vente-123.htm") == "logic-immo.com"


def test_domain_of_returns_empty_on_bad_input():
    assert domain_of("") == ""


def test_domain_of_normalizes_case():
    assert domain_of("https://LeBonCoin.fr/ad/ventes_immobilieres/123") == "leboncoin.fr"


# --- city_presence() ---


def test_city_presence_allowed_city():
    assert city_presence("maison wasquehal 120 m2") == "ALLOWED"


def test_city_presence_disallowed_city():
    assert city_presence("maison roubaix 120 m2") == "DISALLOWED"


def test_city_presence_unknown():
    assert city_presence("maison 120 m2 jardin") == "UNKNOWN"


def test_city_presence_fallback_variant():
    # "marcq en baroeul" (without special characters) should still match
    assert city_presence("maison marcq en baroeul") == "ALLOWED"


# --- is_known_direct_url() ---


def test_is_known_direct_url_logic_immo():
    assert is_known_direct_url("https://www.logic-immo.com/detail-vente-42.htm") is True
    assert is_known_direct_url("https://www.logic-immo.com/recherche-immo/maison") is False


def test_is_known_direct_url_leboncoin():
    assert is_known_direct_url("https://www.leboncoin.fr/ad/ventes_immobilieres/2345678901") is True
    assert is_known_direct_url("https://www.leboncoin.fr/recherche") is False


def test_is_known_direct_url_pap():
    assert is_known_direct_url("https://www.pap.fr/annonce/vente-maison-lille-12345") is True
    assert is_known_direct_url("https://www.pap.fr/") is False


def test_is_known_direct_url_unknown_domain():
    assert is_known_direct_url("https://example.com/house") is False
