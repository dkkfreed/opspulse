import pandas as pd
import numpy as np
from datetime import date
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def detect_zscore_anomalies(
    dates: List[date],
    values: List[float],
    metric: str,
    department_code: Optional[str] = None,
    z_threshold: float = 2.5,
) -> List[Dict]:
    """Detect anomalies using Z-score method with rolling window."""
    if len(values) < 7:
        return []

    series = pd.Series(values, index=pd.to_datetime(dates))
    rolling_mean = series.rolling(window=7, min_periods=3, center=True).mean()
    rolling_std = series.rolling(window=7, min_periods=3, center=True).std()

    z_scores = (series - rolling_mean) / rolling_std.replace(0, np.nan)

    anomalies = []
    for i, (d, val, z) in enumerate(zip(dates, values, z_scores)):
        if pd.isna(z) or abs(z) < z_threshold:
            continue

        severity = "low"
        if abs(z) > 4.0:
            severity = "critical"
        elif abs(z) > 3.5:
            severity = "high"
        elif abs(z) > 3.0:
            severity = "medium"

        likely_cause = _infer_cause(metric, val, float(rolling_mean.iloc[i]), z)

        anomalies.append({
            "date": d,
            "metric": metric,
            "department_code": department_code,
            "observed_value": float(val),
            "expected_value": float(rolling_mean.iloc[i]) if not pd.isna(rolling_mean.iloc[i]) else float(np.mean(values)),
            "z_score": float(z),
            "severity": severity,
            "likely_cause": likely_cause,
            "correlated_fields": {"rolling_window": 7, "threshold": z_threshold},
        })

    return anomalies


def detect_iqr_anomalies(
    dates: List[date],
    values: List[float],
    metric: str,
    department_code: Optional[str] = None,
    iqr_multiplier: float = 1.5,
) -> List[Dict]:
    """Detect anomalies using IQR method (robust to outliers)."""
    if len(values) < 4:
        return []

    arr = np.array(values)
    q1, q3 = np.percentile(arr, 25), np.percentile(arr, 75)
    iqr = q3 - q1
    lower_fence = q1 - iqr_multiplier * iqr
    upper_fence = q3 + iqr_multiplier * iqr
    median = np.median(arr)

    anomalies = []
    for d, val in zip(dates, values):
        if lower_fence <= val <= upper_fence:
            continue

        z_equiv = abs(val - median) / (iqr / 1.35 + 1e-9)
        severity = "medium" if z_equiv < 3.5 else "high"
        likely_cause = _infer_cause(metric, val, float(median), z_equiv)

        anomalies.append({
            "date": d,
            "metric": metric,
            "department_code": department_code,
            "observed_value": float(val),
            "expected_value": float(median),
            "z_score": round(z_equiv, 2),
            "severity": severity,
            "likely_cause": likely_cause,
            "correlated_fields": {"method": "iqr", "q1": q1, "q3": q3, "iqr": iqr},
        })

    return anomalies


def _infer_cause(metric: str, observed: float, expected: float, z: float) -> str:
    """Generate a human-readable likely cause based on the metric and direction."""
    direction = "spike" if observed > expected else "drop"
    magnitude = "significant" if abs(z) > 3.5 else "notable"

    cause_map = {
        "ticket_volume": {
            "spike": f"{magnitude.title()} increase in support demand — check for product issues or outages",
            "drop": f"{magnitude.title()} drop in ticket volume — possible reporting gap or holiday",
        },
        "absent": {
            "spike": f"{magnitude.title()} absenteeism spike — possible illness outbreak or scheduling conflict",
            "drop": "Unusually low absences — data completeness check recommended",
        },
        "utilization_rate": {
            "spike": "Over-utilization detected — risk of burnout and quality degradation",
            "drop": f"{magnitude.title()} under-utilization — demand mismatch or scheduling gap",
        },
        "demand_units": {
            "spike": f"{magnitude.title()} demand surge — verify staffing coverage",
            "drop": f"{magnitude.title()} demand drop — seasonal or external factor likely",
        },
    }

    default = {
        "spike": f"{magnitude.title()} upward deviation in {metric}",
        "drop": f"{magnitude.title()} downward deviation in {metric}",
    }

    return cause_map.get(metric, default).get(direction, f"Unusual value in {metric}")
