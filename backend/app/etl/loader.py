import pandas as pd
import logging
from datetime import date, datetime
from sqlalchemy.orm import Session
from app.models.dimensions import DimDate, DimDepartment, DimLocation, DimEmployee
from app.models.facts import FactOperations, FactTicket, FactMarketSignal, StagingError

logger = logging.getLogger(__name__)


def upsert_dim_date(db: Session, target_date: date) -> DimDate:
    """Get or create a DimDate record."""
    existing = db.query(DimDate).filter(DimDate.date == target_date).first()
    if existing:
        return existing

    from calendar import day_name, month_name
    d = datetime.combine(target_date, datetime.min.time())
    record = DimDate(
        date=target_date,
        year=target_date.year,
        quarter=(target_date.month - 1) // 3 + 1,
        month=target_date.month,
        month_name=month_name[target_date.month],
        week_of_year=int(target_date.strftime("%W")),
        day_of_week=target_date.weekday(),
        day_name=day_name[target_date.weekday()],
        is_weekend=target_date.weekday() >= 5,
        fiscal_year=target_date.year if target_date.month >= 4 else target_date.year - 1,
        fiscal_quarter=((target_date.month - 4) % 12) // 3 + 1 if target_date.month >= 4
                       else ((target_date.month + 8) % 12) // 3 + 1,
    )
    db.add(record)
    db.flush()
    return record


def get_or_create_department(db: Session, code: str, name: str = None) -> DimDepartment:
    existing = db.query(DimDepartment).filter(DimDepartment.code == code).first()
    if existing:
        return existing
    dept = DimDepartment(code=code, name=name or code.title())
    db.add(dept)
    db.flush()
    return dept


def get_or_create_location(db: Session, code: str, city: str = None) -> DimLocation:
    existing = db.query(DimLocation).filter(DimLocation.code == code).first()
    if existing:
        return existing
    loc = DimLocation(code=code, city=city or code.title())
    db.add(loc)
    db.flush()
    return loc


def get_or_create_employee(db: Session, employee_id: str, dept_id: int, loc_id: int, row: dict) -> DimEmployee:
    existing = db.query(DimEmployee).filter(DimEmployee.employee_id == employee_id).first()
    if existing:
        return existing
    emp = DimEmployee(
        employee_id=employee_id,
        first_name=row.get("first_name", "Unknown"),
        last_name=row.get("last_name", "Employee"),
        email=row.get("email", f"{employee_id.lower()}@company.com"),
        role=row.get("role", "Staff"),
        level=row.get("level", "mid"),
        employment_type=row.get("employment_type", "full-time"),
        department_id=dept_id,
        location_id=loc_id,
    )
    db.add(emp)
    db.flush()
    return emp


def load_workforce(db: Session, df: pd.DataFrame, source_file: str) -> int:
    """Load cleaned workforce DataFrame into fact_operations."""
    loaded = 0
    for _, row in df.iterrows():
        try:
            dim_date = upsert_dim_date(db, row["date"].date() if hasattr(row["date"], "date") else row["date"])
            dept = get_or_create_department(db, str(row.get("department_code", "UNKNOWN")))
            loc_code = str(row.get("location_code", "HQ"))
            loc = get_or_create_location(db, loc_code)
            emp = get_or_create_employee(
                db, str(row["employee_id"]), dept.id, loc.id, row.to_dict()
            )

            record = FactOperations(
                date_id=dim_date.id,
                employee_id=emp.id,
                department_id=dept.id,
                location_id=loc.id,
                scheduled_hours=float(row.get("scheduled_hours", 0)),
                actual_hours=float(row.get("actual_hours", 0)),
                overtime_hours=float(row.get("overtime_hours", 0)),
                absent=bool(row.get("absent", False)),
                absence_reason=str(row.get("absence_reason", "")),
                tasks_completed=int(row.get("tasks_completed", 0)),
                tasks_assigned=int(row.get("tasks_assigned", 0)),
                utilization_rate=float(row.get("utilization_rate", 0)),
                demand_units=float(row.get("demand_units", 0)),
                capacity_units=float(row.get("capacity_units", 0)),
                source_file=source_file,
            )
            db.add(record)
            loaded += 1
        except Exception as e:
            logger.error(f"Failed to load workforce row: {e}")
            db.add(StagingError(
                source_file=source_file,
                source_type="workforce",
                raw_data=row.to_dict(),
                error_type=type(e).__name__,
                error_message=str(e),
            ))

    db.commit()
    logger.info(f"Loaded {loaded} workforce records from {source_file}")
    return loaded


