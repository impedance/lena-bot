import logging
import re

from lena_bot.config import MIN_SURFACE
from lena_bot.models import CriteriaResult
from lena_bot.utils.url_tools import city_presence, text_blob

logger = logging.getLogger(__name__)


RENTAL_WORDS = ["location", "à louer", "a louer", "louer", "/locations", "/location"]
APARTMENT_WORDS = ["appartement", "studio", "t2", "t3", "loft"]
EXCLUDE_WORDS = ["viager", "nue-propriété", "nu-propriété", "plain-pied", "plain pied", "flamande"]
NOT_HOUSE_WORDS = ["immeuble", "local commercial", "bureau", "fonds de commerce"]

SURFACE_RE = re.compile(r"(\d{2,3})\s*(m²|m2)\b", re.IGNORECASE)
CH_RE = re.compile(r"(\d)\s*(chambres?|ch)\b", re.IGNORECASE)


def criteria_check(url: str, title: str, snippet: str, level: str) -> CriteriaResult:
    text = text_blob(url, title, snippet)

    if any(w in text for w in EXCLUDE_WORDS):
        return CriteriaResult("EXCLUDED", "exclude_keyword")
    if any(w in text for w in RENTAL_WORDS):
        return CriteriaResult("EXCLUDED", "rental")
    if any(w in text for w in APARTMENT_WORDS):
        return CriteriaResult("EXCLUDED", "apartment")
    if any(w in text for w in NOT_HOUSE_WORDS):
        return CriteriaResult("EXCLUDED", "not_house")

    cp = city_presence(text)
    if level == "STRICT" and cp != "ALLOWED":
        if cp == "DISALLOWED":
            return CriteriaResult("EXCLUDED", "city_disallowed")
        return CriteriaResult("MAYBE_CITY", "city_unknown")
    if cp == "DISALLOWED":
        return CriteriaResult("EXCLUDED", "city_disallowed")

    surfaces = []
    for m in SURFACE_RE.findall(text):
        try:
            surfaces.append(int(m[0]))
        except ValueError:
            pass
    if surfaces and max(surfaces) < MIN_SURFACE:
        return CriteriaResult("EXCLUDED", f"surface<{MIN_SURFACE}")
    if not surfaces and level == "STRICT":
        return CriteriaResult("MAYBE_SURFACE", "surface_missing")

    ch = []
    for m in CH_RE.findall(text):
        try:
            ch.append(int(m[0]))
        except ValueError:
            pass
    if ch and max(ch) < 3:
        return CriteriaResult("EXCLUDED", "bedrooms<3")
    if not ch and level == "STRICT":
        return CriteriaResult("MAYBE_BEDROOMS", "bedrooms_missing")

    if ("jardin" not in text) and ("terrain" not in text) and ("extérieur" not in text) and ("exterieur" not in text):
        if level == "STRICT":
            return CriteriaResult("MAYBE_TERRAIN", "terrain_missing")

    return CriteriaResult("OK", "")
