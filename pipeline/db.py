"""Database connection with CSV fallback.

CSV fallback is first-class for Streamlit Cloud (zero cost).
PostgreSQL used locally for development.
"""

import os
import logging
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Conditional import for Streamlit Cloud compatibility
try:
    import psycopg2
    import psycopg2.extras
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

from config import DB_CONFIG, USE_CSV_FALLBACK, SAMPLE_DIR


@contextmanager
def get_conn():
    """Context manager for PostgreSQL connection."""
    if USE_CSV_FALLBACK or not HAS_PSYCOPG2:
        raise RuntimeError("CSV fallback mode active; use load_csv() instead.")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query_df(sql, params=None):
    """Execute SQL and return DataFrame. Falls back to CSV if configured."""
    if USE_CSV_FALLBACK:
        logger.info("CSV fallback active; SQL queries not available.")
        return pd.DataFrame()
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params=params)


def load_csv(name, subdir="sample"):
    """Load CSV from data directory.

    Args:
        name: filename without extension
        subdir: subdirectory under data/ (default: sample)
    """
    from config import DATA_DIR
    path = DATA_DIR / subdir / f"{name}.csv"
    if not path.exists():
        logger.warning("CSV not found: %s", path)
        return pd.DataFrame()
    df = pd.read_csv(path)
    # Auto-parse date columns
    for col in df.columns:
        if "date" in col.lower():
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def load_safety_data(category):
    """Load safety data by category. Tries DB first, falls back to CSV."""
    if not USE_CSV_FALLBACK and HAS_PSYCOPG2:
        sql = """
            SELECT * FROM staging.location_safety
            WHERE category = %s
            ORDER BY sido, sigungu, dong
        """
        return query_df(sql, params=(category,))
    return load_csv(f"safety_{category}")
