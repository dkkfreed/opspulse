import pandas as pd
import json
import logging
from pathlib import Path
from typing import Union, List, Dict, Any
from app.etl.cleaning import (
    clean_workforce_df, clean_tickets_df, clean_market_signals_df
)

logger = logging.getLogger(__name__)


def ingest_csv(filepath: Union[str, Path], source_type: str) -> Dict[str, Any]:
    """Ingest a CSV file and dispatch to the appropriate cleaner."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    df = pd.read_csv(path, dtype=str)
    logger.info(f"Loaded {len(df)} rows from {path.name}")

    cleaner_map = {
        "workforce": clean_workforce_df,
        "tickets": clean_tickets_df,
        "market": clean_market_signals_df,
    }

    if source_type not in cleaner_map:
        raise ValueError(f"Unknown source_type: {source_type}. Expected: {list(cleaner_map)}")

    clean_df, errors = cleaner_map[source_type](df)
    return {
        "source_file": path.name,
        "source_type": source_type,
        "raw_rows": len(df),
        "clean_rows": len(clean_df),
        "error_count": len(errors),
        "errors": errors,
        "data": clean_df,
    }


def ingest_json(filepath: Union[str, Path]) -> Dict[str, Any]:
    """Ingest a JSON file of market signals."""
    path = Path(filepath)
    with open(path) as f:
        raw = json.load(f)

    records = raw if isinstance(raw, list) else raw.get("signals", raw.get("data", [raw]))
    df = pd.DataFrame(records)
    logger.info(f"Loaded {len(df)} records from {path.name}")

    clean_df, errors = clean_market_signals_df(df)
    return {
        "source_file": path.name,
        "source_type": "market",
        "raw_rows": len(df),
        "clean_rows": len(clean_df),
        "error_count": len(errors),
        "errors": errors,
        "data": clean_df,
    }


def validate_schema(df: pd.DataFrame, required_cols: List[str]) -> List[str]:
    """Return list of missing columns."""
    return [c for c in required_cols if c not in df.columns]
