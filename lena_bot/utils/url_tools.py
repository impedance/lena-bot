import re
from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse

import requests

from lena_bot.config import ALLOWED_CITIES, DISALLOWED_CITY_HINTS, RESOLVE_TIMEOUT_SEC


TRACKING_KEYS = {"gclid", "fbclid"}
TRACKING_PREFIXES = ("utm_",)


def normalize_url(url: str) -> str:
    if not url:
        return ""
    url = re.sub(r"#.*$", "", url).strip()
    try:
        p = urlparse(url)
        q = []
        for k, v in parse_qsl(p.query, keep_blank_values=True):
            lk = k.lower()
            if lk in TRACKING_KEYS:
                continue
            if any(lk.startswith(pref) for pref in TRACKING_PREFIXES):
                continue
            q.append((k, v))
        new_query = urlencode(q, doseq=True)
        p2 = p._replace(query=new_query)
        return urlunparse(p2).rstrip("?&")
    except Exception:
        return url


def domain_of(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        host = re.sub(r"^www\.", "", host)
        return host
    except Exception:
        return ""


def text_blob(url: str, title: str, snippet: str) -> str:
    return " ".join([(url or ""), (title or ""), (snippet or "")]).lower()


def city_presence(text: str) -> str:
    has_allowed = any(c in text for c in ALLOWED_CITIES)
    has_disallowed = any(c in text for c in DISALLOWED_CITY_HINTS)
    if has_allowed:
        return "ALLOWED"
    if has_disallowed:
        return "DISALLOWED"
    return "UNKNOWN"


CATALOG_PATTERNS_GENERIC = [
    r"/recherche",
    r"/search",
    r"/resultats?",
    r"/résultats?",
    r"/liste",
    r"/catalogue",
]

DOMAIN_CATALOG_PATTERNS = {
    "logic-immo.com": [r"/recherche-immo/"],
    "leboncoin.fr": [r"/cl/ventes_immobilieres", r"/cl/achats_immobiliers", r"/recherche"],
    "bienici.com": [r"/recherche"],
    "pap.fr": [r"/recherche"],
    "abrinor.fr": [r"/acheter-un-bien", r"/achat-immobilier", r"\?page=\d+"],
    "immomarcq.fr": [r"/vente/maison/?$", r"/vente/maison/[^/]+/?$", r"/location", r"/vendu"],
    "wasquehal-immobilier.fr": [r"/$"],
}

DIRECT_URL_ALLOWLIST = {
    "logic-immo.com": [r"/detail-vente-\d+\.htm"],
    "leboncoin.fr": [r"/ad/ventes_immobilieres/\d+", r"/ad/achats_immobiliers/\d+"],
    "pap.fr": [r"/annonce/vente-[^/]+-\d+"],
    "bienici.com": [r"/annonce/[^/?#]+"],
    "abrinor.fr": [r"/vente-[^/?#]+"],
}


def is_known_direct_url(url: str) -> bool:
    d = domain_of(url)
    u = (url or "").lower()
    return any(re.search(p, u) for p in DIRECT_URL_ALLOWLIST.get(d, []))


def is_homepage(url: str) -> bool:
    try:
        p = urlparse(url)
        return (p.path in ("", "/")) and not p.query and not p.fragment
    except Exception:
        return False


def is_catalog_url(url: str, title: str = "") -> bool:
    u = (url or "").lower()
    t = (title or "").lower()
    if is_homepage(url):
        return True
    if re.search(r"\b\d+\s+annonces?\b", t):
        return True
    if any(re.search(p, u) for p in CATALOG_PATTERNS_GENERIC):
        return True
    d = domain_of(url)
    return any(re.search(p, u) for p in DOMAIN_CATALOG_PATTERNS.get(d, []))


URL_PARAM_CANDIDATES = {"url", "u", "redir", "redirect", "redirect_url", "destination", "dest"}


def extract_direct_url_from_query(original_url: str) -> str:
    try:
        p = urlparse(original_url)
        q = dict(parse_qsl(p.query, keep_blank_values=True))
        for k, v in q.items():
            if k.lower() in URL_PARAM_CANDIDATES and v:
                cand = unquote(v).strip()
                if cand.startswith("http://") or cand.startswith("https://"):
                    return normalize_url(cand)
        return ""
    except Exception:
        return ""


CANONICAL_RE = re.compile(
    r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
OGURL_RE = re.compile(
    r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def resolve_direct_url_soft(original_url: str, session: requests.Session) -> tuple[str, str]:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) maison_bot/2.1"}
        r = session.get(original_url, timeout=RESOLVE_TIMEOUT_SEC, headers=headers, allow_redirects=True)
        html = (r.text or "")[:300000]

        m = CANONICAL_RE.search(html)
        if m:
            cand = normalize_url(m.group(1).strip())
            if cand and cand != original_url:
                return cand, "canonical"

        m = OGURL_RE.search(html)
        if m:
            cand = normalize_url(m.group(1).strip())
            if cand and cand != original_url:
                return cand, "og:url"

        final_url = normalize_url(getattr(r, "url", "") or "")
        if final_url and final_url != original_url:
            return final_url, "redirect"

        return "", "no_canonical"
    except Exception:
        return "", "resolve_error"


HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)


def expand_catalog_page(url: str, session: requests.Session, max_links: int) -> list[str]:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) maison_bot/2.1"}
        r = session.get(url, timeout=RESOLVE_TIMEOUT_SEC, headers=headers, allow_redirects=True)
        html = (r.text or "")[:250000]
        base = urlparse(url)
        domain = base.netloc

        out = []
        for href in HREF_RE.findall(html):
            href = href.strip()
            if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
                continue
            if href.startswith("//"):
                cand = "https:" + href
            elif href.startswith("http://") or href.startswith("https://"):
                cand = href
            elif href.startswith("/"):
                cand = f"{base.scheme}://{domain}{href}"
            else:
                path = base.path.rsplit("/", 1)[0] + "/" + href
                cand = f"{base.scheme}://{domain}{path}"

            cand = normalize_url(cand)
            if domain_of(cand) != domain_of(url):
                continue

            cl = cand.lower()
            if any(x in cl for x in ("/vente", "/annonce", "/bien", "detail", "fiche")) and len(cl) > 25:
                if not is_catalog_url(cand):
                    out.append(cand)
            if len(out) >= max_links:
                break

        seen, uniq = set(), []
        for item in out:
            if item in seen:
                continue
            seen.add(item)
            uniq.append(item)
        return uniq
    except Exception:
        return []
