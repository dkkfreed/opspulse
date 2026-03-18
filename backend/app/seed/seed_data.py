"""
Seed script — generates and loads realistic synthetic data for OpsPulse.
Run with: python -m app.seed.seed_data
"""
import random
import logging
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal, create_tables
from app.models.dimensions import DimDepartment, DimLocation, DimEmployee, DimDate
from app.models.facts import FactOperations, FactTicket, FactMarketSignal
from app.etl.loader import upsert_dim_date
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

random.seed(42)
np.random.seed(42)

DEPARTMENTS = [
    {"code": "ENG", "name": "Engineering", "division": "Technology", "headcount_target": 45},
    {"code": "OPS", "name": "Operations", "division": "Operations", "headcount_target": 30},
    {"code": "SUPPORT", "name": "Customer Support", "division": "Operations", "headcount_target": 25},
    {"code": "SALES", "name": "Sales", "division": "Revenue", "headcount_target": 20},
    {"code": "HR", "name": "Human Resources", "division": "People", "headcount_target": 10},
    {"code": "FINANCE", "name": "Finance", "division": "Corporate", "headcount_target": 12},
]

LOCATIONS = [
    {"code": "TOR", "city": "Toronto", "region": "Ontario"},
    {"code": "VAN", "city": "Vancouver", "region": "British Columbia"},
    {"code": "MTL", "city": "Montreal", "region": "Quebec"},
    {"code": "REMOTE", "city": "Remote", "region": "Canada-wide", "is_remote": True},
]

ROLES = ["Engineer", "Analyst", "Specialist", "Manager", "Lead", "Coordinator", "Associate"]
LEVELS = ["junior", "mid", "senior", "lead"]
EMP_TYPES = ["full-time", "full-time", "full-time", "part-time", "contract"]
FIRST_NAMES = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Cameron",
               "Blake", "Drew", "Skyler", "Devon", "Quinn", "Reese", "Sage", "Kai"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Wilson", "Martinez", "Anderson", "Taylor", "Thomas", "Hernandez", "Moore"]

TICKET_CATEGORIES = ["technical", "billing", "onboarding", "access_request", "data_quality",
                     "performance", "feature_request", "compliance", "hr_inquiry"]
CHANNELS = ["email", "portal", "phone", "chat"]
PRIORITIES = ["low", "medium", "high", "critical"]
PRIORITY_WEIGHTS = [0.3, 0.4, 0.2, 0.1]
MARKET_SOURCES = ["linkedin_postings", "indeed_trends", "statscan", "glassdoor", "industry_report"]
MARKET_CATEGORIES = ["job_posting", "sentiment", "demand_index", "talent_supply"]
INDUSTRIES = ["Technology", "Finance", "Healthcare", "Retail", "Manufacturing"]


