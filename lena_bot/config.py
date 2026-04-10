import os


def _load_local_env() -> None:
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        return

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key:
                    os.environ.setdefault(key, value)
    except OSError:
        return


_load_local_env()


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
SEARCH_PROVIDER_ORDER = os.getenv("SEARCH_PROVIDER_ORDER", "google_cse,tavily,brave")

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID")

DB_PATH = os.getenv("DB_PATH", "annonces_metropole_lille.sqlite")

MAX_CSE_CALLS_PER_DAY = int(os.getenv("MAX_CSE_CALLS_PER_DAY", "90"))
SLEEP_BETWEEN_CSE_CALLS = float(os.getenv("SLEEP_BETWEEN_CSE_CALLS", "1.2"))

RESOLVE_DIRECT_LINKS = os.getenv("RESOLVE_DIRECT_LINKS", "1").strip() == "1"
RESOLVE_TIMEOUT_SEC = float(os.getenv("RESOLVE_TIMEOUT_SEC", "10"))
MAX_RESOLVE_PER_RUN = int(os.getenv("MAX_RESOLVE_PER_RUN", "12"))

EXPAND_CATALOG_PAGES = os.getenv("EXPAND_CATALOG_PAGES", "1").strip() == "1"
MAX_CATALOG_EXPAND_PER_RUN = int(os.getenv("MAX_CATALOG_EXPAND_PER_RUN", "4"))
MAX_LINKS_PER_CATALOG_PAGE = int(os.getenv("MAX_LINKS_PER_CATALOG_PAGE", "8"))

MAX_ITEMS_PER_RUN_TO_SEND = int(os.getenv("MAX_ITEMS_PER_RUN_TO_SEND", "25"))
TELEGRAM_MAX_LEN = int(os.getenv("TELEGRAM_MAX_LEN", "3500"))

ENABLE_FALLBACK_QUERY = os.getenv("ENABLE_FALLBACK_QUERY", "1").strip() == "1"
ENABLE_CONDITIONAL_PAGINATION = os.getenv("ENABLE_CONDITIONAL_PAGINATION", "1").strip() == "1"

BUDGET_MAX = 380000
MIN_SURFACE = 90

CITIES_A = 'Wasquehal OR "Marcq-en-Barœul" OR "Marcq en Baroeul" OR Mouvaux OR Bondues OR Linselles'
CITIES_B = 'Lille OR Lambersart OR "Marquette-lez-Lille" OR "Marquette lez Lille" OR Hem OR "Villeneuve-d\'Ascq" OR Willems'

ALLOWED_CITIES = [
    "willems",
    "wasquehal",
    "marcq-en-barœul",
    "marcq en baroeul",
    "bondues",
    "marquette-lez-lille",
    "marquette lez lille",
    "mouvaux",
    "villeneuve-d'ascq",
    "villeneuve d'ascq",
    "lambersart",
    "linselles",
    "lille",
    "hem",
]

DISALLOWED_CITY_HINTS = [
    "tourcoing",
    "roubaix",
    "croix",
    "mons-en-barœul",
    "mons en baroeul",
    "wattrelos",
    "roncq",
    "halluin",
    "seclin",
    "faches",
    "lezennes",
    "loos",
    "wattignies",
    "lomme",
    "saint-andré",
    "saint andre",
    "wambrechies",
    "la madeleine",
    "madeleine",
]

BASE_FILTERS_STRICT = r"""
(maison OR "maison de ville" OR "semi-individuelle" OR "semi individuelle" OR "semi ind")
("3 chambres" OR "4 chambres" OR "3 ch" OR "4 ch" OR T4 OR T5)
(90 m² OR "90 m2" OR 95 m² OR "95 m2" OR 100 m² OR "100 m2" OR 110 m² OR "110 m2" OR 120 m² OR "120 m2")
(jardin OR terrain OR "extérieur" OR "exterieur")
(garage OR "box" OR "stationnement")
(gaz OR "chauffage gaz")
(sud OR "sud-ouest" OR "sud ouest" OR "sud-est" OR "sud est" OR SO OR SE)
("semi-mitoyenne" OR "semi mitoyenne" OR "mitoyenne 1 côté" OR "mitoyenne 1 cote" OR "semi-individuelle" OR "semi individuelle")
-viager -"nue-propriété" -"nu-propriété" -"nue propriete" -"nu propriete" -"plain-pied" -"plain pied" -flamande
""".strip().replace("\n", " ")

