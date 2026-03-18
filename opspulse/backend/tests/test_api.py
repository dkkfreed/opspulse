import pytest
from fastapi.testclient import TestClient
from datetime import date


class TestHealthCheck:
    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestWorkforceEndpoints:
    def test_summary_endpoint_returns_200(self, client):
        resp = client.get("/api/v1/workforce/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_employees" in data
        assert "avg_utilization_pct" in data

    def test_by_department_endpoint(self, client):
        resp = client.get("/api/v1/workforce/by-department")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_heatmap_endpoint(self, client):
        resp = client.get("/api/v1/workforce/utilization-heatmap")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_staffing_gaps_endpoint(self, client):
        resp = client.get("/api/v1/workforce/staffing-gaps")
        assert resp.status_code == 200

    def test_date_range_filter(self, client):
        resp = client.get(
            "/api/v1/workforce/summary",
            params={"start_date": "2024-01-01", "end_date": "2024-01-31"}
        )
        assert resp.status_code == 200


class TestTicketEndpoints:
    def test_summary_endpoint(self, client):
        resp = client.get("/api/v1/tickets/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "sla_breach_rate_pct" in data

    def test_trends_endpoint(self, client):
        resp = client.get("/api/v1/tickets/trends")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_sla_report(self, client):
        resp = client.get("/api/v1/tickets/sla-report")
        assert resp.status_code == 200

    def test_by_category(self, client):
        resp = client.get("/api/v1/tickets/by-category")
        assert resp.status_code == 200


class TestAnalyticsEndpoints:
    def test_forecast_invalid_metric(self, client):
        resp = client.get("/api/v1/analytics/forecast", params={"metric": "invalid_metric"})
        assert resp.status_code == 400

    def test_anomalies_endpoint(self, client):
        resp = client.get("/api/v1/analytics/anomalies")
        assert resp.status_code == 200

    def test_narrative_endpoint(self, client):
        resp = client.get("/api/v1/analytics/narrative")
        assert resp.status_code == 200
        data = resp.json()
        assert "headline" in data
        assert "summary" in data

    def test_narrative_invalid_role(self, client):
        resp = client.get("/api/v1/analytics/narrative", params={"role_level": "god_mode"})
        assert resp.status_code == 400

    def test_market_signals_endpoint(self, client):
        resp = client.get("/api/v1/analytics/market-signals")
        assert resp.status_code == 200
