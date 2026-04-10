import re
from abc import ABC, abstractmethod
from collections.abc import Sequence

from lena_bot.models import SearchResult


SITE_RE = re.compile(r"\bsite:([^\s()]+)")


class SearchProvider(ABC):
    name = "base"

    @abstractmethod
    def is_enabled(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query: str,
        start_index: int = 1,
        site_domains: Sequence[str] | None = None,
    ) -> list[SearchResult]:
        raise NotImplementedError

    def should_fetch_page11(self, page1_items_count: int, inserted_on_page1: int) -> bool:
        return True

    @staticmethod
    def extract_site_domains(query: str) -> list[str]:
        out = []
        for match in SITE_RE.findall(query or ""):
            domain = match.strip().strip(".,;:)")
            if not domain:
                continue
            out.append(domain)
        return out
