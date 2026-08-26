from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    market TEXT NOT NULL,
    price_date TEXT NOT NULL,
    native_price REAL NOT NULL,
    native_unit TEXT NOT NULL,
    cny_per_ton REAL NOT NULL,
    fx_rate REAL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (market, price_date)
);
CREATE TABLE IF NOT EXISTS update_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '{}'
);
"""


class PriceStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def upsert(self, points: Iterable[dict]) -> int:
        rows = list(points)
        if not rows:
            return 0
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO prices (
                    market, price_date, native_price, native_unit, cny_per_ton,
                    fx_rate, source_name, source_url, fetched_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(market, price_date) DO UPDATE SET
                    native_price=excluded.native_price,
                    native_unit=excluded.native_unit,
                    cny_per_ton=excluded.cny_per_ton,
                    fx_rate=excluded.fx_rate,
                    source_name=excluded.source_name,
                    source_url=excluded.source_url,
                    fetched_at=excluded.fetched_at,
                    metadata=excluded.metadata
                """,
                [
                    (
                        row["market"], row["date"], row["native_price"],
                        row["native_unit"], row["cny_per_ton"], row.get("fx_rate"),
                        row["source_name"], row["source_url"], row["fetched_at"],
                        json.dumps(row.get("metadata", {}), ensure_ascii=False),
                    )
                    for row in rows
                ],
            )
        return len(rows)

    def latest_by_market(self, limit: int = 7) -> dict[str, list[dict]]:
        output: dict[str, list[dict]] = {}
        with self.connect() as conn:
            markets = [row[0] for row in conn.execute("SELECT DISTINCT market FROM prices")]
            for market in markets:
                rows = conn.execute(
                    "SELECT * FROM prices WHERE market=? ORDER BY price_date DESC LIMIT ?",
                    (market, limit),
                ).fetchall()
                parsed = []
                for row in reversed(rows):
                    item = dict(row)
                    item["date"] = item.pop("price_date")
                    item["metadata"] = json.loads(item["metadata"])
                    parsed.append(item)
                output[market] = parsed
        return output

    def latest_fetch_time(self) -> str | None:
        with self.connect() as conn:
            row = conn.execute("SELECT MAX(fetched_at) FROM prices").fetchone()
            return row[0] if row and row[0] else None

    def start_run(self, started_at: str) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                "INSERT INTO update_runs(started_at,status) VALUES (?, 'running')",
                (started_at,),
            )
            return int(cursor.lastrowid)

    def finish_run(self, run_id: int, finished_at: str, status: str, details: dict) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE update_runs SET finished_at=?, status=?, details=? WHERE id=?",
                (finished_at, status, json.dumps(details, ensure_ascii=False), run_id),
            )
