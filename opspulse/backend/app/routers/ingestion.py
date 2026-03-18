"""
Ingestion API
Accepts CSV uploads, validates them, runs cleaning, loads into warehouse.
Failed rows go to quarantine — never silently dropped.
"""
from __future__ import annotations

import io
import uuid
from datetime import datetime
from typing import Literal

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.facts import IngestionRun, QuarantinedRow
from app.services.cleaning import DataCleaner
from app.services.validation import DataValidator

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])
settings = get_settings()
validator = DataValidator()
cleaner = DataCleaner()

DatasetType = Literal["employee", "operations", "ticket", "market_signal"]


@router.post("/upload/{dataset_type}")
async def upload_csv(
    dataset_type: DatasetType,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_MB}MB limit.")

    run_id = str(uuid.uuid4())[:8].upper()
    run = IngestionRun(
        run_id=run_id,
        source_type="csv",
        source_name=file.filename,
        target_table=f"fact_{dataset_type}" if dataset_type != "employee" else "dim_employee",
        status="running",
    )
    db.add(run)
    await db.flush()

    try:
        df = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
        run.rows_read = len(df)

        # Validate
        val_result = validator.validate(df, dataset_type)

        if val_result.quarantine_rate > settings.QUARANTINE_THRESHOLD and val_result.valid_rows == 0:
            run.status = "failed"
            run.error_message = f"100% quarantine rate — aborting. Check schema."
            run.completed_at = datetime.utcnow()
            await db.flush()
            raise HTTPException(status_code=422, detail=run.error_message)

        # Store quarantined rows
        for q in val_result.quarantined:
            db.add(QuarantinedRow(
                run_id=run_id,
                source_table=dataset_type,
                row_number=q["row_number"],
                raw_data=q["raw_data"],
                error_codes=q["error_codes"],
                error_details=q["error_details"],
            ))

        # Clean valid rows
        clean_method = getattr(cleaner, f"clean_{dataset_type}s" if dataset_type != "market_signal" else "clean_market_signals")
        clean_df = clean_method(val_result.valid_df)

        # Load into DB
        inserted = await _load_dataset(dataset_type, clean_df, db)

        run.rows_inserted = inserted
        run.rows_quarantined = val_result.quarantined_rows
        run.status = "success" if val_result.quarantine_rate < settings.QUARANTINE_THRESHOLD else "partial"
        run.completed_at = datetime.utcnow()
        await db.flush()

        return {
            "run_id": run_id,
            "status": run.status,
            "rows_read": run.rows_read,
            "rows_inserted": run.rows_inserted,
            "rows_quarantined": run.rows_quarantined,
            "quarantine_rate": round(val_result.quarantine_rate, 4),
            "warnings": val_result.warnings,
        }

    except HTTPException:
        raise
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        run.completed_at = datetime.utcnow()
        await db.flush()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")


