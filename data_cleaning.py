"""Data cleaning utilities for sales analytics."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

LOGGER = logging.getLogger(__name__)


def _looks_like_placeholder_header(column_name: str) -> bool:
    lowered = str(column_name).strip().lower()
    return lowered.startswith("unnamed") or lowered in {"nan", "none", ""}


def _header_needs_recovery(columns: pd.Index) -> bool:
    names = [str(col) for col in columns]
    if not names:
        return True
    placeholder_count = sum(1 for col in names if _looks_like_placeholder_header(col))
    return placeholder_count / len(names) >= 0.5


def _detect_header_row(raw_df: pd.DataFrame, max_scan_rows: int = 40) -> int | None:
    """Find a likely header row for exports that include report-title preamble rows."""
    search_tokens = [
        "date",
        "particular",
        "customer",
        "party",
        "gross",
        "total",
        "gst",
        "amount",
        "voucher",
        "invoice",
        "sales",
        "product",
        "item",
    ]

    best_row: int | None = None
    best_score = 0.0

    for row_idx in range(min(max_scan_rows, len(raw_df))):
        row = raw_df.iloc[row_idx]
        cells = [str(val).strip().lower() for val in row.tolist() if pd.notna(val) and str(val).strip()]

        if len(cells) < 3:
            continue

        keyword_hits = sum(1 for token in search_tokens if any(token in cell for cell in cells))
        unique_ratio = len(set(cells)) / max(len(cells), 1)
        score = (keyword_hits * 2.0) + min(len(cells), 20) * 0.1 + unique_ratio

        if score > best_score:
            best_score = score
            best_row = row_idx

    if best_row is None or best_score < 3.0:
        return None

    return best_row


def _canonicalize_column_name(name: str) -> str:
    """Convert messy column names to a clean, comparable snake_case form."""
    cleaned = re.sub(r"[\r\n\t]+", " ", str(name)).strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "unnamed_column"


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names and resolve duplicates predictably."""
    renamed_columns: dict[str, str] = {}
    seen: dict[str, int] = {}

    for original in df.columns:
        base = _canonicalize_column_name(str(original))
        count = seen.get(base, 0)
        seen[base] = count + 1
        final_name = base if count == 0 else f"{base}_{count + 1}"
        renamed_columns[str(original)] = final_name

    return df.rename(columns=renamed_columns)


