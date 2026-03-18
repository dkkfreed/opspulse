import pytest
from datetime import date, timedelta
from app.analytics.forecasting import forecast_metric, build_time_features
from app.analytics.anomaly_detection import detect_zscore_anomalies, detect_iqr_anomalies
import pandas as pd
import numpy as np


def make_dates_and_values(n=60, trend=0.5, noise=2.0):
    base = date(2024, 1, 1)
    dates = [base + timedelta(days=i) for i in range(n)]
    values = [20 + trend * i + np.random.normal(0, noise) for i in range(n)]
    return dates, values


class TestForecasting:
    def test_forecast_returns_expected_keys(self):
        dates, values = make_dates_and_values(60)
        result = forecast_metric(dates, values, horizon_days=14)
        assert "points" in result
        assert "mae" in result
        assert "rmse" in result
        assert "model_type" in result

    def test_forecast_returns_correct_count(self):
        dates, values = make_dates_and_values(60)
        result = forecast_metric(dates, values, horizon_days=14)
        # Historical + forecast
        assert len(result["points"]) == 60 + 14

    def test_forecast_future_flagged(self):
        dates, values = make_dates_and_values(30)
        result = forecast_metric(dates, values, horizon_days=7)
        future_pts = [p for p in result["points"] if p["is_forecast"]]
        historical_pts = [p for p in result["points"] if not p["is_forecast"]]
        assert len(future_pts) == 7
        assert len(historical_pts) == 30

    def test_lower_bound_below_upper(self):
        dates, values = make_dates_and_values(30)
        result = forecast_metric(dates, values, horizon_days=7)
        for p in result["points"]:
            assert p["lower_bound"] <= p["upper_bound"]

    def test_insufficient_data_raises(self):
        with pytest.raises(ValueError, match="at least 7"):
            forecast_metric([date(2024, 1, 1)], [10.0], horizon_days=7)


class TestAnomalyDetection:
    def test_no_anomalies_in_flat_series(self):
        base = date(2024, 1, 1)
        dates = [base + timedelta(days=i) for i in range(30)]
        values = [10.0] * 30
        alerts = detect_zscore_anomalies(dates, values, metric="ticket_volume")
        assert len(alerts) == 0

    def test_spike_detected(self):
        base = date(2024, 1, 1)
        dates = [base + timedelta(days=i) for i in range(30)]
        values = [10.0] * 30
        values[15] = 100.0  # massive spike
        alerts = detect_zscore_anomalies(dates, values, metric="ticket_volume", z_threshold=2.0)
        assert any(a["date"] == dates[15] for a in alerts)

    def test_anomaly_has_required_fields(self):
        base = date(2024, 1, 1)
        dates = [base + timedelta(days=i) for i in range(30)]
        values = [10.0] * 30
        values[15] = 100.0
        alerts = detect_zscore_anomalies(dates, values, metric="ticket_volume", z_threshold=1.5)
        if alerts:
            a = alerts[0]
            assert "date" in a
            assert "severity" in a
            assert "observed_value" in a
            assert "z_score" in a

    def test_iqr_method_detects_outlier(self):
        base = date(2024, 1, 1)
        dates = [base + timedelta(days=i) for i in range(20)]
        values = [5.0] * 20
        values[10] = 50.0
        alerts = detect_iqr_anomalies(dates, values, metric="demand_units")
        assert len(alerts) >= 1