def load_tickets(db: Session, df: pd.DataFrame, source_file: str) -> int:
    """Load cleaned tickets DataFrame into fact_ticket."""
    loaded = 0
    for _, row in df.iterrows():
        try:
            # Skip if ticket already exists
            existing = db.query(FactTicket).filter(
                FactTicket.ticket_id == str(row["ticket_id"])
            ).first()
            if existing:
                continue

            created_dt = row["created_at"]
            created_date = upsert_dim_date(db, created_dt.date() if hasattr(created_dt, "date") else created_dt)
            resolved_date_id = None
            if pd.notna(row.get("resolved_at")):
                rd = upsert_dim_date(db, row["resolved_at"].date())
                resolved_date_id = rd.id

            dept = get_or_create_department(db, str(row.get("department_code", "UNKNOWN")))

            resolution_hours = row.get("actual_resolution_hours")
            if pd.isna(resolution_hours) if isinstance(resolution_hours, float) else False:
                resolution_hours = None

            record = FactTicket(
                ticket_id=str(row["ticket_id"]),
                created_date_id=created_date.id,
                resolved_date_id=resolved_date_id,
                department_id=dept.id,
                category=str(row.get("category", "general")),
                subcategory=str(row.get("subcategory", "")) or None,
                priority=str(row.get("priority", "medium")),
                status=str(row.get("status", "open")),
                created_at=created_dt,
                resolved_at=row.get("resolved_at") if pd.notna(row.get("resolved_at")) else None,
                sla_target_hours=float(row.get("sla_target_hours", 24)),
                actual_resolution_hours=float(resolution_hours) if resolution_hours is not None else None,
                sla_breached=bool(row.get("sla_breached", False)),
                channel=str(row.get("channel", "portal")),
                sentiment_score=float(row.get("sentiment_score", 0)),
                escalated=bool(row.get("escalated", False)),
                source_file=source_file,
            )
            db.add(record)
            loaded += 1
        except Exception as e:
            logger.error(f"Failed to load ticket row: {e}")
            db.add(StagingError(
                source_file=source_file,
                source_type="tickets",
                raw_data={k: str(v) for k, v in row.to_dict().items()},
                error_type=type(e).__name__,
                error_message=str(e),
            ))

    db.commit()
    logger.info(f"Loaded {loaded} ticket records from {source_file}")
    return loaded


def load_market_signals(db: Session, df: pd.DataFrame, source_file: str) -> int:
    """Load cleaned market signals into fact_market_signal."""
    loaded = 0
    for _, row in df.iterrows():
        try:
            signal_date = row["signal_date"]
            dim_date = upsert_dim_date(db, signal_date.date() if hasattr(signal_date, "date") else signal_date)

            record = FactMarketSignal(
                date_id=dim_date.id,
                signal_date=signal_date.date() if hasattr(signal_date, "date") else signal_date,
                source=str(row.get("source", "unknown")),
                category=str(row.get("category", "general")),
                subcategory=str(row.get("subcategory", "")) or None,
                region=str(row.get("region", "")) or None,
                industry=str(row.get("industry", "")) or None,
                value=float(row.get("value", 0)),
                value_label=str(row.get("value_label", "")) or None,
                change_pct=float(row.get("change_pct", 0)),
                notes=str(row.get("notes", "")) or None,
                source_file=source_file,
            )
            db.add(record)
            loaded += 1
        except Exception as e:
            logger.error(f"Failed to load market signal row: {e}")

    db.commit()
    logger.info(f"Loaded {loaded} market signal records from {source_file}")
    return loaded
