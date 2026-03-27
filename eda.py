"""Exploratory data analysis module for invoice-level sales analytics."""

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


def _save_figure(fig: plt.Figure, output_path: Path) -> str:
    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    return str(output_path)


def _detect_net_sales_column(df: pd.DataFrame, revenue_column: str) -> str | None:
    """Find the best non-tax sales amount column for gross-vs-net comparisons."""
    candidates = [
        "sales",
        "net_sales",
        "taxable_value",
        "basic_amount",
        "taxable_amount",
    ]

    for candidate in candidates:
        if candidate in df.columns and candidate != revenue_column:
            return candidate

    return None


def _top_share(series: pd.Series, total_value: float, limit: int) -> float:
    if total_value == 0 or series.empty:
        return 0.0
    return _safe_float(series.head(limit).sum() / total_value * 100)


def perform_eda(df: pd.DataFrame, output_dir: str | Path = "outputs/plots") -> dict[str, Any]:
    """Run business-oriented EDA and save portfolio-ready plots."""
    plot_dir = _ensure_output_dir(output_dir)

    date_column = detect_date_column(df)
    revenue_column = detect_revenue_column(df)
    customer_column = detect_customer_column(df)

    if not date_column or not revenue_column:
        raise ValueError("EDA requires detectable date and revenue columns.")

    working = df.copy()

    # Normalize the two fields the rest of the analysis depends on.
    working[date_column] = pd.to_datetime(working[date_column], errors="coerce", dayfirst=True)
    working[revenue_column] = pd.to_numeric(working[revenue_column], errors="coerce")
    working = working.dropna(subset=[date_column, revenue_column])

    if working.empty:
        raise ValueError("No valid rows available after EDA preprocessing.")

    net_sales_column = _detect_net_sales_column(working, revenue_column)
    if net_sales_column:
        working[net_sales_column] = pd.to_numeric(working[net_sales_column], errors="coerce")

    # Build the reusable time dimensions once so every chart uses the same calendar grain.
    working["_year"] = working[date_column].dt.year
    working["_month_start"] = working[date_column].dt.to_period("M").dt.to_timestamp()

    month_order = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    working["_month_name"] = pd.Categorical(
        working[date_column].dt.month_name(),
        categories=month_order,
        ordered=True,
    )

    total_revenue = working[revenue_column].sum()
    average_txn_value = working[revenue_column].mean()
    median_txn_value = working[revenue_column].median()
    revenue_volatility = working[revenue_column].std(ddof=1)
    unique_customers = (
        int(
            working[customer_column]
            .astype("string")
            .str.strip()
            .replace({"": pd.NA})
            .dropna()
            .nunique()
        )
        if customer_column
        else 0
    )

    year_wise_revenue = working.groupby("_year", dropna=False)[revenue_column].sum().sort_index()
    monthly_revenue = working.groupby("_month_start", dropna=False)[revenue_column].sum().sort_index()
    moving_avg_3m = monthly_revenue.rolling(window=3, min_periods=1).mean()
    month_of_year_revenue = (
        working.groupby("_month_name", observed=False)[revenue_column]
        .sum()
        .sort_values(ascending=False)
    )

    yearly_growth_pct: dict[str, float] = {}
    previous_year_revenue: float | None = None
    for year, value in year_wise_revenue.items():
        current_value = _safe_float(value)
        if previous_year_revenue not in (None, 0.0):
            yearly_growth_pct[str(year)] = _safe_float(((current_value - previous_year_revenue) / previous_year_revenue) * 100)
        previous_year_revenue = current_value

    peak_month_idx = monthly_revenue.idxmax()
    weakest_month_idx = monthly_revenue.idxmin()

    plot_files: list[str] = []

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(monthly_revenue.index, monthly_revenue.values, marker="o", linewidth=2, label="Monthly Revenue")
    ax.plot(moving_avg_3m.index, moving_avg_3m.values, linestyle="--", linewidth=2, label="3-Month Moving Avg")
    ax.set_title("Monthly Revenue Trend")
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue")
    ax.legend()
    ax.grid(alpha=0.25)
    fig.autofmt_xdate()
    plot_files.append(_save_figure(fig, plot_dir / "monthly_revenue_trend.png"))

    fig, ax = plt.subplots(figsize=(10, 5))
    year_positions = list(range(len(year_wise_revenue.index)))
    ax.bar(year_positions, year_wise_revenue.values, color="#1f77b4")
    ax.set_title("Year-wise Revenue")
    ax.set_xlabel("Year")
    ax.set_ylabel("Revenue")
    ax.set_xticks(year_positions)
    ax.set_xticklabels(year_wise_revenue.index.astype(str))
    ax.grid(axis="y", alpha=0.25)
    plot_files.append(_save_figure(fig, plot_dir / "year_wise_revenue.png"))

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(month_of_year_revenue.index.astype(str), month_of_year_revenue.values, color="#2a9d8f")
    ax.set_title("Seasonality by Calendar Month")
    ax.set_xlabel("Month")
    ax.set_ylabel("Cumulative Revenue")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.25)
    plot_files.append(_save_figure(fig, plot_dir / "monthly_seasonality.png"))

    top_customers: list[dict[str, Any]] = []
    pareto_cutoff_count = 0
    top_10_share_pct = 0.0
    top_20_share_pct = 0.0

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

        top_10_share_pct = _top_share(customer_revenue, _safe_float(total_revenue), limit=10)
        top_20_share_pct = _top_share(customer_revenue, _safe_float(total_revenue), limit=20)

        top10 = customer_revenue.head(10)
        top10_contrib = contribution_pct.loc[top10.index]
        top15 = customer_revenue.head(15)

        top_customers = [
            {
                "customer": str(cust),
                "revenue": _safe_float(top10.loc[cust]),
                "contribution_pct": _safe_float(top10_contrib.loc[cust]),
            }
            for cust in top10.index
        ]

        fig, ax = plt.subplots(figsize=(12, 6))
        top15_positions = list(range(len(top15.index)))
        ax.bar(top15_positions, top15.values, color="#457b9d")
        ax.set_title("Top Customers by Revenue")
        ax.set_xlabel("Customer")
        ax.set_ylabel("Revenue")
        ax.set_xticks(top15_positions)
        ax.set_xticklabels(top15.index.astype(str), rotation=75)
        ax.grid(axis="y", alpha=0.25)
        plot_files.append(_save_figure(fig, plot_dir / "top_customers_revenue.png"))

        fig, ax1 = plt.subplots(figsize=(12, 6))
        pareto_names = customer_revenue.head(20).index.astype(str)
        pareto_positions = list(range(len(pareto_names)))
        ax1.bar(pareto_positions, customer_revenue.head(20).values, color="#264653")
        ax1.set_title("Customer Revenue and Pareto")
        ax1.set_xlabel("Customer")
        ax1.set_ylabel("Revenue")
        ax1.set_xticks(pareto_positions)
        ax1.set_xticklabels(pareto_names, rotation=75)
        ax1.grid(axis="y", alpha=0.25)

        ax2 = ax1.twinx()
        ax2.plot(
            pareto_positions,
            cumulative_pct.head(20).values,
            color="#e76f51",
            marker="o",
            linewidth=2,
            label="Cumulative %",
        )
        ax2.set_ylabel("Cumulative Contribution %")
        ax2.set_ylim(0, 110)

        plot_files.append(_save_figure(fig, plot_dir / "customer_pareto.png"))

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(working[revenue_column], bins=30, edgecolor="black", alpha=0.75, color="#f4a261")
    ax.set_title("Revenue Distribution")
    ax.set_xlabel("Revenue")
    ax.set_ylabel("Frequency")
    ax.grid(axis="y", alpha=0.2)
    plot_files.append(_save_figure(fig, plot_dir / "revenue_histogram.png"))

    net_sales_total = None
    invoice_tax_component_total = None
    invoice_tax_component_pct = None

    if net_sales_column:
        comparable_sales = working.dropna(subset=[net_sales_column]).copy()
        if not comparable_sales.empty:
            net_sales_total = comparable_sales[net_sales_column].sum()
            invoice_tax_component_total = (comparable_sales[revenue_column] - comparable_sales[net_sales_column]).sum()
            if comparable_sales[revenue_column].sum() != 0:
                invoice_tax_component_pct = (invoice_tax_component_total / comparable_sales[revenue_column].sum()) * 100

            yearly_compare = (
                comparable_sales.groupby("_year", dropna=False)[[revenue_column, net_sales_column]]
                .sum()
                .sort_index()
            )

            fig, ax = plt.subplots(figsize=(10, 5))
            x_positions = range(len(yearly_compare.index))
            ax.bar(
                [x - 0.2 for x in x_positions],
                yearly_compare[revenue_column].values,
                width=0.4,
                label="Gross Invoice Value",
                color="#1d3557",
            )
            ax.bar(
                [x + 0.2 for x in x_positions],
                yearly_compare[net_sales_column].values,
                width=0.4,
                label="Net Sales",
                color="#a8dadc",
            )
            ax.set_title("Gross Invoice Value vs Net Sales")
            ax.set_xlabel("Year")
            ax.set_ylabel("Value")
            ax.set_xticks(list(x_positions))
            ax.set_xticklabels(yearly_compare.index.astype(str))
            ax.legend()
            ax.grid(axis="y", alpha=0.25)
            plot_files.append(_save_figure(fig, plot_dir / "gross_vs_net_sales.png"))

    q1 = working[revenue_column].quantile(0.25)
    q3 = working[revenue_column].quantile(0.75)
    revenue_skewness = working[revenue_column].skew()
    high_value_order_pct = (working[revenue_column] >= 200000).mean() * 100

    results: dict[str, Any] = {
        "revenue_analysis": {
            "total_revenue": _safe_float(total_revenue),
            "average_transaction_value": _safe_float(average_txn_value),
            "median_transaction_value": _safe_float(median_txn_value),
            "revenue_volatility_std": _safe_float(revenue_volatility),
            "net_sales_total": _safe_float(net_sales_total) if net_sales_total is not None else None,
        },
        "time_series_analysis": {
            "year_wise_revenue": {str(year): _safe_float(val) for year, val in year_wise_revenue.items()},
            "monthly_revenue_trend": {
                idx.strftime("%Y-%m"): _safe_float(val) for idx, val in monthly_revenue.items()
            },
            "moving_average_3m": {
                idx.strftime("%Y-%m"): _safe_float(val) for idx, val in moving_avg_3m.items()
            },
            "month_of_year_revenue": {
                str(idx): _safe_float(val) for idx, val in month_of_year_revenue.items()
            },
            "yearly_growth_pct": yearly_growth_pct,
            "peak_month": {
                "month": peak_month_idx.strftime("%Y-%m"),
                "revenue": _safe_float(monthly_revenue.loc[peak_month_idx]),
            },
            "weakest_month": {
                "month": weakest_month_idx.strftime("%Y-%m"),
                "revenue": _safe_float(monthly_revenue.loc[weakest_month_idx]),
            },
        },
        "customer_analysis": {
            "unique_customers": unique_customers,
            "top_10_customers": top_customers,
            "top_10_contribution_pct": _safe_float(top_10_share_pct),
            "top_20_contribution_pct": _safe_float(top_20_share_pct),
            "pareto_customer_count_for_80pct": pareto_cutoff_count,
        },
        "tax_analysis": {
            "net_sales_column": net_sales_column,
            "invoice_tax_component_total": _safe_float(invoice_tax_component_total)
            if invoice_tax_component_total is not None
            else None,
            "invoice_tax_component_pct_of_gross": _safe_float(invoice_tax_component_pct)
            if invoice_tax_component_pct is not None
            else None,
        },
        "distribution_analysis": {
            "revenue_skewness": _safe_float(revenue_skewness),
            "q1_transaction_value": _safe_float(q1),
            "q3_transaction_value": _safe_float(q3),
            "high_value_orders_pct_over_200k": _safe_float(high_value_order_pct),
        },
        "artifacts": {
            "plot_files": plot_files,
        },
    }

    LOGGER.info("EDA complete. Plots saved to %s", plot_dir)
    return results