def load_excel_robust(file_path: str | Path, sheet_name: int | str = 0) -> pd.DataFrame:
    """Read an Excel file with useful fallbacks and validation."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")

    try:
        df = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
    except Exception as exc:
        LOGGER.warning("Primary Excel read failed for %s: %s. Retrying default engine.", path, exc)
        df = pd.read_excel(path, sheet_name=sheet_name)

    if _header_needs_recovery(df.columns):
        LOGGER.info("Detected placeholder headers in %s. Attempting automatic header-row recovery.", path.name)
        raw_preview = pd.read_excel(path, sheet_name=sheet_name, header=None, engine="openpyxl")
        detected_header_row = _detect_header_row(raw_preview)

        if detected_header_row is not None:
            LOGGER.info("Recovered header row at index %s for %s", detected_header_row, path.name)
            df = pd.read_excel(path, sheet_name=sheet_name, header=detected_header_row, engine="openpyxl")
        else:
            LOGGER.warning(
                "Could not confidently detect a header row in %s. Proceeding with the default header.",
                path.name,
            )

    if df.empty:
        raise ValueError(f"Excel file contains no rows: {path}")

    return df


def _find_best_column(
    columns: list[str],
    include_keywords: list[str],
    preferred_keywords: Optional[list[str]] = None,
    exclude_keywords: Optional[list[str]] = None,
) -> Optional[str]:
    """Score columns by keyword matches and return the strongest candidate."""
    preferred_keywords = preferred_keywords or []
    exclude_keywords = exclude_keywords or []

    for preferred in preferred_keywords:
        exact = [col for col in columns if col == preferred]
        if exact:
            return exact[0]

    candidates: list[tuple[int, str]] = []
    for col in columns:
        if any(token in col for token in exclude_keywords):
            continue

        score = sum(1 for token in include_keywords if token in col)
        if score > 0:
            candidates.append((score, col))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
    return candidates[0][1]


def detect_date_column(df: pd.DataFrame) -> Optional[str]:
    return _find_best_column(
        columns=list(df.columns),
        include_keywords=["date", "invoice", "bill", "posting", "transaction", "doc"],
        preferred_keywords=["date", "invoice_date", "bill_date", "transaction_date"],
    )


def detect_revenue_column(df: pd.DataFrame) -> Optional[str]:
    return _find_best_column(
        columns=list(df.columns),
        include_keywords=["gross", "total", "amount", "revenue", "sale", "value"],
        preferred_keywords=["gross_total", "gross_amount", "invoice_total", "total_amount"],
        exclude_keywords=["gst", "tax", "qty", "quantity", "rate", "price", "discount"],
    )


def detect_customer_column(df: pd.DataFrame) -> Optional[str]:
    return _find_best_column(
        columns=list(df.columns),
        include_keywords=["customer", "party", "client", "buyer", "account", "name", "particular"],
        preferred_keywords=["customer_name", "customer", "party_name", "client_name", "particulars"],
        exclude_keywords=["product", "item", "material", "code", "id", "gst"],
    )


def detect_product_column(df: pd.DataFrame) -> Optional[str]:
    return _find_best_column(
        columns=list(df.columns),
        include_keywords=["product", "item", "particular", "description", "material", "name"],
        preferred_keywords=["product_name", "item_name", "name_of_item", "particulars"],
        exclude_keywords=["customer", "party", "gst", "amount", "total", "rate"],
    )


def detect_gstin_column(df: pd.DataFrame) -> Optional[str]:
    return _find_best_column(
        columns=list(df.columns),
        include_keywords=["gstin", "gst", "tax"],
        preferred_keywords=["gstin", "gst_no", "gst_number", "gstin_no"],
        exclude_keywords=["amount", "value", "total", "rate"],
    )


def _safe_to_numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    cleaned = (
        series.astype("string")
        .str.replace(",", "", regex=False)
        .str.replace(r"[^0-9.\-]", "", regex=True)
        .replace({"": pd.NA, "-": pd.NA})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def convert_numeric_columns(df: pd.DataFrame, min_convert_ratio: float = 0.80) -> pd.DataFrame:
    """Convert numeric-like object columns while preserving text columns."""
    converted = df.copy()

    for col in converted.columns:
        if pd.api.types.is_object_dtype(converted[col]) or pd.api.types.is_string_dtype(converted[col]):
            numeric_series = _safe_to_numeric(converted[col])
            ratio = numeric_series.notna().mean()
            if ratio >= min_convert_ratio:
                converted[col] = numeric_series

    return converted


def _sanitize_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].astype("string").str.strip()
    return df


def _handle_missing_values(
    df: pd.DataFrame,
    date_column: str,
    revenue_column: str,
    customer_column: Optional[str],
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Apply practical missing-value handling for analytics workflows."""
    stats: dict[str, int] = {}
    working = df.copy()

    initial_rows = len(working)
    working = working.dropna(subset=[date_column, revenue_column])
    stats["rows_dropped_missing_date_or_revenue"] = initial_rows - len(working)

    if customer_column:
        missing_customers = int(working[customer_column].isna().sum())
        stats["missing_customers_filled"] = missing_customers
        working[customer_column] = working[customer_column].fillna("Unknown Customer")

    numeric_cols = [col for col in working.columns if pd.api.types.is_numeric_dtype(working[col])]
    for col in numeric_cols:
        if working[col].isna().any():
            median_val = working[col].median(skipna=True)
            if pd.notna(median_val):
                working[col] = working[col].fillna(median_val)

    object_cols = [col for col in working.columns if pd.api.types.is_object_dtype(working[col]) or pd.api.types.is_string_dtype(working[col])]
    for col in object_cols:
        if working[col].isna().any():
            working[col] = working[col].fillna("Unknown")

    return working, stats


def add_time_features(df: pd.DataFrame, date_column: str) -> pd.DataFrame:
    enriched = df.copy()
    enriched["year"] = enriched[date_column].dt.year
    enriched["month"] = enriched[date_column].dt.month
    enriched["year_month"] = enriched[date_column].dt.to_period("M").astype(str)
    return enriched


@dataclass
class CleanedSalesData:
    dataframe: pd.DataFrame
    date_column: str
    revenue_column: str
    customer_column: Optional[str]
    gstin_column: Optional[str]
    missing_value_stats: dict[str, int]


def clean_sales_data(file_path: str | Path) -> CleanedSalesData:
    """Load and clean transaction-level sales data for downstream analytics."""
    raw_df = load_excel_robust(file_path)
    df = normalize_column_names(raw_df)
    df = _sanitize_text_columns(df)

    date_column = detect_date_column(df)
    revenue_column = detect_revenue_column(df)
    customer_column = detect_customer_column(df)
    gstin_column = detect_gstin_column(df)

    if not date_column:
        raise ValueError("Could not detect a date column in DayBook data.")
    if not revenue_column:
        raise ValueError("Could not detect a revenue column in DayBook data.")

    df[date_column] = pd.to_datetime(df[date_column], errors="coerce", dayfirst=True)

    df = convert_numeric_columns(df)
    df[revenue_column] = _safe_to_numeric(df[revenue_column])

    if df[revenue_column].notna().sum() == 0:
        raise ValueError("Detected revenue column could not be converted to numeric values.")

    cleaned_df, missing_stats = _handle_missing_values(df, date_column, revenue_column, customer_column)
    cleaned_df = add_time_features(cleaned_df, date_column)
    cleaned_df = cleaned_df.sort_values(by=date_column).reset_index(drop=True)

    return CleanedSalesData(
        dataframe=cleaned_df,
        date_column=date_column,
        revenue_column=revenue_column,
        customer_column=customer_column,
        gstin_column=gstin_column,
        missing_value_stats=missing_stats,
    )


def clean_reference_data(file_path: str | Path) -> pd.DataFrame:
    """Load and clean master/reference dataset."""
    raw_df = load_excel_robust(file_path)
    df = normalize_column_names(raw_df)
    df = _sanitize_text_columns(df)
    df = convert_numeric_columns(df)
    return df