BASE_FILTERS_FALLBACK = r"""
(maison OR "maison de ville" OR "semi-individuelle" OR "semi individuelle" OR "semi ind")
("3 chambres" OR "4 chambres" OR "3 ch" OR "4 ch" OR T4 OR T5)
(90 m² OR "90 m2" OR 95 m² OR "95 m2" OR 100 m² OR "100 m2" OR 110 m² OR "110 m2" OR 120 m² OR "120 m2")
(jardin OR terrain OR "extérieur" OR "exterieur")
(garage OR "box" OR "stationnement")
-viager -"nue-propriété" -"nu-propriété" -"nue propriete" -"nu propriete" -"plain-pied" -"plain pied" -flamande
""".strip().replace("\n", " ")


def build_queries(level: str):
    base = BASE_FILTERS_STRICT if level == "STRICT" else BASE_FILTERS_FALLBACK
    return [
        ("GROUPE_A", f"({CITIES_A}) {base} {BUDGET_MAX}"),
        ("GROUPE_B", f"({CITIES_B}) {base} {BUDGET_MAX}"),
    ]


SITE_GROUPS = [
    (
        "LBC_VENTE",
        ["leboncoin.fr"],
        '(inurl:/ad/ventes_immobilieres OR inurl:/ad/achats_immobiliers) -inurl:/cl/ -inurl:/recherche -location -louer',
    ),
    (
        "PAP_VENTE",
        ["pap.fr"],
        '(inurl:/annonce/vente OR inurl:/annonces/vente) -location -louer -"location"',
    ),
    (
        "BIENICI_VENTE",
        ["bienici.com"],
        "(inurl:/annonce/ OR inurl:/annonce-vente) -inurl:/recherche -inurl:/resultats",
    ),
    (
        "LOGICIMMO_DETAIL",
        ["logic-immo.com"],
        "(inurl:detail-vente OR inurl:detail-vente-) -inurl:recherche-immo -inurl:recherche",
    ),
    (
        "FIGAROIMMO_ANNONCE",
        ["figaroimmo.fr"],
        "(inurl:annonce OR inurl:annonces OR inurl:detail OR inurl:bien) -inurl:recherche -inurl:resultats",
    ),
    (
        "AGENCES_LOCALES",
        [
            "abrinor.fr",
            "vacherand.fr",
            "immobiliere-duvieuxlille.com",
            "omer-baas.com",
            "nexim-immobilier.fr",
            "agencedemarcqenbaroeul.com",
            "immomarcq.fr",
            "wasquehal-immobilier.fr",
        ],
        "(inurl:vente OR inurl:bien OR inurl:annonce OR inurl:detail OR inurl:fiche) -inurl:location",
    ),
    ("ORPI", ["orpi.com"], "(inurl:annonce OR inurl:annonce-vente OR inurl:vente) -location"),
    ("LAFORET", ["laforet.com"], "(inurl:achat OR inurl:annonce OR inurl:bien) -location"),
    ("GUY_HOQUET", ["guy-hoquet.com"], "(inurl:achat OR inurl:annonce OR inurl:bien) -location"),
    (
        "CENTURY21",
        ["century21.fr"],
        "(inurl:detail OR inurl:trouver_logement OR inurl:bien) -location",
    ),
    ("NESTENN", ["nestenn.com"], "(inurl:vente OR inurl:bien OR inurl:annonce) -location"),
    ("SQUAREHABITAT", ["squarehabitat.fr"], "(inurl:annonce OR inurl:achat OR inurl:bien) -location"),
    (
        "PROMOTEURS",
        ["bouygues-immobilier.com", "nexity.fr"],
        "(inurl:programme OR inurl:logement OR inurl:immobilier OR inurl:annonce)",
    ),
]
