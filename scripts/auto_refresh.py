"""Automated data refresh pipeline (RPA).

Scheduled execution for public data collection and processing.
Designed for cron or systemd timer deployment.

Usage:
    # Manual run
    python scripts/auto_refresh.py

    # Cron (daily at 06:00)
    0 6 * * * cd /path/to/lifestyle-safety-planner && .venv/bin/python scripts/auto_refresh.py >> logs/refresh.log 2>&1

    # Cron (weekly on Monday at 06:00)
    0 6 * * 1 cd /path/to/lifestyle-safety-planner && .venv/bin/python scripts/auto_refresh.py --full >> logs/refresh.log 2>&1
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import RAW_DIR, SAMPLE_DIR

# Setup logging
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(SAMPLE_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "refresh.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("auto_refresh")


def refresh_air_quality():
    """Refresh air quality data (API-based, hourly available)."""
    logger.info("Refreshing air quality data...")
    try:
        from collectors.air_quality import collect_and_save
        df = collect_and_save()
        if df is not None:
            logger.info("Air quality: %d rows collected.", len(df))
            return True
    except Exception as e:
        logger.error("Air quality refresh failed: %s", e)
    return False


def refresh_traffic():
    """Refresh traffic accident data (API-based, annual)."""
    logger.info("Refreshing traffic accident data...")
    try:
        from collectors.traffic import collect_and_save
        df = collect_and_save(years=[2023, 2024])
        if df is not None:
            logger.info("Traffic: %d rows collected.", len(df))
            return True
    except Exception as e:
        logger.error("Traffic refresh failed: %s", e)
    return False


def refresh_csv_collectors():
    """Check and re-parse CSV-based collectors if raw files exist."""
    csv_collectors = [
        ("crime", "crime_raw.csv"),
        ("flood", "flood_raw.csv"),
        ("medical", "medical_raw.csv"),
        ("fire", "fire_raw.csv"),
    ]

    results = {}
    for name, raw_file in csv_collectors:
        raw_path = RAW_DIR / raw_file
        if raw_path.exists():
            logger.info("Re-parsing %s from %s...", name, raw_path)
            try:
                module = __import__(f"collectors.{name}", fromlist=["collect_and_save"])
                df = module.collect_and_save(filepath=raw_path)
                if df is not None:
                    logger.info("%s: %d rows parsed.", name, len(df))
                    results[name] = True
                else:
                    results[name] = False
            except Exception as e:
                logger.error("%s refresh failed: %s", name, e)
                results[name] = False
        else:
            logger.info("%s: raw CSV not found, skipping.", name)
            results[name] = None

    return results


def write_status(results):
    """Write refresh status to a JSON file for dashboard monitoring."""
    import json
    status = {
        "last_refresh": datetime.now().isoformat(),
        "results": {k: str(v) for k, v in results.items()},
    }
    status_path = RAW_DIR / "refresh_status.json"
    with open(status_path, "w") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
    logger.info("Status written to %s", status_path)


def main():
    parser = argparse.ArgumentParser(description="Automated data refresh")
    parser.add_argument(
        "--full", action="store_true",
        help="Run full refresh including annual data (traffic)",
    )
    parser.add_argument(
        "--air-only", action="store_true",
        help="Refresh air quality only (for frequent scheduling)",
    )
    args = parser.parse_args()

    logger.info("=== Auto refresh started (%s) ===",
                "full" if args.full else "air-only" if args.air_only else "standard")

    results = {}

    # Air quality: always refresh (real-time API)
    results["air_quality"] = refresh_air_quality()

    if not args.air_only:
        # CSV-based: re-parse if raw files exist
        csv_results = refresh_csv_collectors()
        results.update(csv_results)

    if args.full:
        # Traffic: annual data, refresh weekly
        results["traffic"] = refresh_traffic()

    write_status(results)

    success = sum(1 for v in results.values() if v is True)
    total = sum(1 for v in results.values() if v is not None)
    logger.info("=== Refresh complete: %d/%d succeeded ===", success, total)


if __name__ == "__main__":
    main()
