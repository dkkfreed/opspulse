"""
ETL Cleaning Service
Handles: deduplication, missing value imputation, date normalization,
field mapping from raw source columns to warehouse schema.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime


class DataCleaner:
    """
    Applies opinionated cleaning rules to raw dataframes.
    All transformations are documented and reversible (original stored in quarantine).
    """

    def clean_employees(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = self._normalize_columns(df)
        df = self._strip_strings(df, ["employee_code", "full_name", "email", "role", "department_code"])
        df["email"] = df["email"].str.lower()
        df["employee_code"] = df["employee_code"].str.upper()
        df["hire_date"] = pd.to_datetime(df["hire_date"], errors="coerce").dt.date
        df["status"] = df.get("status", pd.Series(["active"] * len(df))).fillna("active").str.lower()
        df["seniority_level"] = df.get("seniority_level", pd.Series([None] * len(df))).str.lower()
        df["hourly_rate"] = pd.to_numeric(df.get("hourly_rate", pd.Series([None] * len(df))), errors="coerce")
        df = df.drop_duplicates(subset=["employee_code"], keep="last")
        return df

    def clean_operations(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = self._normalize_columns(df)
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        df["employee_code"] = df["employee_code"].str.upper().str.strip()
        for col in ["scheduled_hours", "actual_hours", "overtime_hours"]:
            df[col] = pd.to_numeric(df.get(col, pd.Series([0] * len(df))), errors="coerce").fillna(0).clip(lower=0)
        df["tasks_completed"] = pd.to_numeric(df.get("tasks_completed", pd.Series([0] * len(df))), errors="coerce").fillna(0).astype(int)
        df["is_absent"] = df.get("is_absent", pd.Series([False] * len(df))).fillna(False).astype(bool)
        # Derived: if actual_hours == 0 and not marked absent, mark absent
        df.loc[(df["actual_hours"] == 0) & (~df["is_absent"]), "is_absent"] = True
        # Compute utilization
        df["utilization_pct"] = np.where(
            df["scheduled_hours"] > 0,
            (df["actual_hours"] / df["scheduled_hours"] * 100).round(1),
            None
        )
        df = df.drop_duplicates(subset=["employee_code", "date"], keep="last")
        return df

    def clean_tickets(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = self._normalize_columns(df)
        df["ticket_number"] = df["ticket_number"].str.upper().str.strip()
        df["category"] = df["category"].str.lower().str.strip()
        df["priority"] = df["priority"].str.lower().str.strip()
        df["status"] = df["status"].str.lower().str.strip()
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df["resolved_at"] = pd.to_datetime(df.get("resolved_at", pd.Series([None] * len(df))), errors="coerce")

        # Compute resolution time in minutes
        df["resolution_minutes"] = (
            (df["resolved_at"] - df["created_at"]).dt.total_seconds() / 60
        ).where(df["resolved_at"].notna()).round(0).astype("Int64")

        # SLA breach flag
        sla_map = {"critical": 240, "high": 480, "medium": 1440, "low": 4320}
        df["sla_target_minutes"] = df["priority"].map(sla_map)
        df["sla_breached"] = (
            df["resolution_minutes"].notna() &
            (df["resolution_minutes"] > df["sla_target_minutes"])
        )
        df = df.drop_duplicates(subset=["ticket_number"], keep="last")
        return df

    def clean_market_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = self._normalize_columns(df)
        df["signal_date"] = pd.to_datetime(df["signal_date"], errors="coerce").dt.date
        df["category"] = df["category"].str.lower().str.strip()
        df["source"] = df["source"].str.strip()
        df["sentiment_score"] = pd.to_numeric(df.get("sentiment_score", pd.Series([None] * len(df))), errors="coerce").clip(-1, 1)
        df["relevance_score"] = pd.to_numeric(df.get("relevance_score", pd.Series([None] * len(df))), errors="coerce").clip(0, 1)
        df["tags"] = df.get("tags", pd.Series([None] * len(df))).apply(self._parse_tags)
        return df

    # ------------------------------------------------------------------
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]
        return df

    def _strip_strings(self, df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
        for col in cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        return df

    def _parse_tags(self, val) -> list[str] | None:
        if pd.isna(val) or val == "":
            return None
        if isinstance(val, list):
            return val
        return [t.strip() for t in str(val).split(",") if t.strip()]
