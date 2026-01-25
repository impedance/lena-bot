import os
import re
import time
import csv
import sqlite3
import logging
import requests
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

# ========== CONFIG ==========
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID  = os.getenv("GOOGLE_CSE_ID")

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT  = os.getenv("TELEGRAM_CHAT_ID")

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
-viager -"nue-propriété" -"nu-propriété" -"nue propriete" -"nu propriete" -"plain-pied" -"plain pied" -flamande
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

DB_PATH = "annonces_metropole_lille.sqlite"
SLEEP_BETWEEN_CALLS = 1.2
MAX_ITEMS_PER_RUN_TO_SEND = 25

# ========== LOGGING ==========
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

def configure_logging():
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

# ========== OUTILS ==========
def normalize_url(url: str) -> str:
    parts = urlsplit(url)
    filtered = []
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
        kl = (k or "").lower()
        if kl in {"gclid", "fbclid"} or kl.startswith("utm_"):
            continue
        filtered.append((k, v))
    query = urlencode(filtered, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))

def google_search(query: str, start_index: int = 1):
    r = requests.get(
        "https://www.googleapis.com/customsearch/v1",
        params={"key": GOOGLE_API_KEY, "cx": GOOGLE_CSE_ID, "q": query, "start": start_index},
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

def insert_listing(conn, url, title, snippet, domain, group):
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO listings
        (url, title, snippet, source_domain, query_group, first_seen)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (url, title, snippet, domain, group, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    return cur.rowcount

def telegram_send(text: str):
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": TG_CHAT, "text": text, "disable_web_page_preview": True},
        timeout=30
    )

def is_catalog_page(url: str, title: str) -> bool:
    if re.search(r"\b\d+\s+annonces?\b", title.lower()):
        return True
    if any(p in url for p in [
        "/immobilier/achat/",
        "/immobilier/vente/",
        "logic-immo.com/recherche-immo/",
        "leboncoin.fr/recherche",
        "bienici.com/recherche"
    ]):
        return True
    return False

def write_new_items_csv(items):
    if not items:
        return None

    now = datetime.now()
    filename = f"nouvelles_annonces_{now.strftime('%Y-%m-%d_%H%M%S')}.csv"

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([
            "date_detection",
            "heure_detection",
            "source_domain",
            "query_group",
            "title",
            "url"
        ])
        for d, t, u, g in items:
            w.writerow([
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S"),
                d, g, t, u
            ])
    return filename

# ========== MAIN ==========
def run():
    configure_logging()
    logger.info(
        "Запуск бота: script=%s db=%s queries=%d domains=%d",
        os.path.basename(__file__),
        DB_PATH,
        len(QUERIES),
        len(DOMAINS),
    )

    conn = ensure_db()
    new_items = []

    sites = " OR ".join(f"site:{d}" for d in DOMAINS)
    hint = '(inurl:annonce OR inurl:annonces OR inurl:listing) -"annonces" -"résultats"'

    for group, q in QUERIES:
        query = f"({sites}) {q} {hint}"
        for start in (1, 11):
            for it in google_search(query, start).get("items", []):
                url = normalize_url(it["link"])
                title = it.get("title", "")
                if is_catalog_page(url, title):
                    continue
                domain = it.get("displayLink", "").replace("www.", "")
                if insert_listing(conn, url, title, it.get("snippet", ""), domain, group):
                    new_items.append((domain, title, url, group))
            time.sleep(SLEEP_BETWEEN_CALLS)

    conn.close()

    if not new_items:
        print("ℹ️ Rien de nouveau.")
        return

    to_send = new_items[:MAX_ITEMS_PER_RUN_TO_SEND]
    csv_file = write_new_items_csv(to_send)
    print(f"📄 CSV créé : {csv_file}")

    msg = "🏡 Nouvelles annonces détectées\n\n"
    for d, t, u, _ in to_send:
        msg += f"• [{d}] {t}\n{u}\n\n"

    telegram_send(msg)
    print(f"✅ Envoyé sur Telegram : {len(to_send)} annonces")

if __name__ == "__main__":
    run()
