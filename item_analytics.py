"""Optional item-level analytics used for product and category storytelling."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

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


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {col: str(col).strip().lower().replace(" ", "_") for col in df.columns}
    return df.rename(columns=renamed)


def load_item_sales_data(file_path: str | Path) -> pd.DataFrame:
    """Load the supplementary item-level dataset used for category drilldowns."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Items dataset not found: {path}")

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Items dataset is empty: {path}")

    df = _normalize_columns(df)

    required_columns = ["date", "customer", "item_name", "category", "quantity", "unit_price", "total_value"]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Items dataset is missing required columns: {missing}")

    # Keep the item dataset analysis self-contained and chart-ready.
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["total_value"] = pd.to_numeric(df["total_value"], errors="coerce")
    df["customer"] = df["customer"].astype("string").str.strip().fillna("Unknown Customer")
    df["item_name"] = df["item_name"].astype("string").str.strip().fillna("Unknown Item")
    df["category"] = df["category"].astype("string").str.strip().fillna("Uncategorized")
    df = df.dropna(subset=["date", "total_value"])

    if df.empty:
        raise ValueError("Items dataset contains no valid rows after preprocessing.")

    return df


def analyze_item_sales(
    file_path: str | Path = "Items.csv",
    output_dir: str | Path = "outputs/plots",
) -> dict[str, Any]:
    """Create product-mix summaries and visualizations from item-level sales data."""
    plot_dir = _ensure_output_dir(output_dir)
    items = load_item_sales_data(file_path)

    # Item-level charts complement invoice analytics with a clearer merchandising and category lens.
    items["_month_start"] = items["date"].dt.to_period("M").dt.to_timestamp()

    total_item_value = items["total_value"].sum()
    average_order_value = items["total_value"].mean()
    monthly_value = items.groupby("_month_start", dropna=False)["total_value"].sum().sort_index()
    category_revenue = items.groupby("category", dropna=False)["total_value"].sum().sort_values(ascending=False)
    top_items = items.groupby("item_name", dropna=False)["total_value"].sum().sort_values(ascending=False).head(10)

    top_3_item_share_pct = (
        (top_items.head(3).sum() / total_item_value) * 100 if total_item_value else 0.0
    )

    plot_files: list[str] = []

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(monthly_value.index, monthly_value.values, marker="o", linewidth=2, color="#2a9d8f")
    ax.set_title("Item-Level Sales Trend")
    ax.set_xlabel("Month")
    ax.set_ylabel("Sales Value")
    ax.grid(alpha=0.25)
    fig.autofmt_xdate()
    plot_files.append(_save_figure(fig, plot_dir / "item_sales_trend.png"))

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(category_revenue.index.astype(str), category_revenue.values, color="#e76f51")
    ax.set_title("Revenue by Product Category")
    ax.set_xlabel("Category")
    ax.set_ylabel("Sales Value")
    ax.grid(axis="y", alpha=0.25)
    plot_files.append(_save_figure(fig, plot_dir / "category_revenue.png"))

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(top_items.index.astype(str), top_items.values, color="#457b9d")
    ax.set_title("Top Items by Sales Value")
    ax.set_xlabel("Item")
    ax.set_ylabel("Sales Value")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.25)
    plot_files.append(_save_figure(fig, plot_dir / "top_items_by_value.png"))

    results: dict[str, Any] = {
        "rows": int(len(items)),
        "date_range": {
            "start": items["date"].min().date().isoformat(),
            "end": items["date"].max().date().isoformat(),
        },
        "total_item_value": _safe_float(total_item_value),
        "average_order_value": _safe_float(average_order_value),
        "category_mix": [
            {
                "category": str(name),
                "revenue": _safe_float(value),
                "contribution_pct": _safe_float((value / total_item_value) * 100) if total_item_value else 0.0,
            }
            for name, value in category_revenue.items()
        ],
        "top_items": [
            {
                "item": str(name),
                "revenue": _safe_float(value),
                "contribution_pct": _safe_float((value / total_item_value) * 100) if total_item_value else 0.0,
            }
            for name, value in top_items.items()
        ],
        "top_3_item_share_pct": _safe_float(top_3_item_share_pct),
        "artifacts": {
            "plot_files": plot_files,
        },
    }

    LOGGER.info("Item analytics complete. Plots saved to %s", plot_dir)
    return results
