"""Interactive Streamlit dashboard for sales analytics."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from data_cleaning import (
    clean_reference_data,
    clean_sales_data,
    detect_customer_column,
    detect_date_column,
    detect_revenue_column,
)
from data_integration import integrate_sales_and_master
from paths import BACKEND_DIR, resolve_backend_path


def discover_excel_file(preferred_names: list[str], fallback_keyword: str) -> Path:
    """Find dataset files by preferred names, then by keyword search."""
    cwd = BACKEND_DIR

    for name in preferred_names:
        candidate = resolve_backend_path(name)
        if candidate.exists():
            return candidate

    matches = sorted(
        [
            path
            for path in (BACKEND_DIR / "data").glob("*.xlsx")
            if fallback_keyword.lower() in path.stem.lower()
        ],
        key=lambda p: p.name.lower(),
    )
    if matches:
        return matches[0]

    raise FileNotFoundError(
        f"Could not locate an Excel file for keyword '{fallback_keyword}' in {cwd}."
    )


@st.cache_data(show_spinner=True)
def load_processed_data() -> tuple[pd.DataFrame, dict[str, object], str, str, str | None]:
    """Load backend-processed merged data via cleaning and integration modules."""
    daybook_path = discover_excel_file(["DayBook.xlsx", "DayBook (1).xlsx"], fallback_keyword="daybook")
    master_path = discover_excel_file(["Master.xlsx"], fallback_keyword="master")

    cleaned_sales = clean_sales_data(daybook_path)
    cleaned_master = clean_reference_data(master_path)
    merged_df, integration_summary = integrate_sales_and_master(cleaned_sales, cleaned_master)

    date_col = detect_date_column(merged_df)
    revenue_col = detect_revenue_column(merged_df)
    customer_col = detect_customer_column(merged_df)

    if not date_col or not revenue_col:
        raise ValueError("Merged data does not contain detectable date and revenue columns.")

    return merged_df, integration_summary, date_col, revenue_col, customer_col


def _prepare_filtered_data(
    merged_df: pd.DataFrame,
    date_col: str,
    customer_col: str | None,
    selected_years: list[int],
    selected_customers: list[str],
) -> pd.DataFrame:
    """Apply sidebar filters to the merged dataset."""
    filtered = merged_df.copy()
    filtered[date_col] = pd.to_datetime(filtered[date_col], errors="coerce", dayfirst=True)
    filtered = filtered.dropna(subset=[date_col])
    filtered["_year"] = filtered[date_col].dt.year

    if selected_years:
        filtered = filtered[filtered["_year"].isin(selected_years)]

    if customer_col and selected_customers:
        filtered = filtered[filtered[customer_col].astype("string").isin(selected_customers)]

    return filtered


def _gst_breakdown(df: pd.DataFrame) -> pd.Series:
    """Compute GST component totals for pie chart."""
    gst_columns = [
        col
        for col in df.columns
        if "gst" in str(col).lower() and "rate" not in str(col).lower() and "percent" not in str(col).lower()
    ]

    if not gst_columns:
        return pd.Series(dtype=float)

    sums: dict[str, float] = {}
    for col in gst_columns:
        values = pd.to_numeric(df[col], errors="coerce")
        total = float(values.sum(skipna=True))
        if total > 0:
            sums[col] = total

    return pd.Series(sums, dtype=float).sort_values(ascending=False)


def main() -> None:
    st.set_page_config(page_title="Sales Analytics Dashboard", layout="wide")
    st.title("Sales Analytics Dashboard")
    st.caption("Interactive dashboard powered by backend cleaned and merged datasets")

    try:
        merged_df, integration_summary, date_col, revenue_col, customer_col = load_processed_data()
    except Exception as exc:
        st.error(f"Failed to load backend-processed data: {exc}")
        st.stop()

    st.sidebar.header("Filters")

    working = merged_df.copy()
    working[date_col] = pd.to_datetime(working[date_col], errors="coerce", dayfirst=True)
    working = working.dropna(subset=[date_col])
    working["_year"] = working[date_col].dt.year

    year_options = sorted([int(y) for y in working["_year"].dropna().unique().tolist()])
    selected_years = st.sidebar.multiselect("Year", options=year_options, default=year_options)

    selected_customers: list[str] = []
    if customer_col:
        customer_options = sorted(
            [
                str(c)
                for c in working[customer_col].dropna().astype("string").unique().tolist()
                if str(c).strip()
            ]
        )
        selected_customers = st.sidebar.multiselect(
            "Customer",
            options=customer_options,
            default=[],
            help="Leave empty to include all customers.",
        )
    else:
        st.sidebar.info("Customer filter not available: customer column not detected.")

    filtered = _prepare_filtered_data(
        merged_df=merged_df,
        date_col=date_col,
        customer_col=customer_col,
        selected_years=selected_years,
        selected_customers=selected_customers,
    )

    filtered[revenue_col] = pd.to_numeric(filtered[revenue_col], errors="coerce")
    filtered = filtered.dropna(subset=[revenue_col])

    if filtered.empty:
        st.warning("No records available for selected filters.")
        st.stop()

    total_revenue = float(filtered[revenue_col].sum())
    total_transactions = int(len(filtered))
    avg_transaction = float(filtered[revenue_col].mean())

    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    kpi_col1.metric("Total Revenue", f"{total_revenue:,.2f}")
    kpi_col2.metric("Total Transactions", f"{total_transactions:,}")
    kpi_col3.metric("Average Transaction Value", f"{avg_transaction:,.2f}")

    st.subheader("Data Integration Summary")
    st.write(integration_summary)

    st.subheader("Monthly Revenue Trend")
    monthly = (
        filtered.set_index(date_col)[revenue_col]
        .resample("MS")
        .sum()
        .reset_index(name="monthly_revenue")
    )
    monthly["year_month"] = monthly[date_col].dt.strftime("%Y-%m")
    line_fig = px.line(
        monthly,
        x="year_month",
        y="monthly_revenue",
        markers=True,
        labels={"year_month": "Month", "monthly_revenue": "Revenue"},
    )
    st.plotly_chart(line_fig, use_container_width=True)

    st.subheader("Top 10 Customers")
    if customer_col:
        top_customers = (
            filtered.groupby(customer_col, dropna=False)[revenue_col]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index(name="revenue")
        )
        bar_fig = px.bar(
            top_customers,
            x=customer_col,
            y="revenue",
            labels={customer_col: "Customer", "revenue": "Revenue"},
        )
        st.plotly_chart(bar_fig, use_container_width=True)
    else:
        st.info("Top customer chart unavailable: customer column not detected.")

    st.subheader("GST Breakdown")
    gst_series = _gst_breakdown(filtered)
    if not gst_series.empty:
        pie_df = gst_series.reset_index()
        pie_df.columns = ["gst_component", "amount"]
        pie_fig = px.pie(pie_df, names="gst_component", values="amount")
        st.plotly_chart(pie_fig, use_container_width=True)
    else:
        st.info("GST breakdown unavailable: no GST amount columns detected.")

    st.subheader("Revenue Distribution")
    hist_fig = px.histogram(filtered, x=revenue_col, nbins=30, labels={revenue_col: "Revenue"})
    st.plotly_chart(hist_fig, use_container_width=True)


if __name__ == "__main__":
    main()
