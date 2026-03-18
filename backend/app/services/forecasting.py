"""
Forecasting Service
Provides baseline time-series forecasting for ticket volume and demand.
Uses exponential smoothing (Holt-Winters) with fallback to linear trend.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np
import pandas as pd
from datetime import date, timedelta


@dataclass
class ForecastPoint:
    date: str
    forecast: float
    lower_ci: float
    upper_ci: float
    is_actual: bool = False
    actual: float | None = None


@dataclass
class ForecastResult:
    metric: str
    horizon_days: int
    points: list[ForecastPoint]
    methodology: str
    mape: float | None  # Mean absolute percentage error on holdout
    trend_direction: str  # "up" | "down" | "flat"
    summary: str


class ForecastingService:
    """
    Time-series forecasting using exponential smoothing.
    Automatically selects model complexity based on data availability.
    """

    def forecast_ticket_volume(
        self,
        daily_counts: pd.Series,  # index=date, values=ticket count
        horizon: int = 30,
    ) -> ForecastResult:
        return self._run_forecast(daily_counts, horizon, "ticket_volume")

    def forecast_demand(
        self,
        daily_demand: pd.Series,
        horizon: int = 30,
    ) -> ForecastResult:
        return self._run_forecast(daily_demand, horizon, "demand")

    def _run_forecast(self, series: pd.Series, horizon: int, metric: str) -> ForecastResult:
        series = series.sort_index().dropna()
        if len(series) < 7:
            return self._naive_forecast(series, horizon, metric)

        try:
            return self._exponential_smoothing_forecast(series, horizon, metric)
        except Exception:
            return self._linear_trend_forecast(series, horizon, metric)

    def _exponential_smoothing_forecast(
        self, series: pd.Series, horizon: int, metric: str
    ) -> ForecastResult:
        """Simple exponential smoothing with trend using statsmodels if available."""
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            n = len(series)
            # Use holdout of 20% for MAPE calculation
            holdout = max(7, int(n * 0.2))
            train = series[:-holdout]
            test = series[-holdout:]

            seasonal = "add" if n >= 28 else None
            seasonal_periods = 7 if seasonal and n >= 28 else None

            model = ExponentialSmoothing(
                train,
                trend="add",
                seasonal=seasonal,
                seasonal_periods=seasonal_periods,
                initialization_method="estimated",
            ).fit(optimized=True)

            # MAPE on holdout
            holdout_pred = model.forecast(len(test))
            mask = test != 0
            mape = float(np.mean(np.abs((test[mask] - holdout_pred[mask]) / test[mask])) * 100) if mask.any() else None

            # Fit on full series for forward forecast
            full_model = ExponentialSmoothing(
                series,
                trend="add",
                seasonal=seasonal,
                seasonal_periods=seasonal_periods,
                initialization_method="estimated",
            ).fit(optimized=True)

            forecast_vals = full_model.forecast(horizon)
            residuals = series - full_model.fittedvalues
            std_resid = float(residuals.std())

            points = self._build_points(series, forecast_vals, std_resid)
            trend = self._detect_trend(forecast_vals)

            return ForecastResult(
                metric=metric,
                horizon_days=horizon,
                points=points,
                methodology="Holt-Winters Exponential Smoothing",
                mape=round(mape, 1) if mape is not None else None,
                trend_direction=trend,
                summary=self._summarize(metric, series, forecast_vals, trend),
            )
        except ImportError:
            return self._linear_trend_forecast(series, horizon, metric)

    def _linear_trend_forecast(self, series: pd.Series, horizon: int, metric: str) -> ForecastResult:
        """Linear regression trend fallback."""
        x = np.arange(len(series))
        y = series.values.astype(float)
        slope, intercept = np.polyfit(x, y, 1)

        future_x = np.arange(len(series), len(series) + horizon)
        forecast_vals_arr = slope * future_x + intercept
        residuals = y - (slope * x + intercept)
        std_resid = float(np.std(residuals))

        last_date = series.index[-1]
        if isinstance(last_date, str):
            last_date = pd.to_datetime(last_date).date()

        forecast_index = pd.date_range(
            start=last_date + timedelta(days=1), periods=horizon, freq="D"
        )
        forecast_vals = pd.Series(forecast_vals_arr, index=forecast_index)
        trend = "up" if slope > 0.1 else ("down" if slope < -0.1 else "flat")

        points = self._build_points(series, forecast_vals, std_resid)
        return ForecastResult(
            metric=metric,
            horizon_days=horizon,
            points=points,
            methodology="Linear Trend Regression",
            mape=None,
            trend_direction=trend,
            summary=self._summarize(metric, series, forecast_vals, trend),
        )

    def _naive_forecast(self, series: pd.Series, horizon: int, metric: str) -> ForecastResult:
        """Mean-based naive forecast for very short series."""
        mean_val = float(series.mean())
        std_val = float(series.std()) if len(series) > 1 else 0.0
        last_date = series.index[-1]
        if isinstance(last_date, str):
            last_date = pd.to_datetime(last_date).date()
        forecast_index = pd.date_range(start=last_date + timedelta(days=1), periods=horizon, freq="D")
        forecast_vals = pd.Series([mean_val] * horizon, index=forecast_index)
        points = self._build_points(series, forecast_vals, std_val)
        return ForecastResult(
            metric=metric,
            horizon_days=horizon,
            points=points,
            methodology="Naive Mean Forecast",
            mape=None,
            trend_direction="flat",
            summary=f"Insufficient history for trend analysis. Forecasting flat at mean of {mean_val:.1f}.",
        )

    def _build_points(
        self,
        actuals: pd.Series,
        forecast: pd.Series,
        std_resid: float,
        ci_multiplier: float = 1.96,
    ) -> list[ForecastPoint]:
        points = []
        # Last 60 actual points
        for dt, val in actuals.tail(60).items():
            d = dt.date() if hasattr(dt, "date") else dt
            points.append(ForecastPoint(
                date=str(d),
                forecast=round(float(val), 2),
                lower_ci=round(float(val), 2),
                upper_ci=round(float(val), 2),
                is_actual=True,
                actual=round(float(val), 2),
            ))
        # Forecast points
        ci = ci_multiplier * std_resid
        for i, (dt, val) in enumerate(forecast.items()):
            d = dt.date() if hasattr(dt, "date") else dt
            growing_ci = ci * (1 + i * 0.02)  # Widen CI over horizon
            points.append(ForecastPoint(
                date=str(d),
                forecast=round(max(0, float(val)), 2),
                lower_ci=round(max(0, float(val) - growing_ci), 2),
                upper_ci=round(max(0, float(val) + growing_ci), 2),
                is_actual=False,
            ))
        return points

    def _detect_trend(self, forecast: pd.Series) -> str:
        if len(forecast) < 2:
            return "flat"
        first_half = forecast[: len(forecast) // 2].mean()
        second_half = forecast[len(forecast) // 2 :].mean()
        pct_change = (second_half - first_half) / (first_half + 1e-9)
        if pct_change > 0.05:
            return "up"
        elif pct_change < -0.05:
            return "down"
        return "flat"

    def _summarize(self, metric: str, actuals: pd.Series, forecast: pd.Series, trend: str) -> str:
        recent_avg = actuals.tail(7).mean()
        forecast_avg = forecast.mean()
        pct = ((forecast_avg - recent_avg) / (recent_avg + 1e-9)) * 100
        direction = "increase" if pct > 0 else "decrease"
        return (
            f"{metric.replace('_', ' ').title()} is forecast to {direction} by "
            f"{abs(pct):.1f}% over the next {len(forecast)} days "
            f"(from avg {recent_avg:.1f} to {forecast_avg:.1f}). "
            f"Trend direction: {trend}."
        )
