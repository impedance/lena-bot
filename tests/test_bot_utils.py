import os
import sqlite3
import tempfile
import unittest


class TestBotUtils(unittest.TestCase):
    def test_normalize_url_strips_fragments_and_trackers(self):
        from bots_fonctionnels import bot_maisonRabotaetV1 as bot

        self.assertEqual(
            bot.normalize_url("https://example.com/x?utm_source=a&gclid=1#frag"),
            "https://example.com/x",
        )
        self.assertEqual(
            bot.normalize_url("https://example.com/x?fbclid=abc"),
            "https://example.com/x",
        )
        self.assertEqual(
            bot.normalize_url("https://example.com/x?utm_medium=a&keep=1"),
            "https://example.com/x?keep=1",
        )

    def test_domain_of(self):
        from bots_fonctionnels import bot_maisonRabotaetV1 as bot

        self.assertEqual(bot.domain_of("https://www.leboncoin.fr/abc"), "leboncoin.fr")
        self.assertEqual(bot.domain_of("https://LEBONCOIN.FR/abc"), "leboncoin.fr")

    def test_catalog_heuristics(self):
        from bots_fonctionnels import bot_maisonRabotaetV1 as bot

        self.assertTrue(bot.looks_like_catalog("https://www.leboncoin.fr/recherche?x=1", "100 annonces"))
        self.assertTrue(bot.looks_like_catalog("https://www.bienici.com/recherche", "Résultats"))
        self.assertFalse(bot.looks_like_catalog("https://www.leboncoin.fr/ad/ventes_immobilieres/123456", "Annonce"))

    def test_price_parsing(self):
        from bots_fonctionnels import bot_maisonRabotaetV1 as bot

        self.assertEqual(bot._price_to_int("349 000 €"), 349000)
        self.assertEqual(bot._price_to_int("349000 EUR"), 349000)
        self.assertIsNone(bot._price_to_int("prix sur demande"))

    def test_ensure_db_migrates_missing_columns(self):
        from bots_fonctionnels import bot_maisonRabotaetV1 as bot

        with tempfile.TemporaryDirectory() as d:
            db_path = os.path.join(d, "test.sqlite")

            # старая схема без price_eur / city / rooms / area_m2
            conn = sqlite3.connect(db_path)
            conn.execute(
                """
                CREATE TABLE listings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    title TEXT,
                    snippet TEXT,
                    source_domain TEXT,
                    query_group TEXT,
                    first_seen TEXT
                )
                """
            )
            conn.commit()
            conn.close()

            conn2 = bot.ensure_db(db_path=db_path)
            cols = {row[1] for row in conn2.execute("PRAGMA table_info(listings)")}
            conn2.close()

            for c in ["price_eur", "city", "rooms", "area_m2", "last_checked", "is_active"]:
                self.assertIn(c, cols)


if __name__ == "__main__":
    unittest.main()

