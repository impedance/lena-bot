import os
import re
import time
import csv
import json
import sqlite3
import logging
import requests
from datetime import datetime
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit, parse_qsl, urlencode

# ================= CONFIG =================
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID  = os.getenv("GOOGLE_CSE_ID")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT  = os.getenv("TELEGRAM_CHAT_ID")

DB_PATH = "annonces_metropole_lille.sqlite"

SLEEP = 1.5
MAX_SEND = 25
DEBUG = True

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.7",
}

# ================= LOGGING =================
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

def configure_logging():
    """
    Настраивает logging один раз.
    Управление:
      - BOT_LOG_LEVEL (по умолчанию INFO)
      - BOT_LOG_FILE  (если задан, пишет также в файл)
    """
    root = logging.getLogger()
    if root.handlers:
        return

    level_name = (os.getenv("BOT_LOG_LEVEL") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handlers = [logging.StreamHandler()]
    log_file = os.getenv("BOT_LOG_FILE")
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )

# ================= YOUR SEARCH PARAMS =================
BUDGET = "350000"

CITIES_A = 'Wasquehal OR "Marcq-en-Barœul" OR "Marcq en Baroeul" OR Mouvaux OR Bondues OR Linselles'
CITIES_B = 'Lille OR Lambersart OR "Marquette-lez-Lille" OR "Marquette lez Lille" OR Hem OR "Villeneuve-d\'Ascq" OR Willems'

BASE_FILTERS = r'''
(maison OR "maison de ville")
(garage)
("semi-mitoyenne" OR "semi mitoyenne" OR "mitoyenne 1 côté" OR "mitoyenne 1 cote")
("3 chambres" OR "4 chambres" OR T4 OR T5)
(85 m² OR "85 m2" OR 90 m² OR "90 m2" OR 95 m² OR 100 m² OR "100 m2")
("100 m²" OR "100 m2" OR 120 m² OR "120 m2" OR 150 m² OR "150 m2" OR jardin)
(gaz OR "chauffage gaz")
(sud OR "sud-ouest" OR "sud ouest" OR "sud-est" OR "sud est" OR SO OR SE)
-viager -"nue-propriété" -"nu-propriété" -"nue propriete" -"nu propriete"
-"plain-pied" -"plain pied" -flamande
'''.strip().replace("\n", " ")

QUERIES = [
    ("GROUPE_A", f'({CITIES_A}) {BASE_FILTERS} {BUDGET}'),
    ("GROUPE_B", f'({CITIES_B}) {BASE_FILTERS} {BUDGET}'),
]

DOMAINS = [
    "bienici.com",
    "leboncoin.fr",
    "logic-immo.com",
    "pap.fr",
    "figaroimmo.fr",
    "abrinor.fr",
    "vacherand.fr",
    "immobiliere-duvieuxlille.com",
    "omer-baas.com",
    "nexim-immobilier.fr",
    "agencedemarcqenbaroeul.com",
    "immomarcq.fr",
    "wasquehal-immobilier.fr",
    "orpi.com",
    "laforet.com",
    "guy-hoquet.com",
    "century21.fr",
    "nestenn.com",
    "squarehabitat.fr",
    "bouygues-immobilier.com",
    "nexity.fr",
]

# ================= UTILS =================
def normalize_url(url: str) -> str:
    """
    Удаляет фрагменты и типичные трекинг-параметры, сохраняя остальные query-параметры.
    """
    parts = urlsplit(url)
    filtered = []
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
        kl = (k or "").lower()
        if kl in {"gclid", "fbclid"} or kl.startswith("utm_"):
            continue
        filtered.append((k, v))
    query = urlencode(filtered, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))

def domain_of(url: str) -> str:
    try:
        d = urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        d = ""
    return d

def google_search(q: str, start: int):
    r = requests.get(
        "https://www.googleapis.com/customsearch/v1",
        params={"key": GOOGLE_API_KEY, "cx": GOOGLE_CSE_ID, "q": q, "start": start},
        timeout=30
    )
    r.raise_for_status()
    return r.json()

def _ensure_columns(conn: sqlite3.Connection, table: str, columns: list[tuple[str, str]]):
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    for name, typ in columns:
        if name in existing:
            continue
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ}")
    conn.commit()

