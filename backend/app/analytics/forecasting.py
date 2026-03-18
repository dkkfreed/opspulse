import pandas as pd
import numpy as np
from datetime import date, timedelta
from typing import Optional, List, Dict
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import logging

logger = logging.getLogger(__name__)


def build_time_features(dates: pd.Series) -> pd.DataFrame:
    """Create time-based features for regression forecasting."""
    df = pd.DataFrame({"date": pd.to_datetime(dates)})
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_month"] = df["date"].dt.day
    df["month"] = df["date"].dt.month
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["t"] = (df["date"] - df["date"].min()).dt.days
    # Cyclic encoding
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    return df.drop(columns=["date"])


def forecast_metric(
    historical_dates: List[date],
    historical_values: List[float],
    horizon_days: int = 30,
    confidence: float = 0.95,
) -> Dict:
    """
    Forecast a metric using Ridge regression with time features.
    Returns dict with predictions and confidence intervals.
    """
    if len(historical_dates) < 7:
        raise ValueError("Need at least 7 data points to forecast")

    dates_series = pd.Series(historical_dates)
    values = np.array(historical_values, dtype=float)

    # Fill any NaN in values
    nan_mask = np.isnan(values)
    if nan_mask.any():
        values[nan_mask] = np.nanmean(values)

    X_hist = build_time_features(dates_series)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_hist)

    model = Ridge(alpha=1.0)
    model.fit(X_scaled, values)

    # Evaluate in-sample
    y_pred_train = model.predict(X_scaled)
    residuals = values - y_pred_train
    residual_std = np.std(residuals)
    mae = mean_absolute_error(values, y_pred_train)
    rmse = float(np.sqrt(mean_squared_error(values, y_pred_train)))

    # Generate future dates
    last_date = max(historical_dates)
    future_dates = [last_date + timedelta(days=i + 1) for i in range(horizon_days)]
    all_dates = list(historical_dates) + future_dates

    future_dates_series = pd.Series(future_dates)
    X_future = build_time_features(future_dates_series)
    X_future_scaled = scaler.transform(X_future)
    y_future = model.predict(X_future_scaled)

    # Confidence interval (normal approximation)
    z = 1.96 if confidence >= 0.95 else 1.645
    margin = z * residual_std

    results = []
    # Historical actuals
    for d, v, pred in zip(historical_dates, values, y_pred_train):
        results.append({
            "date": d,
            "predicted": float(pred),
            "lower_bound": float(pred - margin),
            "upper_bound": float(pred + margin),
            "is_forecast": False,
        })

    # Future forecast
    for d, pred in zip(future_dates, y_future):
        results.append({
            "date": d,
            "predicted": max(0, float(pred)),
            "lower_bound": max(0, float(pred - margin)),
            "upper_bound": max(0, float(pred + margin)),
            "is_forecast": True,
        })

    return {
        "points": results,
        "mae": float(mae),
        "rmse": rmse,
        "model_type": "ridge_regression",
        "confidence_interval": confidence,
    }
