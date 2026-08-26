from __future__ import annotations

from datetime import datetime, timezone

import requests

from .scrapers import SCRAPERS, fetch_fx_rates
from .storage import PriceStore


def update_all(store: PriceStore) -> dict:
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run_id = store.start_run(started)
    details: dict = {"markets": {}, "fx": None}
    status = "success"
    try:
        session = requests.Session()
        fx = fetch_fx_rates(session)
        details["fx"] = fx
        for market, scraper in SCRAPERS.items():
            try:
                points = scraper(session, fx)
                count = store.upsert(points)
                details["markets"][market] = {"status": "success", "rows": count}
            except Exception as exc:  # one source must not prevent the other markets
                status = "partial"
                details["markets"][market] = {"status": "error", "error": str(exc)}
    except Exception as exc:
        status = "error"
        details["error"] = str(exc)
    finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
    store.finish_run(run_id, finished, status, details)
    return {"status": status, "started_at": started, "finished_at": finished, **details}
