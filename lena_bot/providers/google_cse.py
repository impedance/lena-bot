import requests

from lena_bot.config import ENABLE_CONDITIONAL_PAGINATION, GOOGLE_API_KEY, GOOGLE_CSE_ID
from lena_bot.models import SearchResult
from lena_bot.providers.base import SearchProvider
from lena_bot.utils.url_tools import domain_of


def google_search(query: str, start_index: int = 1):
    endpoint = "https://www.googleapis.com/customsearch/v1"
    params = {"key": GOOGLE_API_KEY, "cx": GOOGLE_CSE_ID, "q": query, "start": start_index}
    r = requests.get(endpoint, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def chunk_sites(domains, max_len=1600):
    chunks = []
    current, cur_len = [], 0
    for d in domains:
        part = f"site:{d}"
        add_len = len(part) + (4 if current else 0)
        if current and cur_len + add_len > max_len:
            chunks.append(current)
            current = [d]
            cur_len = len(part)
        else:
            current.append(d)
            cur_len += add_len
    if current:
        chunks.append(current)
    return chunks


def should_fetch_page11(page1_items_count: int, inserted_on_page1: int) -> bool:
    if not ENABLE_CONDITIONAL_PAGINATION:
        return True
    if page1_items_count >= 9:
        return True
    if inserted_on_page1 >= 5:
        return True
    return False


class GoogleCSEProvider(SearchProvider):
    name = "google_cse"

    def is_enabled(self) -> bool:
        return bool(GOOGLE_API_KEY and GOOGLE_CSE_ID)

    def search(self, query: str, start_index: int = 1, site_domains=None) -> list[SearchResult]:
        data = google_search(query, start_index=start_index)
        items = data.get("items", []) or []
        out: list[SearchResult] = []
        for idx, item in enumerate(items, start=start_index):
            url = (item.get("link", "") or "").strip()
            if not url:
                continue
            display_domain = (item.get("displayLink") or "").strip()
            if not display_domain:
                display_domain = domain_of(url)
            out.append(
                SearchResult(
                    url=url,
                    title=(item.get("title", "") or "").strip(),
                    snippet=(item.get("snippet", "") or "").strip(),
                    display_domain=display_domain,
                    provider=self.name,
                    provider_rank=idx,
                    raw=item,
                )
            )
        return out

    def should_fetch_page11(self, page1_items_count: int, inserted_on_page1: int) -> bool:
        return should_fetch_page11(page1_items_count, inserted_on_page1)
