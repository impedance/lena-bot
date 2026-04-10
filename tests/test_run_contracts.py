import importlib
from dataclasses import dataclass

from lena_bot.models import CriteriaResult, SearchResult
from lena_bot.providers.google_cse import should_fetch_page11

run_module = importlib.import_module("lena_bot.run")


@dataclass
class _DummyConn:
    closed: bool = False

    def close(self):
        self.closed = True


class _FakeProvider:
    def __init__(self, name: str, items: list[SearchResult], fetch_page11: bool = False):
        self.name = name
        self._items = items
        self._fetch_page11 = fetch_page11
        self.calls = []

    def search(self, query: str, start_index: int = 1, site_domains=None):
        self.calls.append(start_index)
        return list(self._items)

    def should_fetch_page11(self, page1_items_count: int, inserted_on_page1: int) -> bool:
        return self._fetch_page11


def _patch_minimal_loop(monkeypatch):
    monkeypatch.setattr(run_module, "SITE_GROUPS", [("TEST_GROUP", ["leboncoin.fr"], "")])
    monkeypatch.setattr(run_module, "build_queries", lambda level: [("GROUPE_A", "maison test")] )
    monkeypatch.setattr(run_module, "chunk_sites", lambda domains, max_len=1600: [domains])
    monkeypatch.setattr(run_module.time, "sleep", lambda *_: None)
    monkeypatch.setattr(run_module, "ENABLE_FALLBACK_QUERY", False)
    monkeypatch.setattr(run_module, "TG_TOKEN", "token")
    monkeypatch.setattr(run_module, "TG_CHAT", "chat")


def test_should_fetch_page11_thresholds():
    assert should_fetch_page11(page1_items_count=9, inserted_on_page1=0) is True
    assert should_fetch_page11(page1_items_count=0, inserted_on_page1=5) is True
    assert should_fetch_page11(page1_items_count=8, inserted_on_page1=4) is False


def test_run_skips_google_when_quota_reached(monkeypatch):
    provider = _FakeProvider("google_cse", items=[])
    conn = _DummyConn()

    _patch_minimal_loop(monkeypatch)
    monkeypatch.setattr(run_module, "build_enabled_providers", lambda: [provider])
    monkeypatch.setattr(run_module, "ensure_db", lambda: conn)
    monkeypatch.setattr(run_module, "get_cse_calls", lambda _conn: run_module.MAX_CSE_CALLS_PER_DAY)
    monkeypatch.setattr(run_module, "inc_cse_calls", lambda _conn, inc=1: None)
    monkeypatch.setattr(run_module, "insert_listing", lambda _conn, row: 1)
    monkeypatch.setattr(run_module, "write_run_csv", lambda rows: "fake.csv")
    monkeypatch.setattr(run_module, "telegram_send", lambda text: None)

    run_module.run()

    assert provider.calls == []
    assert conn.closed is True


def test_run_paginates_when_provider_requests_page11(monkeypatch):
    provider = _FakeProvider(
        "tavily",
        items=[
            SearchResult(
                url="https://leboncoin.fr/ad/ventes_immobilieres/123456",
                title="Maison Wasquehal",
                snippet="120 m2 4 chambres jardin",
                display_domain="leboncoin.fr",
            )
        ],
        fetch_page11=True,
    )
    conn = _DummyConn()
    inserted_rows = []
    sent_messages = []

    _patch_minimal_loop(monkeypatch)
    monkeypatch.setattr(run_module, "build_enabled_providers", lambda: [provider])
    monkeypatch.setattr(run_module, "ensure_db", lambda: conn)
    monkeypatch.setattr(run_module, "get_cse_calls", lambda _conn: 0)
    monkeypatch.setattr(run_module, "inc_cse_calls", lambda _conn, inc=1: None)
    monkeypatch.setattr(run_module, "insert_listing", lambda _conn, row: inserted_rows.append(row) or 1)
    monkeypatch.setattr(run_module, "criteria_check", lambda *args, **kwargs: CriteriaResult("OK", ""))
    monkeypatch.setattr(run_module, "write_run_csv", lambda rows: "fake.csv")
    monkeypatch.setattr(run_module, "telegram_send", lambda text: sent_messages.append(text))

    run_module.run()

    assert provider.calls == [1, 11]
    assert len(inserted_rows) == 2
    assert len(sent_messages) == 1


def test_run_smoke_excluded_results_do_not_send(monkeypatch):
    provider = _FakeProvider(
        "tavily",
        items=[
            SearchResult(
                url="https://leboncoin.fr/ad/ventes_immobilieres/987654",
                title="Maison",
                snippet="location",
                display_domain="leboncoin.fr",
            )
        ],
    )
    conn = _DummyConn()
    sent_messages = []
    csv_calls = []
    insert_calls = []

    _patch_minimal_loop(monkeypatch)
    monkeypatch.setattr(run_module, "build_enabled_providers", lambda: [provider])
    monkeypatch.setattr(run_module, "ensure_db", lambda: conn)
    monkeypatch.setattr(run_module, "get_cse_calls", lambda _conn: 0)
    monkeypatch.setattr(run_module, "inc_cse_calls", lambda _conn, inc=1: None)
    monkeypatch.setattr(run_module, "criteria_check", lambda *args, **kwargs: CriteriaResult("EXCLUDED", "rental"))
    monkeypatch.setattr(run_module, "insert_listing", lambda _conn, row: insert_calls.append(row) or 1)
    monkeypatch.setattr(run_module, "write_run_csv", lambda rows: csv_calls.append(rows) or "fake.csv")
    monkeypatch.setattr(run_module, "telegram_send", lambda text: sent_messages.append(text))

    run_module.run()

    assert provider.calls == [1]
    assert insert_calls == []
    assert sent_messages == []
    assert csv_calls == []
