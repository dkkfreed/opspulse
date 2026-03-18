"""
ETL Validation Layer
Validates incoming dataframes against expected schemas.
Bad rows are quarantined — never silently dropped.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ValidationResult:
    valid_df: pd.DataFrame
    quarantined: list[dict]  # list of {row_number, raw_data, error_codes, error_details}
    total_rows: int
    valid_rows: int
    quarantined_rows: int
    warnings: list[str] = field(default_factory=list)

    @property
    def quarantine_rate(self) -> float:
        if self.total_rows == 0:
            return 0.0
        return self.quarantined_rows / self.total_rows


# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------

EMPLOYEE_SCHEMA = {
    "required_columns": ["employee_code", "full_name", "email", "role", "department_code", "hire_date"],
    "nullable": ["seniority_level", "hourly_rate", "manager_employee_code", "location_code"],
    "email_columns": ["email"],
    "date_columns": ["hire_date"],
    "positive_numeric": ["hourly_rate"],
}

OPERATIONS_SCHEMA = {
    "required_columns": ["employee_code", "date", "scheduled_hours", "actual_hours"],
    "nullable": ["overtime_hours", "absence_reason", "tasks_completed"],
    "date_columns": ["date"],
    "positive_numeric": ["scheduled_hours", "actual_hours", "overtime_hours"],
    "range_checks": {"scheduled_hours": (0, 24), "actual_hours": (0, 24)},
}

TICKET_SCHEMA = {
    "required_columns": ["ticket_number", "created_at", "category", "priority", "status"],
    "nullable": ["resolved_at", "department_code", "assignee_code", "description_summary", "sla_target_minutes"],
    "date_columns": ["created_at", "resolved_at"],
    "enum_checks": {
        "priority": ["low", "medium", "high", "critical"],
        "status": ["open", "in_progress", "resolved", "closed", "escalated"],
    },
}

MARKET_SIGNAL_SCHEMA = {
    "required_columns": ["signal_date", "category", "source", "title"],
    "nullable": ["summary", "sentiment_score", "relevance_score", "url", "tags"],
    "date_columns": ["signal_date"],
    "range_checks": {"sentiment_score": (-1.0, 1.0), "relevance_score": (0.0, 1.0)},
    "enum_checks": {
        "category": ["competitor", "market", "regulatory", "hiring", "technology", "sentiment"],
    },
}

SCHEMAS = {
    "employee": EMPLOYEE_SCHEMA,
    "operations": OPERATIONS_SCHEMA,
    "ticket": TICKET_SCHEMA,
    "market_signal": MARKET_SIGNAL_SCHEMA,
}


# ---------------------------------------------------------------------------
# Core validation engine
# ---------------------------------------------------------------------------

class DataValidator:
    def validate(self, df: pd.DataFrame, schema_name: str) -> ValidationResult:
        schema = SCHEMAS[schema_name]
        df = df.copy()
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        valid_rows = []
        quarantined = []

        for idx, row in df.iterrows():
            errors = self._validate_row(row, schema, int(idx))
            if errors:
                quarantined.append({
                    "row_number": int(idx) + 1,
                    "raw_data": row.to_dict(),
                    "error_codes": [e["code"] for e in errors],
                    "error_details": "; ".join(e["detail"] for e in errors),
                })
            else:
                valid_rows.append(row)

        valid_df = pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)

        return ValidationResult(
            valid_df=valid_df,
            quarantined=quarantined,
            total_rows=len(df),
            valid_rows=len(valid_rows),
            quarantined_rows=len(quarantined),
        )

    def _validate_row(self, row: pd.Series, schema: dict, idx: int) -> list[dict]:
        errors = []

        # Required field presence and non-null
        for col in schema.get("required_columns", []):
            if col not in row.index or pd.isna(row.get(col)) or str(row.get(col, "")).strip() == "":
                errors.append({"code": f"MISSING_{col.upper()}", "detail": f"Required field '{col}' is missing or empty"})

        if errors:
            return errors  # Don't attempt further checks on structurally broken rows

        # Email format
        email_re = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
        for col in schema.get("email_columns", []):
            val = str(row.get(col, ""))
            if val and not email_re.match(val):
                errors.append({"code": f"INVALID_EMAIL_{col.upper()}", "detail": f"'{col}' is not a valid email: {val}"})

        # Date parsing
        for col in schema.get("date_columns", []):
            val = row.get(col)
            if pd.notna(val) and val != "":
                try:
                    pd.to_datetime(str(val))
                except (ValueError, TypeError):
                    errors.append({"code": f"INVALID_DATE_{col.upper()}", "detail": f"'{col}' could not be parsed as a date: {val}"})

        # Positive numeric
        for col in schema.get("positive_numeric", []):
            val = row.get(col)
            if pd.notna(val) and val != "":
                try:
                    num = float(val)
                    if num < 0:
                        errors.append({"code": f"NEGATIVE_{col.upper()}", "detail": f"'{col}' must be >= 0, got {num}"})
                except (ValueError, TypeError):
                    errors.append({"code": f"NOT_NUMERIC_{col.upper()}", "detail": f"'{col}' must be numeric, got {val}"})

        # Range checks
        for col, (lo, hi) in schema.get("range_checks", {}).items():
            val = row.get(col)
            if pd.notna(val) and val != "":
                try:
                    num = float(val)
                    if not (lo <= num <= hi):
                        errors.append({"code": f"OUT_OF_RANGE_{col.upper()}", "detail": f"'{col}' must be between {lo} and {hi}, got {num}"})
                except (ValueError, TypeError):
                    pass  # Already caught by numeric check if listed there

        # Enum checks
        for col, allowed in schema.get("enum_checks", {}).items():
            val = str(row.get(col, "")).strip().lower()
            if val and val not in allowed:
                errors.append({"code": f"INVALID_ENUM_{col.upper()}", "detail": f"'{col}' must be one of {allowed}, got '{val}'"})

        return errors