def seed_all():
    create_tables()
    db = SessionLocal()
    try:
        logger.info("Seeding departments...")
        dept_map = {}
        for d in DEPARTMENTS:
            existing = db.query(DimDepartment).filter(DimDepartment.code == d["code"]).first()
            if not existing:
                dept = DimDepartment(**d)
                db.add(dept)
                db.flush()
                dept_map[d["code"]] = dept
            else:
                dept_map[d["code"]] = existing
        db.commit()

        logger.info("Seeding locations...")
        loc_map = {}
        for l in LOCATIONS:
            existing = db.query(DimLocation).filter(DimLocation.code == l["code"]).first()
            if not existing:
                loc = DimLocation(**l)
                db.add(loc)
                db.flush()
                loc_map[l["code"]] = loc
            else:
                loc_map[l["code"]] = existing
        db.commit()

        logger.info("Seeding employees...")
        employees = []
        emp_id = 1001
        for dept_code, dept in dept_map.items():
            for _ in range(dept.headcount_target):
                loc = random.choice(list(loc_map.values()))
                existing = db.query(DimEmployee).filter(
                    DimEmployee.employee_id == f"EMP{emp_id}"
                ).first()
                if not existing:
                    emp = DimEmployee(
                        employee_id=f"EMP{emp_id}",
                        first_name=random.choice(FIRST_NAMES),
                        last_name=random.choice(LAST_NAMES),
                        email=f"emp{emp_id}@company.com",
                        role=random.choice(ROLES),
                        level=random.choice(LEVELS),
                        employment_type=random.choice(EMP_TYPES),
                        department_id=dept.id,
                        location_id=loc.id,
                        hire_date=date(
                            random.randint(2019, 2023),
                            random.randint(1, 12),
                            random.randint(1, 28),
                        ),
                        is_active=True,
                    )
                    db.add(emp)
                    db.flush()
                    employees.append(emp)
                else:
                    employees.append(existing)
                emp_id += 1
        db.commit()
        logger.info(f"Seeded {len(employees)} employees")

        logger.info("Seeding operations facts (90 days)...")
        end_date = date.today()
        start_date = end_date - timedelta(days=90)
        ops_count = 0

        current = start_date
        while current <= end_date:
            dim_date = upsert_dim_date(db, current)
            is_weekend = current.weekday() >= 5

            for emp in employees:
                if is_weekend and emp.employment_type != "contract":
                    current = current + timedelta(days=1) if is_weekend else current
                    continue

                base_scheduled = 8.0 if emp.employment_type == "full-time" else 4.0
                dept_code = emp.department.code if emp.department else "OPS"

                # Inject anomaly: SUPPORT dept has spike in week 6-7
                anomaly_boost = 0
                day_num = (current - start_date).days
                if dept_code == "SUPPORT" and 35 <= day_num <= 42:
                    anomaly_boost = random.uniform(2, 5)

                # Seasonal trend: slight increase over time
                trend_factor = 1.0 + (day_num / 90) * 0.1

                absent = random.random() < 0.04
                actual_hours = 0.0 if absent else (
                    base_scheduled * random.uniform(0.85, 1.15) * trend_factor + anomaly_boost
                )
                overtime = max(0, actual_hours - base_scheduled)

                demand = base_scheduled * random.uniform(0.9, 1.3) * trend_factor
                capacity = base_scheduled * 0.95

                record = FactOperations(
                    date_id=dim_date.id,
                    employee_id=emp.id,
                    department_id=emp.department_id,
                    location_id=emp.location_id,
                    scheduled_hours=base_scheduled,
                    actual_hours=round(actual_hours, 2),
                    overtime_hours=round(overtime, 2),
                    absent=absent,
                    absence_reason=random.choice(["sick", "personal", "vacation", ""]) if absent else "",
                    tasks_completed=random.randint(0 if absent else 3, 12),
                    tasks_assigned=random.randint(5, 15),
                    utilization_rate=round(actual_hours / base_scheduled, 3) if base_scheduled > 0 else 0,
                    demand_units=round(demand, 2),
                    capacity_units=round(capacity, 2),
                    source_file="seed_data",
                )
                db.add(record)
                ops_count += 1

            db.commit()
            current += timedelta(days=1)

        logger.info(f"Seeded {ops_count} operations records")

        logger.info("Seeding tickets (90 days)...")
        ticket_id = 1
        sla_map = {"critical": 4, "high": 8, "medium": 24, "low": 72}
        current = start_date
        while current <= end_date:
            day_num = (current - start_date).days
            # Volume trend + anomaly
            base_volume = int(15 + day_num * 0.3 + random.normalvariate(0, 3))
            if 35 <= day_num <= 42:
                base_volume = int(base_volume * 1.8)
            base_volume = max(5, base_volume)

            for _ in range(base_volume):
                priority = random.choices(PRIORITIES, weights=PRIORITY_WEIGHTS)[0]
                category = random.choice(TICKET_CATEGORIES)
                dept = random.choice(list(dept_map.values()))
                sla_hours = sla_map[priority]

                created_at = datetime.combine(current, datetime.min.time()).replace(
                    hour=random.randint(7, 19), minute=random.randint(0, 59)
                )

                # 70% resolved
                resolved_at = None
                resolution_hours = None
                status = "open"
                if random.random() < 0.70:
                    res_hours = random.expovariate(1 / (sla_hours * 0.8))
                    resolution_hours = round(min(res_hours, sla_hours * 3), 2)
                    resolved_at = created_at + timedelta(hours=resolution_hours)
                    if resolved_at.date() > end_date:
                        resolved_at = None
                        resolution_hours = None
                        status = "in_progress"
                    else:
                        status = random.choice(["resolved", "closed"])
                elif random.random() < 0.4:
                    status = "in_progress"

                sla_breached = False
                if resolution_hours and resolution_hours > sla_hours:
                    sla_breached = True
                elif status in ("open", "in_progress"):
                    open_hours = (datetime.utcnow() - created_at).total_seconds() / 3600
                    sla_breached = open_hours > sla_hours

                dim_date = upsert_dim_date(db, current)
                resolved_date_id = None
                if resolved_at:
                    rd = upsert_dim_date(db, resolved_at.date())
                    resolved_date_id = rd.id

                record = FactTicket(
                    ticket_id=f"TKT-{ticket_id:05d}",
                    created_date_id=dim_date.id,
                    resolved_date_id=resolved_date_id,
                    department_id=dept.id,
                    category=category,
                    subcategory=f"{category}_sub",
                    priority=priority,
                    status=status,
                    created_at=created_at,
                    resolved_at=resolved_at,
                    sla_target_hours=float(sla_hours),
                    actual_resolution_hours=resolution_hours,
                    sla_breached=sla_breached,
                    channel=random.choice(CHANNELS),
                    sentiment_score=round(random.uniform(-0.8, 0.8), 2),
                    escalated=random.random() < 0.05,
                    source_file="seed_data",
                )
                db.add(record)
                ticket_id += 1

            db.commit()
            current += timedelta(days=1)

        logger.info(f"Seeded {ticket_id - 1} tickets")

        logger.info("Seeding market signals (90 days)...")
        current = start_date
        while current <= end_date:
            dim_date = upsert_dim_date(db, current)
            for _ in range(random.randint(3, 8)):
                record = FactMarketSignal(
                    date_id=dim_date.id,
                    signal_date=current,
                    source=random.choice(MARKET_SOURCES),
                    category=random.choice(MARKET_CATEGORIES),
                    region=random.choice(["Ontario", "BC", "Quebec", "National"]),
                    industry=random.choice(INDUSTRIES),
                    value=round(random.uniform(50, 200), 2),
                    value_label="index_points",
                    change_pct=round(random.uniform(-8, 12), 2),
                    notes=f"Market signal for {current}",
                    source_file="seed_data",
                )
                db.add(record)
            db.commit()
            current += timedelta(days=1)

        logger.info("Seeding complete!")

    except Exception as e:
        logger.exception(f"Seeding failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
