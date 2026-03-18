import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)


def clean_workforce_df(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
    """Clean and validate workforce CSV data. Returns (clean_df, error_rows)."""
    errors = []
    original_len = len(df)

    # Normalize column names
    df.columns = df.columns.str.strip().str.lower().str.replace(r"\s+", "_", regex=True)

    # Required columns
    required = ["employee_id", "date", "scheduled_hours", "actual_hours"]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Deduplicate
    dupes = df.duplicated(subset=["employee_id", "date"], keep="first")
    if dupes.sum() > 0:
        logger.warning(f"Dropping {dupes.sum()} duplicate rows")
        df = df[~dupes].copy()

    # Parse dates
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bad_dates = df["date"].isna()
    if bad_dates.any():
        for idx, row in df[bad_dates].iterrows():
            errors.append({"row": int(idx), "error": "invalid_date", "data": row.to_dict()})
        df = df[~bad_dates].copy()

    # Numeric coercion
    numeric_cols = ["scheduled_hours", "actual_hours", "overtime_hours",
                    "tasks_completed", "tasks_assigned", "demand_units", "capacity_units"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Range validation
    mask_hours = (df["scheduled_hours"] < 0) | (df["scheduled_hours"] > 24)
    if mask_hours.any():
        for idx, row in df[mask_hours].iterrows():
            errors.append({"row": int(idx), "error": "hours_out_of_range", "data": row.to_dict()})
        df = df[~mask_hours].copy()

    mask_actual = df["actual_hours"] < 0
    df.loc[mask_actual, "actual_hours"] = 0.0

    # Compute derived fields
    df["utilization_rate"] = np.where(
        df["scheduled_hours"] > 0,
        (df["actual_hours"] / df["scheduled_hours"]).clip(0, 2),
        0.0,
    )
    if "overtime_hours" not in df.columns:
        df["overtime_hours"] = (df["actual_hours"] - df["scheduled_hours"]).clip(lower=0)

    if "absent" not in df.columns:
        df["absent"] = df["actual_hours"] == 0

    # Fill remaining nulls
    df["absence_reason"] = df.get("absence_reason", pd.Series([""] * len(df))).fillna("")
    df["department_code"] = df.get("department_code", pd.Series(["UNKNOWN"] * len(df))).fillna("UNKNOWN")

    logger.info(f"Workforce cleaning: {original_len} rows in -> {len(df)} clean, {len(errors)} errors")
    return df, errors


def clean_tickets_df(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
    """Clean and validate support ticket CSV data."""
    errors = []
    original_len = len(df)

    df.columns = df.columns.str.strip().str.lower().str.replace(r"\s+", "_", regex=True)

    required = ["ticket_id", "created_at", "category", "priority", "status"]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Deduplicate on ticket_id
    dupes = df.duplicated(subset=["ticket_id"], keep="first")
    df = df[~dupes].copy()

    # Parse timestamps
    for ts_col in ["created_at", "resolved_at"]:
        if ts_col in df.columns:
            df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")

    bad_created = df["created_at"].isna()
    for idx, row in df[bad_created].iterrows():
        errors.append({"row": int(idx), "error": "invalid_created_at", "data": row.to_dict()})
    df = df[~bad_created].copy()

    # Standardize enums
    valid_priorities = {"low", "medium", "high", "critical"}
    valid_statuses = {"open", "in_progress", "resolved", "closed"}

    df["priority"] = df["priority"].str.lower().str.strip()
    df["status"] = df["status"].str.lower().str.strip()

    bad_priority = ~df["priority"].isin(valid_priorities)
    df.loc[bad_priority, "priority"] = "medium"

    bad_status = ~df["status"].isin(valid_statuses)
    df.loc[bad_status, "status"] = "open"

    # SLA targets (hours) by priority
    sla_map = {"critical": 4, "high": 8, "medium": 24, "low": 72}
    df["sla_target_hours"] = df["priority"].map(sla_map)

    # Resolution hours
    df["actual_resolution_hours"] = None
    resolved_mask = df["resolved_at"].notna()
    if resolved_mask.any():
        df.loc[resolved_mask, "actual_resolution_hours"] = (
            (df.loc[resolved_mask, "resolved_at"] - df.loc[resolved_mask, "created_at"])
            .dt.total_seconds() / 3600
        )

    # SLA breach flag
    df["sla_breached"] = False
    breach_mask = resolved_mask & (
        df["actual_resolution_hours"] > df["sla_target_hours"]
    )
    df.loc[breach_mask, "sla_breached"] = True

    # Open tickets that are overdue
    now = datetime.utcnow()
    open_mask = df["status"].isin(["open", "in_progress"])
    if open_mask.any():
        open_hours = (now - df.loc[open_mask, "created_at"]).dt.total_seconds() / 3600
        df.loc[open_mask & (open_hours > df.loc[open_mask, "sla_target_hours"]), "sla_breached"] = True

    # Sentiment score default
    if "sentiment_score" not in df.columns:
        df["sentiment_score"] = 0.0
    df["sentiment_score"] = pd.to_numeric(df["sentiment_score"], errors="coerce").fillna(0.0)

    # Escalated flag
    if "escalated" not in df.columns:
        df["escalated"] = False

    df["channel"] = df.get("channel", pd.Series(["portal"] * len(df))).fillna("portal")
    df["department_code"] = df.get("department_code", pd.Series(["UNKNOWN"] * len(df))).fillna("UNKNOWN")

    logger.info(f"Ticket cleaning: {original_len} in -> {len(df)} clean, {len(errors)} errors")
    return df, errors


def clean_market_signals_df(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
    """Clean and validate market signals JSON-derived DataFrame."""
    errors = []

    df.columns = df.columns.str.strip().str.lower().str.replace(r"\s+", "_", regex=True)

    df["signal_date"] = pd.to_datetime(df.get("signal_date", df.get("date")), errors="coerce")
    bad = df["signal_date"].isna()
    for idx, row in df[bad].iterrows():
        errors.append({"row": int(idx), "error": "invalid_signal_date", "data": row.to_dict()})
    df = df[~bad].copy()

    df["value"] = pd.to_numeric(df.get("value", 0), errors="coerce").fillna(0.0)
    df["change_pct"] = pd.to_numeric(df.get("change_pct", 0), errors="coerce").fillna(0.0)

    df["source"] = df.get("source", pd.Series(["unknown"] * len(df))).fillna("unknown")
    df["category"] = df.get("category", pd.Series(["general"] * len(df))).fillna("general")

    return df, errors
