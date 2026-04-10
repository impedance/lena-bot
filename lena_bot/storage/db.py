import sqlite3
from datetime import date, datetime

from lena_bot.config import DB_PATH


def ensure_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            raw_url TEXT,
            title TEXT,
            snippet TEXT,
            source_domain TEXT,
            query_group TEXT,
            site_group TEXT,
            query_level TEXT,
            query_text TEXT,
            url_status TEXT,
            resolved_url TEXT,
            resolved_note TEXT,
            criteria_status TEXT,
            criteria_note TEXT,
            first_seen TEXT
        )
    """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cse_usage (
            day TEXT PRIMARY KEY,
            calls INTEGER NOT NULL
        )
    """
    )
    conn.commit()
    return conn


def get_cse_calls(conn) -> int:
    today = date.today().isoformat()
    cur = conn.cursor()
    cur.execute("SELECT calls FROM cse_usage WHERE day = ?", (today,))
    row = cur.fetchone()
    return int(row[0]) if row else 0


def inc_cse_calls(conn, inc: int = 1) -> int:
    today = date.today().isoformat()
    cur = conn.cursor()
    cur.execute("SELECT calls FROM cse_usage WHERE day = ?", (today,))
    row = cur.fetchone()
    current = int(row[0]) if row else 0
    newv = current + inc
    cur.execute(
        "INSERT INTO cse_usage(day, calls) VALUES(?, ?) "
        "ON CONFLICT(day) DO UPDATE SET calls=?",
        (today, newv, newv),
    )
    conn.commit()
    return newv


def insert_listing(conn, row: dict) -> int:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR IGNORE INTO listings
        (url, raw_url, title, snippet, source_domain, query_group, site_group, query_level, query_text,
         url_status, resolved_url, resolved_note, criteria_status, criteria_note, first_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            row["url"],
            row.get("raw_url", ""),
            row.get("title", ""),
            row.get("snippet", ""),
            row.get("source_domain", ""),
            row.get("query_group", ""),
            row.get("site_group", ""),
            row.get("query_level", ""),
            row.get("query_text", ""),
            row.get("url_status", "DIRECT"),
            row.get("resolved_url", ""),
            row.get("resolved_note", ""),
            row.get("criteria_status", "OK"),
            row.get("criteria_note", ""),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    return cur.rowcount
