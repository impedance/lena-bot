from lena_bot.config import MIN_SURFACE
from lena_bot.filters.criteria import criteria_check


def _check(url: str, title: str, snippet: str, level: str = "STRICT"):
    return criteria_check(url=url, title=title, snippet=snippet, level=level)


def test_criteria_blackbox_matrix():
    cases = [
        (
            "excluded_apartment",
            _check("https://example.com/annonce", "Appartement T3", "Centre-ville"),
            "EXCLUDED",
            "apartment",
        ),
        (
            "excluded_rental",
            _check("https://example.com/location", "Maison à louer", "Disponible"),
            "EXCLUDED",
            "rental",
        ),
        (
            "excluded_city_disallowed",
            _check("https://example.com/house", "Maison", "Située à Roubaix, 120 m2 4 chambres jardin"),
            "EXCLUDED",
            "city_disallowed",
        ),
        (
            "excluded_surface_lt_min",
            _check("https://example.com/house", "Maison Wasquehal", "85 m2 4 chambres jardin"),
            "EXCLUDED",
            f"surface<{MIN_SURFACE}",
        ),
        (
            "excluded_bedrooms_lt_3",
            _check("https://example.com/house", "Maison Wasquehal", "120 m2 2 chambres jardin"),
            "EXCLUDED",
            "bedrooms<3",
        ),
        (
            "maybe_city",
            _check("https://example.com/house", "Maison", "120 m2 4 chambres jardin"),
            "MAYBE_CITY",
            "city_unknown",
        ),
        (
            "maybe_surface",
            _check("https://example.com/house", "Maison Wasquehal", "4 chambres jardin"),
            "MAYBE_SURFACE",
            "surface_missing",
        ),
        (
            "maybe_bedrooms",
            _check("https://example.com/house", "Maison Wasquehal", "120 m2 jardin"),
            "MAYBE_BEDROOMS",
            "bedrooms_missing",
        ),
        (
            "maybe_terrain",
            _check("https://example.com/house", "Maison Wasquehal", "120 m2 4 chambres"),
            "MAYBE_TERRAIN",
            "terrain_missing",
        ),
        (
            "ok",
            _check("https://example.com/house", "Maison Wasquehal", "120 m2 4 chambres avec jardin"),
            "OK",
            "",
        ),
    ]

    for _, result, expected_status, expected_note in cases:
        assert result.status == expected_status
        assert result.note == expected_note
