"""FastAPI backend for the interactive Dynacool analytics dashboard."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from data_cleaning import clean_reference_data, clean_sales_data
from data_integration import integrate_data
from paths import BACKEND_DIR, DATA_DIR, resolve_backend_path

APP = FastAPI(title="Sales Analytics API", version="1.1.0")

frontend_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
configured_frontend_origin = os.getenv("FRONTEND_ORIGIN", "").strip()
if configured_frontend_origin:
    frontend_origins.extend([origin.strip() for origin in configured_frontend_origin.split(",") if origin.strip()])

APP.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _discover_excel_file(preferred_names: list[str], fallback_keyword: str) -> Path:
    cwd = BACKEND_DIR

    for name in preferred_names:
        candidate = resolve_backend_path(name)
        if candidate.exists():
            return candidate

    matches = sorted(
        [
            path
            for path in DATA_DIR.glob("*.xlsx")
            if fallback_keyword.lower() in path.stem.lower()
        ],
        key=lambda p: p.name.lower(),
    )
    if matches:
        return matches[0]

    raise FileNotFoundError(f"No Excel file found for keyword '{fallback_keyword}' in {cwd}")


def _discover_file(preferred_names: list[str], glob_pattern: str) -> Path | None:
    cwd = BACKEND_DIR
    for name in preferred_names:
        candidate = resolve_backend_path(name)
        if candidate.exists():
            return candidate

    matches = sorted(DATA_DIR.glob(glob_pattern), key=lambda p: p.name.lower())
    return matches[0] if matches else None


def _normalize_text(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _normalize_series(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
        .replace({"": pd.NA, "nan": pd.NA, "none": pd.NA})
    )


def _normalize_items_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={col: str(col).strip().lower().replace(" ", "_") for col in df.columns})


def _load_items_dataframe() -> pd.DataFrame:
    items_path = _discover_file(["Items.csv"], "*items*.csv")
    if items_path is None:
        return pd.DataFrame(
            columns=[
                "date",
                "customer",
                "item_name",
                "category",
                "quantity",
                "unit_price",
                "total_value",
                "_year",
                "_month",
                "_customer_norm",
                "_product",
                "_product_norm",
            ]
        )

    items_df = pd.read_csv(items_path)
    if items_df.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "customer",
                "item_name",
                "category",
                "quantity",
                "unit_price",
                "total_value",
                "_year",
                "_month",
                "_customer_norm",
                "_product",
                "_product_norm",
            ]
        )

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
            items_df["total_value"] = (
                pd.to_numeric(items_df[qty_col], errors="coerce")
                * pd.to_numeric(items_df[unit_price_col], errors="coerce")
            )
        else:
            items_df["total_value"] = 0.0

    items_df["date"] = pd.to_datetime(items_df.get("date"), errors="coerce")
    items_df["quantity"] = pd.to_numeric(items_df.get("quantity"), errors="coerce").fillna(0.0)
    items_df["unit_price"] = pd.to_numeric(items_df.get("unit_price"), errors="coerce").fillna(0.0)
    items_df["total_value"] = pd.to_numeric(items_df["total_value"], errors="coerce").fillna(0.0)
    items_df["customer"] = items_df["customer"].astype("string").fillna("Unknown Customer").str.strip()
    items_df["item_name"] = items_df["item_name"].astype("string").fillna("Unknown Product").str.strip()
    items_df["category"] = items_df["category"].astype("string").fillna("Uncategorized").str.strip()
    items_df = items_df.dropna(subset=["date"])

    items_df["_year"] = items_df["date"].dt.year
    items_df["_month"] = items_df["date"].dt.to_period("M").astype(str)
    items_df["_customer_norm"] = _normalize_series(items_df["customer"])
    items_df["_product"] = items_df["item_name"]
    items_df["_product_norm"] = _normalize_series(items_df["item_name"])

    return items_df


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
        df["_customer"] = df[customer_col].astype("string").fillna("Unknown Customer").str.strip()
    else:
        df["_customer"] = "Unknown Customer"

    df["_customer_norm"] = _normalize_series(df["_customer"])

    return df


BASE_DF = _load_base_dataframe()
BASE_ITEMS_DF = _load_items_dataframe()


def _apply_item_filters(
    df: pd.DataFrame,
    year: Optional[int] = None,
    customer: Optional[str] = None,
    product: Optional[str] = None,
) -> pd.DataFrame:
    filtered = df.copy()

    if year is not None and "_year" in filtered.columns:
        filtered = filtered[filtered["_year"] == year]

    if customer:
        customer_norm = _normalize_text(customer)
        if customer_norm and customer_norm != "all" and "_customer_norm" in filtered.columns:
            filtered = filtered[filtered["_customer_norm"] == customer_norm]

    if product:
        product_norm = _normalize_text(product)
        if product_norm and product_norm != "all" and "_product_norm" in filtered.columns:
            filtered = filtered[filtered["_product_norm"] == product_norm]

    return filtered


def _product_customer_scope(
    year: Optional[int] = None,
    customer: Optional[str] = None,
    product: Optional[str] = None,
) -> set[str] | None:
    """Approximate product-level filtering for sales views using item-level customer matches."""
    if not product:
        return None

    scoped_items = _apply_item_filters(BASE_ITEMS_DF, year=year, customer=customer, product=product)
    if scoped_items.empty:
        return set()

    return set(scoped_items["_customer_norm"].dropna().astype(str).tolist())


def _apply_sales_filters(
    df: pd.DataFrame,
    year: Optional[int] = None,
    customer: Optional[str] = None,
    product: Optional[str] = None,
) -> pd.DataFrame:
    filtered = df.copy()

    if year is not None:
        filtered = filtered[filtered["_year"] == year]

    if customer:
        customer_norm = _normalize_text(customer)
        if customer_norm and customer_norm != "all":
            filtered = filtered[filtered["_customer_norm"] == customer_norm]

    scoped_customers = _product_customer_scope(year=year, customer=customer, product=product)
    if scoped_customers is not None:
        if not scoped_customers:
            return filtered.iloc[0:0].copy()
        filtered = filtered[filtered["_customer_norm"].isin(scoped_customers)]

    return filtered


def _years_from_frames(*frames: pd.DataFrame) -> list[int]:
    values: set[int] = set()
    for frame in frames:
        if "_year" not in frame.columns:
            continue
        for value in frame["_year"].dropna().tolist():
            values.add(int(value))
    return sorted(values)


def _sorted_strings(values: pd.Series) -> list[str]:
    cleaned = [str(value).strip() for value in values.dropna().astype("string").tolist() if str(value).strip()]
    return sorted(set(cleaned), key=str.casefold)


def _build_filter_options(
    year: Optional[int] = None,
    customer: Optional[str] = None,
    product: Optional[str] = None,
) -> dict[str, list[object]]:
    years_source_sales = _apply_sales_filters(BASE_DF, year=None, customer=customer, product=product)
    years_source_items = _apply_item_filters(BASE_ITEMS_DF, year=None, customer=customer, product=product)

    customers_source = _apply_sales_filters(BASE_DF, year=year, customer=None, product=product)
    products_source = _apply_item_filters(BASE_ITEMS_DF, year=year, customer=customer, product=None)

    return {
        "years": _years_from_frames(years_source_sales, years_source_items),
        "customers": _sorted_strings(customers_source["_customer"]) if "_customer" in customers_source.columns else [],
        "products": _sorted_strings(products_source["_product"]) if "_product" in products_source.columns else [],
    }


@APP.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@APP.get("/filters")
def get_filters(
    year: Optional[int] = Query(default=None),
    customer: Optional[str] = Query(default=None),
    product: Optional[str] = Query(default=None),
) -> dict[str, list[object]]:
    return _build_filter_options(year=year, customer=customer, product=product)


@APP.get("/kpis")
def get_kpis(
    year: Optional[int] = Query(default=None),
    customer: Optional[str] = Query(default=None),
    product: Optional[str] = Query(default=None),
) -> dict[str, object]:
    sales_df = _apply_sales_filters(BASE_DF, year=year, customer=customer, product=product)
    items_df = _apply_item_filters(BASE_ITEMS_DF, year=year, customer=customer, product=product)
    filter_options = _build_filter_options(year=year, customer=customer, product=product)

    total_revenue = float(sales_df["_revenue"].sum()) if len(sales_df) else 0.0
    total_transactions = int(len(sales_df))
    average_transaction_value = float(total_revenue / total_transactions) if total_transactions else 0.0

    return {
        "total_revenue": total_revenue,
        "total_transactions": total_transactions,
        "average_transaction_value": average_transaction_value,
        "item_sales_value": float(items_df["total_value"].sum()) if len(items_df) else 0.0,
        "selected_scope_rows": total_transactions,
        "years": filter_options["years"],
        "customers": filter_options["customers"],
        "products": filter_options["products"],
    }


@APP.get("/monthly-sales")
def get_monthly_sales(
    year: Optional[int] = Query(default=None),
    customer: Optional[str] = Query(default=None),
    product: Optional[str] = Query(default=None),
) -> list[dict[str, object]]:
    df = _apply_sales_filters(BASE_DF, year=year, customer=customer, product=product)
    monthly = df.groupby("_month", dropna=False)["_revenue"].sum().sort_index()
    return [{"month": month, "revenue": float(value)} for month, value in monthly.items()]


@APP.get("/top-customers")
def get_top_customers(
    year: Optional[int] = Query(default=None),
    customer: Optional[str] = Query(default=None),
    product: Optional[str] = Query(default=None),
) -> list[dict[str, object]]:
    df = _apply_sales_filters(BASE_DF, year=year, customer=customer, product=product)
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
    product: Optional[str] = Query(default=None),
) -> list[dict[str, object]]:
    df = _apply_sales_filters(BASE_DF, year=year, customer=customer, product=product)

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
    product: Optional[str] = Query(default=None),
) -> list[dict[str, object]]:
    df = _apply_item_filters(BASE_ITEMS_DF, year=year, customer=customer, product=product)
    result = (
        df.groupby("_product", dropna=False)["total_value"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
        .rename(columns={"_product": "Item Name", "total_value": "Total Value"})
    )
    return result.to_dict(orient="records")


@APP.get("/category-sales")
def get_category_sales(
    year: Optional[int] = Query(default=None),
    customer: Optional[str] = Query(default=None),
    product: Optional[str] = Query(default=None),
) -> list[dict[str, object]]:
    df = _apply_item_filters(BASE_ITEMS_DF, year=year, customer=customer, product=product)
    result = (
        df.groupby("category", dropna=False)["total_value"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={"category": "Category", "total_value": "Total Value"})
    )
    return result.to_dict(orient="records")
