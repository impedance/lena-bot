from collections.abc import Sequence

import requests

from lena_bot.config import TAVILY_API_KEY
from lena_bot.models import SearchResult
from lena_bot.providers.base import SearchProvider
from lena_bot.utils.url_tools import domain_of


class TavilyProvider(SearchProvider):
    name = "tavily"

    def is_enabled(self) -> bool:
        return bool(TAVILY_API_KEY)

    def search(
        self,
        query: str,
        start_index: int = 1,
        site_domains: Sequence[str] | None = None,
    ) -> list[SearchResult]:
        endpoint = "https://api.tavily.com/search"
        domains = list(site_domains or self.extract_site_domains(query))
        max_results = 20 if start_index > 1 else 10
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
        }
        if domains:
            payload["include_domains"] = domains

        response = requests.post(endpoint, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", []) or []
        if start_index > 1:
            results = results[10:20]

        out: list[SearchResult] = []
        for idx, item in enumerate(results, start=start_index):
            url = (item.get("url", "") or "").strip()
            if not url:
                continue
            out.append(
                SearchResult(
                    url=url,
                    title=(item.get("title", "") or "").strip(),
                    snippet=(item.get("content", "") or "").strip(),
                    display_domain=domain_of(url),
                    provider=self.name,
                    provider_rank=idx,
                    raw=item,
                )
            )
        return out
