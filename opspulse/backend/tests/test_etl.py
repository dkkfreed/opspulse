import pytest
import pandas as pd
from datetime import date, datetime
from app.etl.cleaning import clean_workforce_df, clean_tickets_df


def make_workforce_df():
    return pd.DataFrame({
        "employee_id": ["EMP001", "EMP002", "EMP001", "EMP003"],
        "date": ["2024-01-15", "2024-01-15", "2024-01-15", "bad-date"],
        "scheduled_hours": ["8.0", "8.0", "8.0", "8.0"],
        "actual_hours": ["7.5", "9.0", "7.5", "8.0"],
        "overtime_hours": ["0", "1.0", "0", "0"],
        "department_code": ["ENG", "OPS", "ENG", "HR"],
    })


def make_tickets_df():
    return pd.DataFrame({
        "ticket_id": ["TKT-001", "TKT-002", "TKT-001", "TKT-003"],
        "created_at": [
            "2024-01-15 09:00:00", "2024-01-15 10:00:00",
            "2024-01-15 09:00:00", "2024-01-15 11:00:00"
        ],
        "resolved_at": ["2024-01-15 17:00:00", None, "2024-01-15 17:00:00", None],
        "category": ["technical", "billing", "technical", "onboarding"],
        "priority": ["HIGH", "medium", "HIGH", "invalid_priority"],
        "status": ["resolved", "open", "resolved", "in_progress"],
    })


class TestWorkforceCleaning:
    def test_deduplication(self):
        df, errors = clean_workforce_df(make_workforce_df())
        # EMP001 on same date appears twice - should dedup
        dup_check = df[df["employee_id"] == "EMP001"]
        assert len(dup_check) == 1

    def test_invalid_date_quarantined(self):
        df, errors = clean_workforce_df(make_workforce_df())
        bad_date_errors = [e for e in errors if e["error"] == "invalid_date"]
        assert len(bad_date_errors) == 1

    def test_utilization_computed(self):
        df, _ = clean_workforce_df(make_workforce_df())
        assert "utilization_rate" in df.columns
        assert df["utilization_rate"].between(0, 2).all()

    def test_required_columns_missing_raises(self):
        bad_df = pd.DataFrame({"employee_id": ["EMP001"]})
        with pytest.raises(ValueError, match="Missing required columns"):
            clean_workforce_df(bad_df)

    def test_numeric_coercion(self):
        df = make_workforce_df().copy()
        df.loc[0, "scheduled_hours"] = "abc"
        clean_df, _ = clean_workforce_df(df)
        # Row with invalid hours should be coerced to 0
        assert clean_df["scheduled_hours"].dtype in [float, "float64"]


class TestTicketsCleaning:
    def test_deduplication_by_ticket_id(self):
        df, errors = clean_tickets_df(make_tickets_df())
        assert len(df[df["ticket_id"] == "TKT-001"]) == 1

    def test_priority_standardized_lowercase(self):
        df, _ = clean_tickets_df(make_tickets_df())
        assert (df["priority"] == df["priority"].str.lower()).all()

    def test_invalid_priority_defaults_to_medium(self):
        df, _ = clean_tickets_df(make_tickets_df())
        tkt3 = df[df["ticket_id"] == "TKT-003"]
        assert tkt3.iloc[0]["priority"] == "medium"

    def test_sla_target_assigned(self):
        df, _ = clean_tickets_df(make_tickets_df())
        assert "sla_target_hours" in df.columns
        assert (df["sla_target_hours"] > 0).all()

    def test_resolution_hours_calculated(self):
        df, _ = clean_tickets_df(make_tickets_df())
        resolved = df[df["ticket_id"] == "TKT-001"]
        assert resolved.iloc[0]["actual_resolution_hours"] == pytest.approx(8.0, abs=0.1)
