import csv
from datetime import datetime


def write_run_csv(rows, filename=None):
    if not rows:
        return None
    now = datetime.now()
    if filename is None:
        filename = f"{now.strftime('%Y-%m-%d_%H-%M-%S')}_run_results.csv"

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(
            [
                "date_detection",
                "heure_detection",
                "site_group",
                "query_group",
                "query_level",
                "source_domain",
                "criteria_status",
                "criteria_note",
                "url_status",
                "resolved_note",
                "title",
                "url",
                "resolved_url",
                "raw_url",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r["date_detection"],
                    r["heure_detection"],
                    r["site_group"],
                    r["query_group"],
                    r["query_level"],
                    r["source_domain"],
                    r["criteria_status"],
                    r.get("criteria_note", ""),
                    r["url_status"],
                    r.get("resolved_note", ""),
                    r["title"],
                    r["url"],
                    r.get("resolved_url", ""),
                    r.get("raw_url", ""),
                ]
            )
    return filename
