"""Data integration utilities for sales and reference data."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from data_cleaning import CleanedSalesData, detect_customer_column, detect_gstin_column

LOGGER = logging.getLogger(__name__)


def standardize_text(series: pd.Series) -> pd.Series:
    """Standardize text values for key matching while preserving missing values."""
    return (
        series.astype("string")
        .str.lower()
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .replace({"": pd.NA, "nan": pd.NA, "none": pd.NA})
    )


def _normalize_join_values(series: pd.Series) -> pd.Series:
    """Normalize join keys for robust string matching."""
    return standardize_text(series)


def _select_join_keys(daybook_df: pd.DataFrame, master_df: pd.DataFrame) -> tuple[str, str, str]:
    """Select the best available join key: GSTIN first, customer next."""
    daybook_gstin = detect_gstin_column(daybook_df)
    master_gstin = detect_gstin_column(master_df)

    if daybook_gstin and master_gstin:
        return daybook_gstin, master_gstin, "gstin"

    daybook_customer = detect_customer_column(daybook_df)
    master_customer = detect_customer_column(master_df)

    if daybook_customer and master_customer:
        return daybook_customer, master_customer, "customer"

    raise ValueError("No suitable join keys found. Expected GSTIN or customer name columns in both datasets.")


def _build_skipped_integration_summary(
    daybook_df: pd.DataFrame,
    master_df: pd.DataFrame,
) -> dict[str, Any]:
    """Describe why a merge was skipped when the reference sheet is not customer keyed."""
    return {
        "integration_status": "skipped",
        "join_key_used": None,
        "join_key_daybook": None,
        "join_key_master": None,
        "total_rows": int(len(daybook_df)),
        "matched_rows": None,
        "unmatched_rows": None,
        "match_rate_pct": None,
        "unmatched_rate_pct": None,
        "master_duplicate_rows_removed": 0,
        "daybook_rows_missing_join_key": 0,
        "reference_rows": int(len(master_df)),
        "reference_columns": [str(col) for col in master_df.columns],
        "reason": (
            "Reference workbook does not expose GSTIN or customer columns that align with the DayBook data. "
            "It is treated as a catalog-style reference sheet, so sales analytics continue without a direct merge."
        ),
    }


def _deduplicate_master(master_df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Resolve duplicate master keys by retaining first occurrence per normalized key."""
    before = len(master_df)
    deduped = master_df.dropna(subset=["_join_key"]).drop_duplicates(subset=["_join_key"], keep="first")
    duplicates_removed = before - len(deduped)
    return deduped, duplicates_removed


