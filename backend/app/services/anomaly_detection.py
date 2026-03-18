"""
Anomaly Detection Service
Uses IsolationForest for multivariate anomalies and Z-score for univariate spikes.
Surfaces likely reasons using correlated field analysis.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class Anomaly:
    date: str
    metric: str
    observed_value: float
    expected_range: tuple[float, float]
    severity: str  # "warning" | "critical"
    anomaly_score: float
    likely_reasons: list[str]
    correlated_fields: dict[str, float]


@dataclass
class AnomalyReport:
    anomalies: list[Anomaly]
    total_points_analyzed: int
    anomaly_rate: float
    detection_method: str
    summary: str


class AnomalyDetectionService:

    def detect_ticket_anomalies(
        self,
        daily_df: pd.DataFrame,  # columns: date, ticket_count, + optional correlates
        contamination: float = 0.05,
    ) -> AnomalyReport:
        return self._detect(daily_df, "ticket_count", contamination, "tickets")

    def detect_workforce_anomalies(
        self,
        daily_df: pd.DataFrame,  # columns: date, utilization_pct, absent_count, etc.
        contamination: float = 0.05,
    ) -> AnomalyReport:
        return self._detect(daily_df, "utilization_pct", contamination, "workforce")

    def _detect(
        self,
        df: pd.DataFrame,
        primary_col: str,
        contamination: float,
        context: str,
    ) -> AnomalyReport:
        df = df.copy().sort_values("date").reset_index(drop=True)
        if primary_col not in df.columns or len(df) < 10:
            return AnomalyReport(
                anomalies=[],
                total_points_analyzed=len(df),
                anomaly_rate=0.0,
                detection_method="none — insufficient data",
                summary="Not enough data for anomaly detection (minimum 10 data points).",
            )

        numeric_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c != "date"]
        feature_df = df[numeric_cols].fillna(df[numeric_cols].median())

        # --- IsolationForest ---
        try:
            from sklearn.ensemble import IsolationForest
            from sklearn.preprocessing import StandardScaler

            scaler = StandardScaler()
            X = scaler.fit_transform(feature_df)
            clf = IsolationForest(contamination=contamination, random_state=42)
            labels = clf.fit_predict(X)  # -1 = anomaly
            scores = clf.score_samples(X)   # lower = more anomalous
            method = "IsolationForest"
        except ImportError:
            labels, scores = self._zscore_labels(df[primary_col], contamination)
            method = "Z-Score"

        # --- Z-score baseline for expected range ---
        col_mean = df[primary_col].mean()
        col_std = df[primary_col].std()
        expected_lo = col_mean - 2 * col_std
        expected_hi = col_mean + 2 * col_std

        anomalies = []
        for i, (lbl, score) in enumerate(zip(labels, scores)):
            if lbl == -1:
                row = df.iloc[i]
                val = float(row.get(primary_col, 0))
                z = abs(val - col_mean) / (col_std + 1e-9)
                severity = "critical" if z > 3 else "warning"
                reasons = self._infer_reasons(row, primary_col, col_mean, col_std, context)
                correlates = {
                    c: round(float(row[c]), 2)
                    for c in numeric_cols
                    if c != primary_col and pd.notna(row.get(c))
                }
                anomalies.append(Anomaly(
                    date=str(row["date"]),
                    metric=primary_col,
                    observed_value=round(val, 2),
                    expected_range=(round(expected_lo, 2), round(expected_hi, 2)),
                    severity=severity,
                    anomaly_score=round(float(score), 4),
                    likely_reasons=reasons,
                    correlated_fields=correlates,
                ))

        rate = len(anomalies) / max(len(df), 1)
        return AnomalyReport(
            anomalies=sorted(anomalies, key=lambda a: a.anomaly_score),
            total_points_analyzed=len(df),
            anomaly_rate=round(rate, 4),
            detection_method=method,
            summary=self._build_summary(anomalies, primary_col),
        )

    def _zscore_labels(
        self, series: pd.Series, contamination: float
    ) -> tuple[np.ndarray, np.ndarray]:
        z = np.abs((series - series.mean()) / (series.std() + 1e-9))
        threshold = np.quantile(z, 1 - contamination)
        labels = np.where(z >= threshold, -1, 1)
        scores = -z  # lower = more anomalous
        return labels, scores

    def _infer_reasons(
        self,
        row: pd.Series,
        primary_col: str,
        mean: float,
        std: float,
        context: str,
    ) -> list[str]:
        reasons = []
        val = float(row.get(primary_col, 0))

        if context == "tickets":
            if val > mean + 2 * std:
                reasons.append("Unusually high ticket volume — possible system incident or product release")
            if row.get("critical_count", 0) > 0:
                reasons.append(f"Critical tickets present: {int(row.get('critical_count', 0))}")
            if row.get("sla_breaches", 0) > mean * 0.3:
                reasons.append("Elevated SLA breach rate — may indicate staffing shortage")
        elif context == "workforce":
            if val < mean - 2 * std:
                reasons.append("Unusually low utilization — possible mass absence or public holiday")
            absent = row.get("absent_count", 0)
            if absent and absent > 0:
                reasons.append(f"High absence: {int(absent)} employees absent")
            ot = row.get("overtime_hours", 0)
            if ot and ot > mean * 1.5:
                reasons.append("High overtime — demand likely exceeding capacity")

        if not reasons:
            direction = "above" if val > mean else "below"
            reasons.append(f"Value {direction} historical norm by {abs(val - mean) / (std + 1e-9):.1f} standard deviations")

        return reasons

    def _build_summary(self, anomalies: list[Anomaly], metric: str) -> str:
        if not anomalies:
            return f"No anomalies detected in {metric}."
        critical = [a for a in anomalies if a.severity == "critical"]
        warnings = [a for a in anomalies if a.severity == "warning"]
        parts = [f"Detected {len(anomalies)} anomalies in {metric.replace('_', ' ')}:"]
        if critical:
            parts.append(f"{len(critical)} critical (dates: {', '.join(a.date for a in critical[:3])}{'...' if len(critical) > 3 else ''})")
        if warnings:
            parts.append(f"{len(warnings)} warnings")
        return " ".join(parts) + "."
