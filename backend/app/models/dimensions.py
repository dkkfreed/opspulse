from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class DimDepartment(Base):
    __tablename__ = "dim_department"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    division = Column(String(100))
    cost_center = Column(String(20))
    manager_name = Column(String(100))
    headcount_target = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    employees = relationship("DimEmployee", back_populates="department")
    operations = relationship("FactOperations", back_populates="department")
    tickets = relationship("FactTicket", back_populates="department")


class DimLocation(Base):
    __tablename__ = "dim_location"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    city = Column(String(100), nullable=False)
    region = Column(String(100))
    country = Column(String(100), default="Canada")
    timezone = Column(String(50), default="America/Toronto")
    is_remote = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    employees = relationship("DimEmployee", back_populates="location")
    operations = relationship("FactOperations", back_populates="location")


class DimEmployee(Base):
    __tablename__ = "dim_employee"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(20), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(200), unique=True)
    role = Column(String(100))
    level = Column(String(50))  # junior, mid, senior, lead
    employment_type = Column(String(50))  # full-time, part-time, contract
    department_id = Column(Integer, ForeignKey("dim_department.id"))
    location_id = Column(Integer, ForeignKey("dim_location.id"))
    hire_date = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    department = relationship("DimDepartment", back_populates="employees")
    location = relationship("DimLocation", back_populates="employees")
    operations = relationship("FactOperations", back_populates="employee")


class DimDate(Base):
    __tablename__ = "dim_date"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, nullable=False, index=True)
    year = Column(Integer, nullable=False)
    quarter = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    month_name = Column(String(20), nullable=False)
    week_of_year = Column(Integer, nullable=False)
    day_of_week = Column(Integer, nullable=False)
    day_name = Column(String(20), nullable=False)
    is_weekend = Column(Boolean, nullable=False)
    is_holiday = Column(Boolean, default=False)
    fiscal_year = Column(Integer)
    fiscal_quarter = Column(Integer)