def ensure_db(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            snippet TEXT,
            source_domain TEXT,
            query_group TEXT,
            first_seen TEXT
        )
    """)
    conn.commit()

    _ensure_columns(conn, "listings", [
        ("price_eur", "INTEGER"),
        ("city", "TEXT"),
        ("rooms", "INTEGER"),
        ("area_m2", "REAL"),
        ("last_checked", "TEXT"),
        ("is_active", "INTEGER"),
    ])
    return conn

def insert(conn, url, title, snippet, price_eur, dom, group):
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO listings
        (url, title, snippet, price_eur, source_domain, query_group, first_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (url, title, snippet, price_eur, dom, group, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    return cur.rowcount

def telegram(msg: str):
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": TG_CHAT, "text": msg, "disable_web_page_preview": True},
        timeout=30
    )

# ================= LISTING VS CATALOG HEURISTICS =================
LIST_MARKERS = [
    "/recherche", "/recherche-", "recherche-immo",
    "search", "resultat", "resultats", "résultats",
    "liste", "listing", "listings", "catalogue",
    "annonces/?", "annonces?", "page=", "tri=", "sort=", "prixmin", "prixmax",
]

def looks_like_catalog(url: str, title: str) -> bool:
    u = (url or "").lower()
    t = (title or "").lower()

    if any(m in u for m in LIST_MARKERS):
        return True

    # Частые "не-объявления" (оценка/цены/статистика)
    if "seloger.com/prix-de-l-immo/" in u:
        return True
    if "seloger.com/estimation" in u or "seloger.com/estimer" in u:
        return True
    if any(x in t for x in ["prix m2", "prix du m2", "baromètre", "barometre", "estimation", "estimer"]):
        return True

    # Заголовки-списки
    if re.search(r"\b\d+\s+annonces?\b", t):
        if any(w in t for w in ["résultats", "resultats", "liste", "sélection", "selection", "page"]):
            return True

    # Некоторые явные поисковые пути
    if "leboncoin.fr/recherche" in u:
        return True
    if "bienici.com/recherche" in u:
        return True
    if "logic-immo.com/recherche-immo/" in u:
        return True

    return False

def looks_like_listing_path(url: str) -> bool:
    """Проверка: путь похож на карточку (мягко, без жёсткой привязки)."""
    u = (url or "").lower()
    if looks_like_catalog(u, ""):
        return False
    # частые маркеры карточек
    return any(k in u for k in [
        "/annonce", "/annonces/", "/ad/", "/ads/", "/detail", "/details",
        "/vente/", "/achat/", "/immobilier/", "/biens/", "/bien/", "/property"
    ])

# ================= HTML PARSING (без обязательных зависимостей) =================
def fetch(url: str):
    r = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
    r.raise_for_status()
    return r.url, r.text

def extract_canonical_and_og(html: str):
    canonical = None
    og = None

    m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', html, re.I)
    if m:
        canonical = m.group(1).strip()

    m = re.search(r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if m:
        og = m.group(1).strip()

    return canonical, og

def parse_json_ld_blocks(html: str):
    blocks = []
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.I | re.S):
        raw = m.group(1).strip()
        if not raw:
            continue
        try:
            blocks.append(json.loads(raw))
        except Exception:
            # иногда там несколько JSON подряд или мусор
            continue
    return blocks

def _walk_json(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk_json(v)
    elif isinstance(obj, list):
        for x in obj:
            yield from _walk_json(x)

def extract_price_from_jsonld(jsonld) -> int | None:
    """
    Ищем price / offers.price / priceSpecification.price.
    Возвращаем int (EUR) если получилось.
    """
    for node in _walk_json(jsonld):
        if not isinstance(node, dict):
            continue

        # прямое price
        if "price" in node:
            p = node.get("price")
            pe = _price_to_int(p)
            if pe:
                return pe

        # offers
        offers = node.get("offers")
        if isinstance(offers, dict):
            pe = _price_to_int(offers.get("price"))
            if pe:
                return pe
            ps = offers.get("priceSpecification")
            pe = _price_to_int(ps.get("price") if isinstance(ps, dict) else None)
            if pe:
                return pe
        elif isinstance(offers, list):
            for off in offers:
                if isinstance(off, dict):
                    pe = _price_to_int(off.get("price"))
                    if pe:
                        return pe

    return None

def _price_to_int(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        v = int(value)
        return v if v > 0 else None
    if isinstance(value, str):
        s = value
        s = s.replace("\xa0", " ").replace("€", "").replace("EUR", "").replace("eur", "")
        s = s.strip()
        m = re.search(r"(\d[\d\s.,]{2,})", s)
        if not m:
            return None
        digits = re.sub(r"[^\d]", "", m.group(1))
        if not digits:
            return None
        v = int(digits)
        return v if v > 0 else None
    return None

def extract_price_from_text(html: str) -> int | None:
    # Находим что-то типа "349 000 €" / "349000 €"
    m = re.search(r"(\d[\d\s\xa0.,]{2,})\s*(€|eur)\b", html, re.I)
    if not m:
        return None
    digits = re.sub(r"[^\d]", "", m.group(1))
    if not digits:
        return None
    v = int(digits)
    return v if v > 0 else None

def extract_links(html: str, base_url: str) -> list[str]:
    hrefs = []
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\']', html, re.I):
        h = m.group(1).strip()
        if not h or h.startswith("#") or h.startswith("mailto:") or h.startswith("tel:"):
            continue
        full = urljoin(base_url, h)
        hrefs.append(full)
    return hrefs

def pick_best_listing_link(candidates: list[str], base_domain: str) -> str | None:
    # фильтруем только тот же домен + похоже на карточку
    cleaned = []
    for u in candidates:
        nu = normalize_url(u)
        if domain_of(nu) != base_domain:
            continue
        if looks_like_listing_path(nu):
            cleaned.append(nu)

    if not cleaned:
        return None

    # скоринг: длиннее путь + наличие цифр (ID) + меньше query params
    def score(u: str) -> int:
        p = urlparse(u)
        path = p.path or ""
        has_id = 1 if re.search(r"\d{4,}", path) else 0
        qpen = 0 if not p.query else -2
        return len(path) + 25 * has_id + qpen

    cleaned = sorted(set(cleaned), key=score, reverse=True)
    return cleaned[0]

# ================= RESOLVE: "прямо на карточку" =================
def resolve_to_listing(url: str, title: str) -> tuple[str, int | None, str]:
    """
    Возвращает (final_listing_url, price_eur_or_None, reason)
    """
    url = normalize_url(url)
    dom = domain_of(url)

    # 1) Если уже похоже на карточку — всё равно попробуем вытащить цену
    try_fetch = True

    # 2) Если похоже на каталог — точно надо "дораскрывать"
    if looks_like_catalog(url, title):
        try_fetch = True

    if not try_fetch:
        return url, None, "no_fetch"

    try:
        final_url, html = fetch(url)
        final_url = normalize_url(final_url)
    except Exception as e:
        return url, None, f"fetch_error:{type(e).__name__}"

    # 3) canonical / og:url
    canonical, og = extract_canonical_and_og(html)
    for u in [canonical, og]:
        if u:
            nu = normalize_url(u)
            if domain_of(nu) == dom and looks_like_listing_path(nu):
                # цена из этой страницы (мы уже её скачали, но canonical может отличаться)
                price = None
                jsonlds = parse_json_ld_blocks(html)
                for j in jsonlds:
                    price = extract_price_from_jsonld(j)
                    if price:
                        break
                if not price:
                    price = extract_price_from_text(html)
                return nu, price, "canonical_or_og"

    # 4) JSON-LD: иногда содержит url карточки и/или цену
    price = None
    jsonlds = parse_json_ld_blocks(html)
    for j in jsonlds:
        if price is None:
            price = extract_price_from_jsonld(j)

        # пытаемся найти url внутри jsonld
        for node in _walk_json(j):
            if isinstance(node, dict) and "url" in node:
                nu = normalize_url(str(node.get("url")))
                if domain_of(nu) == dom and looks_like_listing_path(nu):
                    return nu, price, "jsonld_url"

    # 5) Если это каталог/поиск — пробуем вытащить лучшую ссылку-карточку со страницы
    links = extract_links(html, final_url)
    best = pick_best_listing_link(links, dom)
    if best:
        # иногда цена видна прямо в списке: попробуем взять из текста текущей страницы
        if price is None:
            price = extract_price_from_text(html)
        return best, price, "best_link_in_page"

    # 6) Фоллбек: остаёмся на final_url, но цена может быть в тексте/JSONLD
    if price is None:
        price = extract_price_from_text(html)
    return final_url, price, "fallback_final"

# ================= CSV =================
def write_csv(items):
    if not items:
        return None
    now = datetime.now()
    fname = f"nouvelles_annonces_{now.strftime('%Y-%m-%d_%H%M%S')}.csv"
    with open(fname, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["date_detection", "heure_detection", "source_domain", "query_group", "price_eur", "title", "url"])
        for row in items:
            dom, group, price_eur, title, url = row
            w.writerow([now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), dom, group, price_eur or "", title, url])
    return fname

# ================= MAIN =================
def run():
    configure_logging()
    logger.info(
        "Запуск бота: script=%s db=%s queries=%d domains=%d",
        os.path.basename(__file__),
        DB_PATH,
        len(QUERIES),
        len(DOMAINS),
    )

    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        raise SystemExit("❌ Нужно выставить GOOGLE_API_KEY и GOOGLE_CSE_ID.")
    if not TG_TOKEN or not TG_CHAT:
        raise SystemExit("❌ Нужно выставить TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID.")

    conn = ensure_db()
    new_items = []

    sites = " OR ".join(f"site:{d}" for d in DOMAINS)

    buy_signal = '(vente OR "à vendre" OR "a vendre" OR acheter)'
    negative_strong = (
        '-"prix-de-l-immo" -"prix de l\'immo" -"estimation" -"baromètre" -"barometre" '
        '-"prix m2" -"prix du m2" '
        '-inurl:recherche -inurl:search -inurl:resultat -inurl:resultats -inurl:résultats '
        '-location -"à louer" -"a louer" -louer '
        '-locaux -local -bureaux -bureau -commercial -commerce '
    )
    positive_soft = '(("€" OR EUR OR "m²" OR "m2" OR chambre OR chambres) OR (inurl:annonce OR inurl:ad OR inurl:detail))'
    hint = f"{buy_signal} {positive_soft} {negative_strong}"

    stats = {
        "google_items": 0,
        "resolved": 0,
        "inserted_new": 0,
        "duplicate": 0,
        "fetch_errors": 0
    }
    reasons = {}

    for group, q in QUERIES:
        query = f"({sites}) {q} {hint}"

        for start in (1, 11, 21):
            data = google_search(query, start)
            items = data.get("items", [])
            stats["google_items"] += len(items)

            for it in items:
                raw_url = it.get("link", "") or ""
                if not raw_url:
                    continue
                raw_url = normalize_url(raw_url)
                title = it.get("title", "") or ""
                snippet = it.get("snippet", "") or ""

                final_url, price_eur, reason = resolve_to_listing(raw_url, title)
                reasons[reason] = reasons.get(reason, 0) + 1
                stats["resolved"] += 1

                if reason.startswith("fetch_error"):
                    stats["fetch_errors"] += 1

                dom = domain_of(final_url)

                rc = insert(conn, final_url, title, snippet, price_eur, dom, group)
                if rc == 1:
                    stats["inserted_new"] += 1
                    new_items.append((dom, group, price_eur, title, final_url))
                else:
                    stats["duplicate"] += 1

                time.sleep(0.3)

            time.sleep(SLEEP)

    conn.close()

    if DEBUG:
        print("\n=== DEBUG STATS ===")
        print(stats)
        print("\n=== RESOLVE REASONS ===")
        for k, v in sorted(reasons.items(), key=lambda x: x[1], reverse=True):
            print(f"{k}: {v}")

    logger.info(
        "Итоги: google_items=%d resolved=%d new=%d dup=%d fetch_errors=%d",
        stats["google_items"],
        stats["resolved"],
        stats["inserted_new"],
        stats["duplicate"],
        stats["fetch_errors"],
    )

    if not new_items:
        print("ℹ️ Rien de nouveau.")
        return

    to_send = new_items[:MAX_SEND]
    csv_file = write_csv(to_send)
    print(f"📄 CSV créé : {csv_file}")

    msg = "🏡 Nouvelles annonces détectées\n\n"
    for dom, group, price, title, url in to_send:
        ptxt = f"{price:,} €".replace(",", " ") if isinstance(price, int) else "prix ?"
        msg += f"• [{dom}] ({group}) {ptxt}\n{title}\n{url}\n\n"

    telegram(msg)
    print(f"✅ Envoyé sur Telegram : {len(to_send)} annonces")

if __name__ == "__main__":
    run()
