from collections.abc import Sequence

import requests

from lena_bot.config import BRAVE_API_KEY
from lena_bot.models import SearchResult
from lena_bot.providers.base import SearchProvider
from lena_bot.providers.google_cse import should_fetch_page11
from lena_bot.utils.url_tools import domain_of


class BraveProvider(SearchProvider):
    name = "brave"

    def is_enabled(self) -> bool:
        return bool(BRAVE_API_KEY)

    def search(
        self,
        query: str,
        start_index: int = 1,
        site_domains: Sequence[str] | None = None,
    ) -> list[SearchResult]:
        endpoint = "https://api.search.brave.com/res/v1/web/search"
        offset = max(0, start_index - 1)
        params = {
            "q": query,
            "count": 10,
            "offset": offset,
        }
        headers = {
            "X-Subscription-Token": BRAVE_API_KEY or "",
            "Accept": "application/json",
        }
        response = requests.get(endpoint, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        results = ((data.get("web") or {}).get("results") or [])

        out: list[SearchResult] = []
        for idx, item in enumerate(results, start=start_index):
            url = (item.get("url", "") or "").strip()
            if not url:
                continue
            out.append(
                SearchResult(
                    url=url,
                    title=(item.get("title", "") or "").strip(),
                    snippet=(item.get("description", "") or "").strip(),
                    display_domain=domain_of(url),
                    provider=self.name,
                    provider_rank=idx,
                    raw=item,
                )
            )
        return out

    def should_fetch_page11(self, page1_items_count: int, inserted_on_page1: int) -> bool:
        return should_fetch_page11(page1_items_count, inserted_on_page1)
