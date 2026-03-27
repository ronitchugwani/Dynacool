"""Generate a realistic item-level sales dataset for analytics.

This script expects access to a cleaned sales object with a DataFrame at
`cleaned.dataframe` (as used in this project). It extracts real customer names,
generates synthetic item-level transactions, and saves them to Items.csv.
"""

from __future__ import annotations

import random
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from paths import DATA_DIR, resolve_backend_path


def _detect_customer_column(df: pd.DataFrame) -> str:
    """Detect likely customer column from the cleaned dataframe."""
    candidates = [
        "particulars",
        "customer",
        "customer_name",
        "party_name",
        "client_name",
        "name",
    ]

    lowered_map = {str(col).strip().lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate in lowered_map:
            return str(lowered_map[candidate])

    # Fallback: pick the first string-like column with enough unique names.
    for col in df.columns:
        if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
            unique_count = int(df[col].astype("string").str.strip().replace({"": pd.NA}).dropna().nunique())
            if unique_count >= 10:
                return str(col)

    raise ValueError("Could not detect a customer column in cleaned.dataframe.")


def _monthly_date_pool(start_year: int = 2023, end_year: int = 2025) -> list[pd.Timestamp]:
    """Build a date pool spread across months between start_year and end_year."""
    month_starts = pd.date_range(f"{start_year}-01-01", f"{end_year}-12-01", freq="MS")
    date_pool: list[pd.Timestamp] = []

    for month_start in month_starts:
        # Keep generated dates distributed across early/mid/late month.
        month_days = pd.date_range(month_start, month_start + pd.offsets.MonthEnd(1), freq="D")
        for day in [5, 10, 15, 20, 25]:
            if day <= len(month_days):
                date_pool.append(month_days[day - 1])

    return date_pool


def generate_item_sales_dataset(
    cleaned: Any,
    output_path: str = "data/Items.csv",
    rows: int = 300,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic item-level sales data using real customer names.

    Parameters
    ----------
    cleaned:
        Cleaned sales object that contains a DataFrame at `cleaned.dataframe`.
    output_path:
        CSV output file path.
    rows:
        Number of synthetic rows to generate.
    seed:
        Random seed for reproducible output.
    """
    if not hasattr(cleaned, "dataframe"):
        raise ValueError("Expected a cleaned object with attribute `dataframe`.")

    cleaned_df = cleaned.dataframe.copy()
    if cleaned_df.empty:
        raise ValueError("cleaned.dataframe is empty. Cannot generate item sales dataset.")

    customer_col = _detect_customer_column(cleaned_df)
    customer_series = (
        cleaned_df[customer_col]
        .astype("string")
        .str.strip()
        .replace({"": pd.NA})
        .dropna()
    )

    if customer_series.empty:
        raise ValueError("No valid customer names found in cleaned.dataframe.")

    # Use real customer frequency to create realistic non-uniform customer sampling.
    customer_counts = customer_series.value_counts()
    customers = customer_counts.index.tolist()
    customer_weights = (customer_counts.values / customer_counts.values.sum()).astype(float)

    item_catalog = [
        {"item_name": "Compressor Unit", "category": "Equipment", "unit_price": 18500},
        {"item_name": "Cooling Coil", "category": "Components", "unit_price": 7200},
        {"item_name": "Refrigerant Gas", "category": "Consumables", "unit_price": 2800},
        {"item_name": "Air Handler Unit", "category": "Equipment", "unit_price": 24500},
        {"item_name": "Temperature Sensor", "category": "Electronics", "unit_price": 1650},
        {"item_name": "Control Panel", "category": "Electronics", "unit_price": 9800},
    ]

    # Non-uniform item probabilities based on typical refrigeration demand.
    item_probs = np.array([0.18, 0.24, 0.30, 0.10, 0.08, 0.10], dtype=float)
    item_probs = item_probs / item_probs.sum()

    # Quantity distribution: skewed toward low quantities, clipped to 1..10.
    rng = np.random.default_rng(seed)
    random.seed(seed)
    date_pool = _monthly_date_pool(2023, 2025)

    records: list[dict[str, Any]] = []
    for idx in range(1, rows + 1):
        item_idx = int(rng.choice(len(item_catalog), p=item_probs))
        item = item_catalog[item_idx]

        quantity = int(np.clip(rng.poisson(lam=3.2) + 1, 1, 10))
        customer = str(rng.choice(customers, p=customer_weights))
        date = random.choice(date_pool)

        # Add light price variation by transaction to feel realistic.
        price_variation = float(rng.normal(loc=1.0, scale=0.04))
        unit_price = round(max(item["unit_price"] * price_variation, 1.0), 2)
        total_value = round(quantity * unit_price, 2)

        records.append(
            {
                "Date": pd.to_datetime(date).date().isoformat(),
                "Invoice No": f"INV{idx:03d}",
                "Customer": customer,
                "Item Name": item["item_name"],
                "Category": item["category"],
                "Quantity": quantity,
                "Unit Price": unit_price,
                "Total Value": total_value,
            }
        )

    items_df = pd.DataFrame(records)
    items_df["Date"] = pd.to_datetime(items_df["Date"])  # Keep this as datetime for analytics.
    items_df = items_df.sort_values("Date").reset_index(drop=True)

    output_file = resolve_backend_path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    items_df.to_csv(output_file, index=False)

    print("Generated item-level dataset preview:")
    print(items_df.head())
    print(f"\nTotal rows: {len(items_df)}")
    print(f"Saved file: {output_file}")

    return items_df


def main() -> None:
    """Example runnable entrypoint for this repository."""
    try:
        # Project-specific loader to produce `cleaned` object with `.dataframe`.
        from data_cleaning import clean_sales_data

        cleaned = clean_sales_data(DATA_DIR / "DayBook (1).xlsx")
        generate_item_sales_dataset(cleaned=cleaned, output_path=str(DATA_DIR / "Items.csv"), rows=300, seed=42)
    except Exception as exc:
        print("Failed to generate item-level dataset.")
        print(f"Reason: {exc}")
        print(
            "Tip: If you already have `cleaned` in your environment, call\n"
            "generate_item_sales_dataset(cleaned, output_path='Items.csv')."
        )


if __name__ == "__main__":
    main()
