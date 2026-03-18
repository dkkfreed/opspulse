from sqlalchemy import Column, Integer, String, Date, Boolean, Float, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class FactOperations(Base):
    __tablename__ = "fact_operations"

    id = Column(Integer, primary_key=True, index=True)
    date_id = Column(Integer, ForeignKey("dim_date.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("dim_employee.id"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("dim_department.id"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("dim_location.id"), index=True)

    # Scheduling metrics
    scheduled_hours = Column(Float, default=0.0)
    actual_hours = Column(Float, default=0.0)
    overtime_hours = Column(Float, default=0.0)
    absent = Column(Boolean, default=False)
    absence_reason = Column(String(100))

    # Productivity metrics
    tasks_completed = Column(Integer, default=0)
    tasks_assigned = Column(Integer, default=0)
    utilization_rate = Column(Float)  # actual/scheduled

    # Demand metrics
    demand_units = Column(Float, default=0.0)
    capacity_units = Column(Float, default=0.0)

    # Source tracking
    source_file = Column(String(255))
    ingested_at = Column(DateTime, server_default=func.now())

    date = relationship("DimDate")
    employee = relationship("DimEmployee", back_populates="operations")
    department = relationship("DimDepartment", back_populates="operations")
    location = relationship("DimLocation", back_populates="operations")


class FactTicket(Base):
    __tablename__ = "fact_ticket"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(50), unique=True, nullable=False, index=True)
    created_date_id = Column(Integer, ForeignKey("dim_date.id"), index=True)
    resolved_date_id = Column(Integer, ForeignKey("dim_date.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("dim_department.id"), index=True)

    category = Column(String(100), nullable=False)
    subcategory = Column(String(100))
    priority = Column(String(20), nullable=False)  # low, medium, high, critical
    status = Column(String(50), nullable=False)     # open, in_progress, resolved, closed

    created_at = Column(DateTime, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    sla_target_hours = Column(Float)
    actual_resolution_hours = Column(Float)
    sla_breached = Column(Boolean, default=False)

    channel = Column(String(50))   # email, phone, portal, chat
    sentiment_score = Column(Float)  # -1 to 1
    escalated = Column(Boolean, default=False)

    source_file = Column(String(255))
    ingested_at = Column(DateTime, server_default=func.now())

    created_date = relationship("DimDate", foreign_keys=[created_date_id])
    resolved_date = relationship("DimDate", foreign_keys=[resolved_date_id])
    department = relationship("DimDepartment", back_populates="tickets")


class FactMarketSignal(Base):
    __tablename__ = "fact_market_signal"

    id = Column(Integer, primary_key=True, index=True)
    date_id = Column(Integer, ForeignKey("dim_date.id"), index=True)
    signal_date = Column(Date, nullable=False, index=True)

    source = Column(String(100), nullable=False)
    category = Column(String(100), nullable=False)  # job_posting, news, sentiment
    subcategory = Column(String(100))
    region = Column(String(100))
    industry = Column(String(100))

    value = Column(Float)
    value_label = Column(String(100))
    change_pct = Column(Float)
    signal_metadata = Column(JSON)
    notes = Column(Text)

    source_file = Column(String(255))
    ingested_at = Column(DateTime, server_default=func.now())

    date = relationship("DimDate")


class StagingError(Base):
    __tablename__ = "staging_error"

    id = Column(Integer, primary_key=True, index=True)
    source_file = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)  # csv, json, api
    row_number = Column(Integer)
    raw_data = Column(JSON)
    error_type = Column(String(100), nullable=False)
    error_message = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