def integrate_data(cleaned_data: CleanedSalesData, master_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Compatibility API for integrating cleaned sales data with master data."""
    if not isinstance(cleaned_data, CleanedSalesData):
        raise TypeError("cleaned_data must be a CleanedSalesData instance.")
    if not isinstance(master_df, pd.DataFrame):
        raise TypeError("master_df must be a pandas DataFrame.")

    df = cleaned_data.dataframe.copy()
    master = master_df.copy()

    daybook_gstin = cleaned_data.gstin_column
    master_gstin = detect_gstin_column(master)

    if daybook_gstin and master_gstin:
        df["join_key"] = standardize_text(df[daybook_gstin])
        master["join_key"] = standardize_text(master[master_gstin])
        key_used = "GSTIN"
        daybook_key_used = daybook_gstin
        master_key_used = master_gstin
    else:
        daybook_customer = cleaned_data.customer_column or detect_customer_column(df)
        master_customer = detect_customer_column(master)

        if not daybook_customer or not master_customer:
            raise ValueError("No suitable join key found in both datasets (GSTIN/customer).")

        df["join_key"] = standardize_text(df[daybook_customer])
        master["join_key"] = standardize_text(master[master_customer])
        key_used = "customer"
        daybook_key_used = daybook_customer
        master_key_used = master_customer

    deduped_master = master.dropna(subset=["join_key"]).drop_duplicates(subset=["join_key"], keep="first")
    duplicates_removed = len(master) - len(deduped_master)

    merged = pd.merge(
        df,
        deduped_master,
        on="join_key",
        how="left",
        suffixes=("", "_master"),
        indicator=True,
    )

    total = len(merged)
    unmatched_mask = merged["_merge"] == "left_only"
    unmatched = int(unmatched_mask.sum())
    matched = total - unmatched
    match_rate = float((matched / total) * 100) if total else 0.0

    LOGGER.info("Integration key used: %s (%s -> %s)", key_used, daybook_key_used, master_key_used)
    LOGGER.info("Match stats: total=%s matched=%s unmatched=%s match_rate=%.2f%%", total, matched, unmatched, match_rate)
    if duplicates_removed > 0:
        LOGGER.warning("Master duplicate join keys removed: %s", duplicates_removed)

    merged["_merge_status"] = merged["_merge"].astype(str).map(
        {
            "both": "matched",
            "left_only": "missing_in_master",
            "right_only": "missing_in_daybook",
        }
    )
    merged = merged.drop(columns=["_merge"])

    stats = {
        "join_key_used": key_used,
        "join_key_daybook": daybook_key_used,
        "join_key_master": master_key_used,
        "total_rows": total,
        "matched_rows": matched,
        "unmatched_rows": unmatched,
        "match_rate": match_rate,
        "master_duplicates_removed": duplicates_removed,
    }

    return merged, stats


def integrate_sales_and_master(
    cleaned_sales_data: CleanedSalesData,
    cleaned_master_df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Merge cleaned DayBook and Master data and return merged data with integration summary."""
    if not isinstance(cleaned_sales_data, CleanedSalesData):
        raise TypeError("cleaned_sales_data must be a CleanedSalesData instance.")
    if not isinstance(cleaned_master_df, pd.DataFrame):
        raise TypeError("cleaned_master_df must be a pandas DataFrame.")

    working_daybook = cleaned_sales_data.dataframe.copy()
    working_master = cleaned_master_df.copy()

    try:
        join_daybook, join_master, strategy = _select_join_keys(working_daybook, working_master)
    except ValueError:
        LOGGER.warning(
            "Skipping DayBook-to-Master merge because the reference workbook does not share customer/GSTIN keys."
        )
        return working_daybook, _build_skipped_integration_summary(working_daybook, working_master)

    working_daybook["_join_key"] = _normalize_join_values(working_daybook[join_daybook])
    working_master["_join_key"] = _normalize_join_values(working_master[join_master])

    if strategy == "gstin":
        LOGGER.info("Integration join key selected: GSTIN (%s -> %s)", join_daybook, join_master)
    else:
        LOGGER.info(
            "Integration join key selected: customer (%s -> %s). GSTIN not available in both datasets.",
            join_daybook,
            join_master,
        )

    master_dedup, duplicates_removed = _deduplicate_master(working_master)
    if duplicates_removed > 0:
        LOGGER.warning("Master duplicate-key rows removed: %s", duplicates_removed)

    merged = pd.merge(
        working_daybook,
        master_dedup,
        on="_join_key",
        how="left",
        suffixes=("", "_master"),
        indicator=True,
    )

    unmatched_mask = merged["_merge"] == "left_only"
    unmatched_count = int(unmatched_mask.sum())
    total_rows = len(merged)
    join_success_rate = float((~unmatched_mask).mean() * 100) if total_rows else 0.0
    unmatched_rate = float(unmatched_mask.mean() * 100) if total_rows else 0.0

    missing_daybook_keys = int(working_daybook["_join_key"].isna().sum())
    if missing_daybook_keys > 0:
        LOGGER.warning("DayBook rows with missing join key values: %s", missing_daybook_keys)

    if unmatched_count > 0:
        LOGGER.warning("Unmatched DayBook rows: %s (%.2f%%)", unmatched_count, unmatched_rate)

    LOGGER.info(
        "Integration completed with matched %.2f%% and unmatched %.2f%% of DayBook rows.",
        join_success_rate,
        unmatched_rate,
    )

    merged["_merge_status"] = (
        merged["_merge"]
        .astype(str)
        .map(
            {
                "both": "matched",
                "left_only": "missing_in_master",
                "right_only": "missing_in_daybook",
            }
        )
        .fillna("unknown")
    )
    merged = merged.drop(columns=["_merge", "_join_key"])

    matched_rows = total_rows - unmatched_count
    summary = {
        "join_key_used": strategy,
        "join_key_daybook": join_daybook,
        "join_key_master": join_master,
        "total_rows": total_rows,
        "matched_rows": matched_rows,
        "unmatched_rows": unmatched_count,
        "match_rate_pct": join_success_rate,
        "unmatched_rate_pct": unmatched_rate,
        "master_duplicate_rows_removed": duplicates_removed,
        "daybook_rows_missing_join_key": missing_daybook_keys,
    }

    return merged, summary
