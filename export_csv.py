import sqlite3
import csv
from datetime import date

DB_PATH = "annonces_metropole_lille.sqlite"

def export_csv(filename, where_sql="", params=()):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(f"""
        SELECT first_seen, source_domain, query_group, title, url, snippet
        FROM listings
        {where_sql}
        ORDER BY first_seen DESC
    """, params)

    rows = cur.fetchall()
    conn.close()

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["first_seen", "source_domain", "query_group", "title", "url", "snippet"])
        w.writerows(rows)

    print(f"✅ {filename} créé ({len(rows)} lignes)")

if __name__ == "__main__":
    today = date.today().isoformat()

    # 1) Export du jour
    export_csv(f"annonces_{today}.csv", "WHERE first_seen LIKE ?", (today + "%",))

    # 2) Export complet (historique)
    export_csv("annonces_toutes.csv")

    # 3) Export détaillé (identique ici, mais tu peux le garder comme “vue détail”)
    export_csv("annonces_detail.csv")
