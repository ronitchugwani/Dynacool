"""Main entry point for production sales analytics pipeline."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from data_cleaning import CleanedSalesData, clean_reference_data, clean_sales_data
from data_integration import integrate_sales_and_master
from eda import perform_eda
from forecasting import build_monthly_revenue_series, forecast_revenue_arima


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def discover_excel_file(preferred_names: list[str], fallback_keyword: str) -> Path:
    """Find dataset files by preferred names, then by keyword search."""
    cwd = Path.cwd()

    for name in preferred_names:
        candidate = cwd / name
        if candidate.exists():
            return candidate

    matches = sorted(
        [
            path
            for path in cwd.glob("*.xlsx")
            if fallback_keyword.lower() in path.stem.lower()
        ],
        key=lambda p: p.name.lower(),
    )
    if matches:
        return matches[0]

    raise FileNotFoundError(
        f"Could not locate an Excel file for keyword '{fallback_keyword}' in {cwd}."
    )


def ensure_output_dirs() -> tuple[Path, Path]:
    plots_dir = Path("outputs") / "plots"
    results_dir = Path("outputs") / "results"
    plots_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    return plots_dir, results_dir


def to_serializable(value: Any) -> Any:
    """Convert non-JSON native values into JSON-safe values recursively."""
    if isinstance(value, dict):
        return {str(k): to_serializable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_serializable(v) for v in value]
    if isinstance(value, tuple):
        return [to_serializable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def save_results(results: dict[str, Any], result_file: Path) -> None:
    serializable = to_serializable(results)
    with result_file.open("w", encoding="utf-8") as handle:
        json.dump(serializable, handle, indent=2)


def print_key_insights(
    cleaned_sales: CleanedSalesData,
    integration_summary: dict[str, Any],
    eda_results: dict[str, Any],
    forecast_results: dict[str, Any],
) -> None:
    revenue_summary = eda_results.get("revenue_analysis", {})
    gst_summary = eda_results.get("gst_analysis", {})
    customer_summary = eda_results.get("customer_analysis", {})

    print("\n=== Key Insights ===")
    print(f"Total Revenue: {revenue_summary.get('total_revenue', 0):,.2f}")
    print(f"Average Transaction Value: {revenue_summary.get('average_transaction_value', 0):,.2f}")
    print(f"Revenue Volatility (Std Dev): {revenue_summary.get('revenue_volatility_std', 0):,.2f}")
    print(
        "Join Strategy Used: "
        f"{integration_summary.get('join_key_used')} "
        f"({integration_summary.get('join_key_daybook')} -> {integration_summary.get('join_key_master')})"
    )
    print(f"Master Match Rate: {integration_summary.get('match_rate_pct', 0.0):.2f}%")
    print(f"GST as % of Revenue: {gst_summary.get('gst_as_pct_of_revenue', 0):.2f}%")

    top_customers = customer_summary.get("top_10_customers", [])
    if top_customers:
        top_customer = top_customers[0]
        print(
            "Top Customer: "
            f"{top_customer.get('customer')} | "
            f"Revenue: {top_customer.get('revenue', 0):,.2f} | "
            f"Contribution: {top_customer.get('contribution_pct', 0):.2f}%"
        )

    forecast_items = forecast_results.get("forecast", {})
    if forecast_items:
        first_month = next(iter(forecast_items))
        print(
            "Next Forecasted Month: "
            f"{first_month} -> {forecast_items[first_month].get('forecast', 0):,.2f}"
        )

    print(f"Detected Date Column: {cleaned_sales.date_column}")
    print(f"Detected Revenue Column: {cleaned_sales.revenue_column}")
    print(f"Detected Customer Column: {cleaned_sales.customer_column}")


def run_pipeline() -> None:
    configure_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting sales analytics pipeline.")
    plots_dir, results_dir = ensure_output_dirs()

    daybook_path = discover_excel_file(["DayBook.xlsx", "DayBook (1).xlsx"], fallback_keyword="daybook")
    master_path = discover_excel_file(["Master.xlsx"], fallback_keyword="master")

    logger.info("Using DayBook file: %s", daybook_path)
    logger.info("Using Master file: %s", master_path)

    cleaned_sales = clean_sales_data(daybook_path)
    cleaned_master = clean_reference_data(master_path)

    merged_df, integration_summary = integrate_sales_and_master(cleaned_sales, cleaned_master)
    eda_results = perform_eda(merged_df, output_dir=plots_dir)

    monthly_series = build_monthly_revenue_series(
        merged_df,
        date_column=cleaned_sales.date_column,
        revenue_column=cleaned_sales.revenue_column,
    )
    forecast_results = forecast_revenue_arima(monthly_series, periods=6, output_dir=plots_dir)

    combined_results = {
        "cleaning": {
            "date_column": cleaned_sales.date_column,
            "revenue_column": cleaned_sales.revenue_column,
            "customer_column": cleaned_sales.customer_column,
            "gstin_column": cleaned_sales.gstin_column,
            "missing_value_stats": cleaned_sales.missing_value_stats,
            "records_after_cleaning": len(cleaned_sales.dataframe),
        },
        "integration": integration_summary,
        "eda": eda_results,
        "forecast": forecast_results,
    }

    save_results(combined_results, results_dir / "analysis_results.json")

    print_key_insights(cleaned_sales, integration_summary, eda_results, forecast_results)
    logger.info("Pipeline completed successfully. Results saved to %s", results_dir / "analysis_results.json")


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as exc:
        logging.getLogger(__name__).exception("Pipeline failed: %s", exc)
        raise SystemExit(1)
