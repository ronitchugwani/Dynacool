"""FastAPI backend for sales analytics dashboard endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from data_cleaning import clean_reference_data, clean_sales_data
from data_integration import integrate_data

APP = FastAPI(title="Sales Analytics API", version="1.0.0")

APP.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _discover_excel_file(preferred_names: list[str], fallback_keyword: str) -> Path:
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

    raise FileNotFoundError(f"No Excel file found for keyword '{fallback_keyword}' in {cwd}")


def _discover_optional_excel_file(preferred_names: list[str], fallback_keyword: str) -> Path | None:
    try:
        return _discover_excel_file(preferred_names, fallback_keyword)
    except FileNotFoundError:
        return None


def _discover_file(preferred_names: list[str], glob_pattern: str) -> Path | None:
    cwd = Path.cwd()
    for name in preferred_names:
        candidate = cwd / name
        if candidate.exists():
            return candidate

    matches = sorted(cwd.glob(glob_pattern), key=lambda p: p.name.lower())
    return matches[0] if matches else None


def _standardize_text_series(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
        .replace({"": pd.NA, "nan": pd.NA, "none": pd.NA})
    )


def _normalize_items_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {
        col: str(col).strip().lower().replace(" ", "_")
        for col in df.columns
    }
    return df.rename(columns=renamed)


def _load_items_dataframe() -> pd.DataFrame:
    items_path = _discover_file(["Items.csv"], "*items*.csv")
    if items_path is None:
        return pd.DataFrame(columns=["date", "customer", "item_name", "category", "total_value", "_year", "_customer_norm"])

    items_df = pd.read_csv(items_path)
    if items_df.empty:
        return pd.DataFrame(columns=["date", "customer", "item_name", "category", "total_value", "_year", "_customer_norm"])

    items_df = _normalize_items_columns(items_df)

    if "item_name" not in items_df.columns and "product" in items_df.columns:
        items_df["item_name"] = items_df["product"]
    if "customer" not in items_df.columns:
        items_df["customer"] = "Unknown Customer"
    if "category" not in items_df.columns:
        items_df["category"] = "Uncategorized"

    if "total_value" not in items_df.columns:
        qty_col = "quantity" if "quantity" in items_df.columns else None
        unit_price_col = "unit_price" if "unit_price" in items_df.columns else None
        if qty_col and unit_price_col:
            items_df["total_value"] = pd.to_numeric(items_df[qty_col], errors="coerce") * pd.to_numeric(items_df[unit_price_col], errors="coerce")
        else:
            items_df["total_value"] = 0.0

    items_df["total_value"] = pd.to_numeric(items_df["total_value"], errors="coerce").fillna(0.0)

    if "date" in items_df.columns:
        items_df["date"] = pd.to_datetime(items_df["date"], errors="coerce")
    else:
        items_df["date"] = pd.NaT

    items_df["_year"] = items_df["date"].dt.year
    items_df["_customer_norm"] = _standardize_text_series(items_df["customer"])
    items_df["item_name"] = items_df["item_name"].astype("string").fillna("Unknown Item").str.strip()
    items_df["category"] = items_df["category"].astype("string").fillna("Uncategorized").str.strip()

    return items_df


def _attach_sales_customer_match(items_df: pd.DataFrame, sales_df: pd.DataFrame) -> pd.DataFrame:
    if items_df.empty:
        return items_df.copy()

    sales_customers = sales_df[["_customer"]].copy()
    sales_customers["_customer_norm"] = _standardize_text_series(sales_customers["_customer"])
    sales_customers = sales_customers.dropna(subset=["_customer_norm"]).drop_duplicates(subset=["_customer_norm"])
    sales_customers["_matched_in_sales"] = True

    merged = items_df.merge(
        sales_customers[["_customer_norm", "_matched_in_sales"]],
        on="_customer_norm",
        how="left",
    )
    merged["_matched_in_sales"] = merged["_matched_in_sales"].fillna(False)
    return merged


def _load_base_dataframe() -> pd.DataFrame:
    daybook_path = _discover_excel_file(["DayBook.xlsx", "DayBook (1).xlsx"], "daybook")
    master_path = _discover_excel_file(["Master.xlsx"], "master")

    cleaned_sales = clean_sales_data(daybook_path)
    cleaned_master = clean_reference_data(master_path)

    try:
        merged, _ = integrate_data(cleaned_sales, cleaned_master)
        df = merged
    except Exception:
        df = cleaned_sales.dataframe.copy()

    date_col = cleaned_sales.date_column
    revenue_col = cleaned_sales.revenue_column
    customer_col = cleaned_sales.customer_column

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
    df[revenue_col] = pd.to_numeric(df[revenue_col], errors="coerce")
    df = df.dropna(subset=[date_col, revenue_col])

    df["_date"] = df[date_col]
    df["_year"] = df[date_col].dt.year
    df["_month"] = df[date_col].dt.to_period("M").astype(str)
    df["_revenue"] = df[revenue_col]

    if customer_col and customer_col in df.columns:
        df["_customer"] = df[customer_col].astype("string").fillna("Unknown Customer")
    else:
        df["_customer"] = "Unknown Customer"

    df["_customer_norm"] = _standardize_text_series(df["_customer"])

    return df


BASE_DF = _load_base_dataframe()
BASE_ITEMS_DF = _attach_sales_customer_match(_load_items_dataframe(), BASE_DF)


def _apply_filters(df: pd.DataFrame, year: Optional[int], customer: Optional[str]) -> pd.DataFrame:
    filtered = df.copy()

    if year is not None:
        filtered = filtered[filtered["_year"] == year]

    if customer:
        normalized_customer = customer.strip().lower()
        if normalized_customer and normalized_customer != "all":
            filtered = filtered[filtered["_customer"].str.lower() == normalized_customer]

    return filtered


def _apply_item_filters(df: pd.DataFrame, year: Optional[int], customer: Optional[str]) -> pd.DataFrame:
    filtered = df.copy()

    if year is not None and "_year" in filtered.columns:
        filtered = filtered[filtered["_year"] == year]

    if customer:
        normalized_customer = customer.strip().lower()
        if normalized_customer and normalized_customer != "all":
            filtered = filtered[filtered["_customer_norm"] == normalized_customer]

    return filtered


@APP.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@APP.get("/kpis")
def get_kpis(
    year: Optional[int] = Query(default=None),
    customer: Optional[str] = Query(default=None),
) -> dict[str, object]:
    df = _apply_filters(BASE_DF, year=year, customer=customer)

    total_revenue = float(df["_revenue"].sum()) if len(df) else 0.0
    total_transactions = int(len(df))
    average_transaction_value = float(total_revenue / total_transactions) if total_transactions else 0.0

    years = sorted([int(y) for y in BASE_DF["_year"].dropna().unique().tolist()])
    customers = sorted([str(c) for c in BASE_DF["_customer"].dropna().unique().tolist()])

    return {
        "total_revenue": total_revenue,
        "total_transactions": total_transactions,
        "average_transaction_value": average_transaction_value,
        "years": years,
        "customers": customers,
    }


@APP.get("/monthly-sales")
def get_monthly_sales(
    year: Optional[int] = Query(default=None),
    customer: Optional[str] = Query(default=None),
) -> list[dict[str, object]]:
    df = _apply_filters(BASE_DF, year=year, customer=customer)
    monthly = df.groupby("_month", dropna=False)["_revenue"].sum().sort_index()

    return [{"month": month, "revenue": float(value)} for month, value in monthly.items()]


@APP.get("/top-customers")
def get_top_customers(
    year: Optional[int] = Query(default=None),
    customer: Optional[str] = Query(default=None),
) -> list[dict[str, object]]:
    df = _apply_filters(BASE_DF, year=year, customer=customer)

    top = (
        df.groupby("_customer", dropna=False)["_revenue"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    return [{"customer": str(name), "revenue": float(value)} for name, value in top.items()]


@APP.get("/gst")
def get_gst(
    year: Optional[int] = Query(default=None),
    customer: Optional[str] = Query(default=None),
) -> list[dict[str, object]]:
    df = _apply_filters(BASE_DF, year=year, customer=customer)

    gst_columns = [
        col
        for col in df.columns
        if "gst" in str(col).lower() and "rate" not in str(col).lower() and "percent" not in str(col).lower()
    ]

    breakdown: list[dict[str, object]] = []
    for col in gst_columns:
        values = pd.to_numeric(df[col], errors="coerce")
        total = float(values.sum(skipna=True))
        if total > 0:
            breakdown.append({"name": col, "value": total})

    return breakdown


@APP.get("/top-products")
def get_top_products(
    year: Optional[int] = Query(default=None),
    customer: Optional[str] = Query(default=None),
) -> list[dict[str, object]]:
    df = _apply_item_filters(BASE_ITEMS_DF, year=year, customer=customer)
    result = (
        df.groupby("item_name", dropna=False)["total_value"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
        .rename(columns={"item_name": "Item Name", "total_value": "Total Value"})
    )
    return result.to_dict(orient="records")


@APP.get("/category-sales")
def get_category_sales(
    year: Optional[int] = Query(default=None),
    customer: Optional[str] = Query(default=None),
) -> list[dict[str, object]]:
    df = _apply_item_filters(BASE_ITEMS_DF, year=year, customer=customer)
    result = (
        df.groupby("category", dropna=False)["total_value"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={"category": "Category", "total_value": "Total Value"})
    )
    return result.to_dict(orient="records")
