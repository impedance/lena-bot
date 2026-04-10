import json
from pathlib import Path

from lena_bot.models import SearchResult
from lena_bot.providers.brave import BraveProvider
from lena_bot.providers.google_cse import GoogleCSEProvider
from lena_bot.providers.tavily import TavilyProvider

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class _MockResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _assert_contract(results, provider_name: str):
    assert len(results) == 1
    item = results[0]
    assert isinstance(item, SearchResult)
    assert item.url == "https://example.com/house-1"
    assert item.title == "Maison familiale"
    assert item.snippet == "Belle maison avec jardin."
    assert item.display_domain == "example.com"
    assert item.provider == provider_name
    assert item.provider_rank == 1
    assert isinstance(item.raw, dict)


def test_google_cse_normalization(monkeypatch):
    payload = _load_fixture("google_cse_response.json")

    def _fake_get(*args, **kwargs):
        return _MockResponse(payload)

    monkeypatch.setattr("lena_bot.providers.google_cse.requests.get", _fake_get)

    provider = GoogleCSEProvider()
    results = provider.search("test query", start_index=1)
    _assert_contract(results, "google_cse")


def test_tavily_normalization(monkeypatch):
    payload = _load_fixture("tavily_response.json")

    def _fake_post(*args, **kwargs):
        return _MockResponse(payload)

    monkeypatch.setattr("lena_bot.providers.tavily.requests.post", _fake_post)

    provider = TavilyProvider()
    results = provider.search("test query", start_index=1, site_domains=["example.com"])
    _assert_contract(results, "tavily")


def test_brave_normalization(monkeypatch):
    payload = _load_fixture("brave_response.json")

    def _fake_get(*args, **kwargs):
        return _MockResponse(payload)

    monkeypatch.setattr("lena_bot.providers.brave.requests.get", _fake_get)

    provider = BraveProvider()
    results = provider.search("test query", start_index=1)
    _assert_contract(results, "brave")
