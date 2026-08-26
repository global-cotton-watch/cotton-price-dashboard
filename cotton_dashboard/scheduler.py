from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .service import update_all
from .storage import PriceStore


def seconds_until(hour: int, minute: int, timezone_name: str) -> float:
    tz = ZoneInfo(timezone_name)
    now = datetime.now(tz)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def main() -> None:
    database = os.environ.get("COTTON_DATABASE", "/data/cotton.db")
    timezone_name = os.environ.get("UPDATE_TIMEZONE", "Asia/Shanghai")
    hour = int(os.environ.get("UPDATE_HOUR", "9"))
    minute = int(os.environ.get("UPDATE_MINUTE", "15"))
    store = PriceStore(database)
    while True:
        result = update_all(store)
        print(result, flush=True)
        time.sleep(seconds_until(hour, minute, timezone_name))


if __name__ == "__main__":
    main()
