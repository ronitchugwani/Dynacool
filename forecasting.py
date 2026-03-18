"""Forecasting module for monthly revenue projections."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

from data_cleaning import detect_date_column, detect_revenue_column

LOGGER = logging.getLogger(__name__)


def build_monthly_revenue_series(
    df: pd.DataFrame,
    date_column: str | None = None,
    revenue_column: str | None = None,
) -> pd.Series:
    """Create a monthly revenue time series for forecasting."""
    date_col = date_column or detect_date_column(df)
    revenue_col = revenue_column or detect_revenue_column(df)

    if not date_col or not revenue_col:
        raise ValueError("Monthly series generation requires date and revenue columns.")

    working = df.copy()
    working[date_col] = pd.to_datetime(working[date_col], errors="coerce", dayfirst=True)
    working[revenue_col] = pd.to_numeric(working[revenue_col], errors="coerce")
    working = working.dropna(subset=[date_col, revenue_col])

    monthly = (
        working.set_index(date_col)[revenue_col]
        .resample("MS")
        .sum()
        .sort_index()
    )

    if monthly.empty:
        raise ValueError("Monthly revenue series is empty after preprocessing.")

    return monthly


def forecast_revenue_arima(
    monthly_revenue: pd.Series,
    periods: int = 6,
    output_dir: str | Path = "outputs/plots",
) -> dict[str, Any]:
    """Forecast next months of revenue using ARIMA and save a forecast plot."""
    if len(monthly_revenue) < 6:
        raise ValueError("ARIMA forecasting needs at least 6 monthly observations.")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    model = ARIMA(monthly_revenue.astype(float), order=(1, 1, 1))
    fitted = model.fit()

    forecast_result = fitted.get_forecast(steps=periods)
    forecast_mean = forecast_result.predicted_mean
    confidence = forecast_result.conf_int(alpha=0.05)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(monthly_revenue.index, monthly_revenue.values, label="Actual", linewidth=2)
    ax.plot(forecast_mean.index, forecast_mean.values, label=f"Forecast ({periods} months)", linewidth=2)

    ax.fill_between(
        forecast_mean.index,
        confidence.iloc[:, 0],
        confidence.iloc[:, 1],
        color="gray",
        alpha=0.2,
        label="95% Confidence Interval",
    )

    ax.set_title("Monthly Revenue Forecast (ARIMA)")
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue")
    ax.legend()
    ax.grid(alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path / "revenue_forecast_arima.png", dpi=300)
    plt.close(fig)

    forecast_payload = {
        idx.strftime("%Y-%m"): {
            "forecast": float(forecast_mean.loc[idx]),
            "lower_95": float(confidence.iloc[pos, 0]),
            "upper_95": float(confidence.iloc[pos, 1]),
        }
        for pos, idx in enumerate(forecast_mean.index)
    }

    LOGGER.info("Forecasting complete. Plot saved to %s", output_path / "revenue_forecast_arima.png")

    return {
        "model": "ARIMA(1,1,1)",
        "forecast_horizon_months": periods,
        "forecast": forecast_payload,
    }