async def _load_dataset(dataset_type: str, df: pd.DataFrame, db: AsyncSession) -> int:
    """Upsert cleaned rows into the appropriate table using raw SQL for performance."""
    if df.empty:
        return 0

    inserted = 0
    records = df.where(pd.notna(df), None).to_dict("records")

    if dataset_type == "employee":
        for r in records:
            await db.execute(text("""
                INSERT INTO dim_employee (employee_code, full_name, email, role, department_id, hire_date, status, hourly_rate)
                SELECT :code, :name, :email, :role,
                       (SELECT id FROM dim_department WHERE department_code = :dept_code LIMIT 1),
                       :hire_date, :status, :hourly_rate
                ON CONFLICT (employee_code) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    email = EXCLUDED.email,
                    role = EXCLUDED.role,
                    updated_at = NOW()
            """), {
                "code": r.get("employee_code"),
                "name": r.get("full_name"),
                "email": r.get("email"),
                "role": r.get("role"),
                "dept_code": r.get("department_code"),
                "hire_date": r.get("hire_date"),
                "status": r.get("status", "active"),
                "hourly_rate": r.get("hourly_rate"),
            })
            inserted += 1

    elif dataset_type == "operations":
        for r in records:
            await db.execute(text("""
                INSERT INTO fact_operations (date_id, employee_id, department_id, scheduled_hours, actual_hours, overtime_hours, is_absent, tasks_completed, utilization_pct)
                SELECT
                    (SELECT id FROM dim_date WHERE date = :d LIMIT 1),
                    (SELECT id FROM dim_employee WHERE employee_code = :emp_code LIMIT 1),
                    (SELECT department_id FROM dim_employee WHERE employee_code = :emp_code LIMIT 1),
                    :scheduled, :actual, :overtime, :absent, :tasks, :util
                ON CONFLICT DO NOTHING
            """), {
                "d": r.get("date"),
                "emp_code": r.get("employee_code"),
                "scheduled": r.get("scheduled_hours", 8),
                "actual": r.get("actual_hours", 0),
                "overtime": r.get("overtime_hours", 0),
                "absent": r.get("is_absent", False),
                "tasks": r.get("tasks_completed", 0),
                "util": r.get("utilization_pct"),
            })
            inserted += 1

    elif dataset_type == "ticket":
        for r in records:
            await db.execute(text("""
                INSERT INTO fact_tickets (ticket_number, created_date_id, category, priority, status, created_at, resolved_at, resolution_minutes, sla_target_minutes, sla_breached, description_summary)
                SELECT
                    :num,
                    (SELECT id FROM dim_date WHERE date = CAST(:created_at AS DATE) LIMIT 1),
                    :category, :priority, :status, :created_at, :resolved_at, :res_min, :sla_target, :sla_breached, :summary
                ON CONFLICT (ticket_number) DO UPDATE SET
                    status = EXCLUDED.status,
                    resolved_at = EXCLUDED.resolved_at,
                    resolution_minutes = EXCLUDED.resolution_minutes,
                    sla_breached = EXCLUDED.sla_breached
            """), {
                "num": r.get("ticket_number"),
                "created_at": r.get("created_at"),
                "category": r.get("category"),
                "priority": r.get("priority"),
                "status": r.get("status"),
                "resolved_at": r.get("resolved_at"),
                "res_min": r.get("resolution_minutes"),
                "sla_target": r.get("sla_target_minutes"),
                "sla_breached": r.get("sla_breached", False),
                "summary": r.get("description_summary"),
            })
            inserted += 1

    elif dataset_type == "market_signal":
        for r in records:
            await db.execute(text("""
                INSERT INTO fact_market_signals (date_id, signal_date, category, source, title, summary, sentiment_score, relevance_score)
                SELECT
                    (SELECT id FROM dim_date WHERE date = :sig_date LIMIT 1),
                    :sig_date, :category, :source, :title, :summary, :sentiment, :relevance
            """), {
                "sig_date": r.get("signal_date"),
                "category": r.get("category"),
                "source": r.get("source"),
                "title": r.get("title"),
                "summary": r.get("summary"),
                "sentiment": r.get("sentiment_score"),
                "relevance": r.get("relevance_score"),
            })
            inserted += 1

    return inserted


@router.get("/runs")
async def list_runs(
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(text("""
        SELECT run_id, source_type, source_name, target_table, status,
               rows_read, rows_inserted, rows_quarantined, started_at, completed_at
        FROM ingestion_run
        ORDER BY started_at DESC
        LIMIT :limit
    """), {"limit": limit})
    return [dict(r) for r in result.mappings().all()]


@router.get("/quarantine")
async def list_quarantine(
    run_id: str | None = Query(default=None),
    reviewed: bool | None = Query(default=None),
    limit: int = Query(default=50, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(text("""
        SELECT id, run_id, source_table, row_number, raw_data, error_codes, error_details, quarantined_at, reviewed
        FROM quarantined_row
        WHERE (:run_id IS NULL OR run_id = :run_id)
        AND (:reviewed IS NULL OR reviewed = :reviewed)
        ORDER BY quarantined_at DESC
        LIMIT :limit
    """), {"run_id": run_id, "reviewed": reviewed, "limit": limit})
    return [dict(r) for r in result.mappings().all()]
