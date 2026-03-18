"""Exploratory data analysis module for sales analytics."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from data_cleaning import detect_customer_column, detect_date_column, detect_revenue_column

LOGGER = logging.getLogger(__name__)


def _ensure_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return float("nan")


def _detect_gst_columns(df: pd.DataFrame) -> list[str]:
    candidates = []
    for col in df.columns:
        if any(token in col for token in ["gst", "cgst", "sgst", "igst", "tax"]):
            if not any(exclude in col for exclude in ["rate", "percentage", "percent"]):
                candidates.append(col)
    return list(dict.fromkeys(candidates))


def perform_eda(df: pd.DataFrame, output_dir: str | Path = "outputs/plots") -> dict[str, Any]:
    """Run required EDA analyses and save all plots."""
    plot_dir = _ensure_output_dir(output_dir)

    date_column = detect_date_column(df)
    revenue_column = detect_revenue_column(df)
    customer_column = detect_customer_column(df)

    if not date_column or not revenue_column:
        raise ValueError("EDA requires detectable date and revenue columns.")

    working = df.copy()
    working[date_column] = pd.to_datetime(working[date_column], errors="coerce", dayfirst=True)
    working[revenue_column] = pd.to_numeric(working[revenue_column], errors="coerce")
    working = working.dropna(subset=[date_column, revenue_column])

    if working.empty:
        raise ValueError("No valid rows available after EDA preprocessing.")

    total_revenue = working[revenue_column].sum()
    average_txn_value = working[revenue_column].mean()
    revenue_volatility = working[revenue_column].std(ddof=1)

    working["_year"] = working[date_column].dt.year
    working["_month_start"] = working[date_column].dt.to_period("M").dt.to_timestamp()

    year_wise_revenue = working.groupby("_year", dropna=False)[revenue_column].sum().sort_index()
    monthly_revenue = working.groupby("_month_start", dropna=False)[revenue_column].sum().sort_index()
    moving_avg_3m = monthly_revenue.rolling(window=3, min_periods=1).mean()

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(monthly_revenue.index, monthly_revenue.values, marker="o", linewidth=2, label="Monthly Revenue")
    ax.plot(moving_avg_3m.index, moving_avg_3m.values, linestyle="--", linewidth=2, label="3-Month Moving Avg")
    ax.set_title("Monthly Revenue Trend")
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue")
    ax.legend()
    ax.grid(alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(plot_dir / "monthly_revenue_trend.png", dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(year_wise_revenue.index.astype(str), year_wise_revenue.values)
    ax.set_title("Year-wise Revenue")
    ax.set_xlabel("Year")
    ax.set_ylabel("Revenue")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(plot_dir / "year_wise_revenue.png", dpi=300)
    plt.close(fig)

    top_customers: list[dict[str, Any]] = []
    pareto_cutoff_count = 0

    if customer_column:
        customer_revenue = (
            working.groupby(customer_column, dropna=False)[revenue_column]
            .sum()
            .sort_values(ascending=False)
        )
        contribution_pct = (customer_revenue / total_revenue * 100) if total_revenue else customer_revenue * 0
        cumulative_pct = contribution_pct.cumsum()
        pareto_cutoff_count = int((cumulative_pct <= 80).sum())
        if pareto_cutoff_count == 0 and len(cumulative_pct) > 0:
            pareto_cutoff_count = 1

        top10 = customer_revenue.head(10)
        top10_contrib = contribution_pct.loc[top10.index]

        top_customers = [
            {
                "customer": str(cust),
                "revenue": _safe_float(top10.loc[cust]),
                "contribution_pct": _safe_float(top10_contrib.loc[cust]),
            }
            for cust in top10.index
        ]

        fig, ax1 = plt.subplots(figsize=(12, 6))
        ax1.bar(customer_revenue.head(20).index.astype(str), customer_revenue.head(20).values)
        ax1.set_title("Customer Revenue and Pareto")
        ax1.set_xlabel("Customer")
        ax1.set_ylabel("Revenue")
        ax1.tick_params(axis="x", rotation=75)
        ax1.grid(axis="y", alpha=0.25)

        ax2 = ax1.twinx()
        ax2.plot(
            cumulative_pct.head(20).index.astype(str),
            cumulative_pct.head(20).values,
            color="darkred",
            marker="o",
            linewidth=2,
            label="Cumulative %",
        )
        ax2.set_ylabel("Cumulative Contribution %")
        ax2.set_ylim(0, 110)

        fig.tight_layout()
        fig.savefig(plot_dir / "customer_pareto.png", dpi=300)
        plt.close(fig)

    gst_columns = _detect_gst_columns(working)
    gst_breakdown: dict[str, float] = {}

    for col in gst_columns:
        working[col] = pd.to_numeric(working[col], errors="coerce")
        gst_breakdown[col] = _safe_float(working[col].sum(skipna=True))

    total_gst_collected = sum(gst_breakdown.values())
    gst_pct_of_revenue = (total_gst_collected / total_revenue * 100) if total_revenue else 0.0

    if gst_breakdown:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(gst_breakdown.keys(), gst_breakdown.values())
        ax.set_title("GST Breakdown")
        ax.set_xlabel("GST Component")
        ax.set_ylabel("Amount")
        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()
        fig.savefig(plot_dir / "gst_breakdown.png", dpi=300)
        plt.close(fig)

    revenue_skewness = working[revenue_column].skew()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(working[revenue_column], bins=30, edgecolor="black", alpha=0.75)
    ax.set_title("Revenue Distribution")
    ax.set_xlabel("Revenue")
    ax.set_ylabel("Frequency")
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(plot_dir / "revenue_histogram.png", dpi=300)
    plt.close(fig)

    results: dict[str, Any] = {
        "revenue_analysis": {
            "total_revenue": _safe_float(total_revenue),
            "average_transaction_value": _safe_float(average_txn_value),
            "revenue_volatility_std": _safe_float(revenue_volatility),
        },
        "time_series_analysis": {
            "year_wise_revenue": {str(year): _safe_float(val) for year, val in year_wise_revenue.items()},
            "monthly_revenue_trend": {
                idx.strftime("%Y-%m"): _safe_float(val) for idx, val in monthly_revenue.items()
            },
            "moving_average_3m": {
                idx.strftime("%Y-%m"): _safe_float(val) for idx, val in moving_avg_3m.items()
            },
        },
        "customer_analysis": {
            "top_10_customers": top_customers,
            "pareto_customer_count_for_80pct": pareto_cutoff_count,
        },
        "gst_analysis": {
            "total_gst_collected": _safe_float(total_gst_collected),
            "gst_breakdown": gst_breakdown,
            "gst_as_pct_of_revenue": _safe_float(gst_pct_of_revenue),
        },
        "distribution_analysis": {
            "revenue_skewness": _safe_float(revenue_skewness),
        },
    }

    LOGGER.info("EDA complete. Plots saved to %s", plot_dir)
    return results
