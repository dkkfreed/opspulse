from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date


class ForecastPoint(BaseModel):
    date: date
    predicted: float
    lower_bound: float
    upper_bound: float
    is_forecast: bool


class ForecastResult(BaseModel):
    metric: str
    department_code: Optional[str] = None
    horizon_days: int
    model_type: str
    mae: Optional[float] = None
    rmse: Optional[float] = None
    confidence_interval: float
    points: List[ForecastPoint]


class AnomalyAlert(BaseModel):
    date: date
    metric: str
    department_code: Optional[str] = None
    observed_value: float
    expected_value: float
    z_score: float
    severity: str
    likely_cause: Optional[str] = None
    correlated_fields: Optional[Dict[str, Any]] = None


class NarrativeInsight(BaseModel):
    generated_at: str
    period: str
    role_level: str
    headline: str
    summary: str
    key_findings: List[str]
    alerts: List[str]
    recommendations: List[str]
