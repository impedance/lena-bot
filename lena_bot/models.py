from dataclasses import dataclass
from typing import Any


@dataclass
class CriteriaResult:
    status: str
    note: str


@dataclass
class SearchResult:
    url: str
    title: str = ""
    snippet: str = ""
    display_domain: str = ""
    provider: str = ""
    provider_rank: int = 0
    raw: dict[str, Any] | None = None
