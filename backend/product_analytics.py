"""Product-level analytics helpers for sales dashboard APIs."""

from __future__ import annotations

import re
from typing import Optional

import pandas as pd

from data_cleaning import detect_product_column


def _normalize_text(value: object) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_name_series(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .fillna("")
        .map(_normalize_text)
        .replace({"": pd.NA})
    )


def _select_transaction_product_column(transactions_df: pd.DataFrame, catalog_keys: set[str]) -> Optional[str]:
    text_columns = [
        col
        for col in transactions_df.columns
        if pd.api.types.is_object_dtype(transactions_df[col]) or pd.api.types.is_string_dtype(transactions_df[col])
    ]

    if not text_columns:
        return None

    if not catalog_keys:
        return detect_product_column(transactions_df)

    best_column: Optional[str] = None
    best_overlap = 0

    for col in text_columns:
        normalized_values = _normalize_name_series(transactions_df[col]).dropna().unique().tolist()
        overlap = sum(1 for value in normalized_values if value in catalog_keys)
        if overlap > best_overlap:
            best_overlap = overlap
            best_column = col

    return best_column if best_overlap > 0 else None


def detect_category_column(df: pd.DataFrame) -> Optional[str]:
    candidates = [str(col) for col in df.columns]
    preferred = ["category", "under", "product_category", "item_category"]
    for name in preferred:
        if name in candidates:
            return name

    keyword_hits: list[tuple[int, str]] = []
    include_tokens = ["category", "under", "group", "type", "class"]
    exclude_tokens = ["amount", "price", "rate", "qty", "quantity", "gst"]

    for col in candidates:
        lowered = col.lower()
        if any(token in lowered for token in exclude_tokens):
            continue

        score = sum(1 for token in include_tokens if token in lowered)
        if score > 0:
            keyword_hits.append((score, col))

    if not keyword_hits:
        return None

    keyword_hits.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
    return keyword_hits[0][1]


def prepare_items_catalog(items_df: pd.DataFrame) -> pd.DataFrame:
    product_col = detect_product_column(items_df)
    category_col = detect_category_column(items_df)

    if not product_col:
        string_cols = [
            col
            for col in items_df.columns
            if pd.api.types.is_object_dtype(items_df[col]) or pd.api.types.is_string_dtype(items_df[col])
        ]
        product_col = string_cols[0] if string_cols else None

    if not product_col:
        return pd.DataFrame(columns=["_product_key", "_catalog_product", "_catalog_category"])

    catalog = items_df.copy()
    catalog["_product_key"] = _normalize_name_series(catalog[product_col])
    catalog["_catalog_product"] = catalog[product_col].astype("string").str.strip()

    if category_col and category_col in catalog.columns:
        catalog["_catalog_category"] = catalog[category_col].astype("string").str.strip().fillna("Uncategorized")
    else:
        catalog["_catalog_category"] = "Uncategorized"

    catalog = catalog.dropna(subset=["_product_key"]).drop_duplicates(subset=["_product_key"], keep="first")
    return catalog[["_product_key", "_catalog_product", "_catalog_category"]]


def enrich_transactions_with_products(transactions_df: pd.DataFrame, items_df: pd.DataFrame) -> pd.DataFrame:
    enriched = transactions_df.copy()
    catalog = prepare_items_catalog(items_df)
    catalog_keys = set(catalog["_product_key"].dropna().astype(str).tolist()) if not catalog.empty else set()

    txn_product_col = _select_transaction_product_column(enriched, catalog_keys)
    if not txn_product_col:
        txn_product_col = detect_product_column(enriched) if not catalog_keys else None

    if not txn_product_col:
        enriched["_product"] = "Unknown Product"
        enriched["_category"] = "Uncategorized"
        return enriched

    enriched["_product"] = enriched[txn_product_col].astype("string").str.strip().fillna("Unknown Product")
    enriched["_product_key"] = _normalize_name_series(enriched[txn_product_col])

    if not catalog.empty:
        enriched = enriched.merge(catalog, on="_product_key", how="left")
        enriched["_product"] = enriched["_catalog_product"].fillna(enriched["_product"])
        enriched["_category"] = enriched["_catalog_category"].fillna("Uncategorized")
        enriched = enriched.drop(columns=["_catalog_product", "_catalog_category"])
    else:
        enriched["_category"] = "Uncategorized"

    enriched["_product"] = enriched["_product"].astype("string").str.strip().replace({"": "Unknown Product"})
    enriched["_category"] = enriched["_category"].astype("string").str.strip().replace({"": "Uncategorized"})
    enriched = enriched.drop(columns=["_product_key"], errors="ignore")

    return enriched


def top_products_by_revenue(df: pd.DataFrame, limit: int = 10) -> list[dict[str, object]]:
    grouped = (
        df.groupby("_product", dropna=False)["_revenue"]
        .sum()
        .sort_values(ascending=False)
        .head(limit)
    )
    return [{"product": str(name), "revenue": float(value)} for name, value in grouped.items()]


def revenue_by_category(df: pd.DataFrame) -> list[dict[str, object]]:
    grouped = (
        df.groupby("_category", dropna=False)["_revenue"]
        .sum()
        .sort_values(ascending=False)
    )
    return [{"category": str(name), "revenue": float(value)} for name, value in grouped.items()]


def product_contribution(df: pd.DataFrame, limit: int = 10) -> list[dict[str, object]]:
    total_revenue = float(df["_revenue"].sum()) if len(df) else 0.0
    products = top_products_by_revenue(df, limit=limit)

    contribution: list[dict[str, object]] = []
    for item in products:
        revenue = float(item["revenue"])
        pct = (revenue / total_revenue * 100.0) if total_revenue else 0.0
        contribution.append(
            {
                "product": item["product"],
                "revenue": revenue,
                "contribution_pct": round(pct, 2),
            }
        )

    return contribution


def _detect_catalog_value_column(df: pd.DataFrame) -> Optional[str]:
    preferred = ["opening_balance", "rate", "opening_qty", "value", "amount", "price"]
    candidates = [col for col in preferred if col in df.columns]

    numeric_columns = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
    for col in numeric_columns:
        if col not in candidates:
            candidates.append(col)

    if not candidates:
        return None

    best_col: Optional[str] = None
    best_score = -1

    for col in candidates:
        values = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        non_zero = int((values.abs() > 0).sum())
        total_abs = float(values.abs().sum())
        score = non_zero * 1_000_000 + total_abs
        if score > best_score:
            best_score = score
            best_col = col

    return best_col


def catalog_top_products(items_df: pd.DataFrame, limit: int = 10) -> list[dict[str, object]]:
    if items_df.empty:
        return []

    product_col = detect_product_column(items_df)
    if not product_col:
        return []

    value_col = _detect_catalog_value_column(items_df)
    if not value_col:
        return []

    working = items_df.copy()
    working[product_col] = working[product_col].astype("string").str.strip()
    working[value_col] = pd.to_numeric(working[value_col], errors="coerce").fillna(0.0)
    working = working.dropna(subset=[product_col])

    grouped = (
        working.groupby(product_col, dropna=False)[value_col]
        .sum()
        .sort_values(ascending=False)
        .head(limit)
    )

    return [
        {
            "product": str(name),
            "revenue": float(value),
            "source": "catalog",
            "metric": value_col,
        }
        for name, value in grouped.items()
    ]


def catalog_revenue_by_category(items_df: pd.DataFrame) -> list[dict[str, object]]:
    if items_df.empty:
        return []

    product_col = detect_product_column(items_df)
    category_col = detect_category_column(items_df)
    value_col = _detect_catalog_value_column(items_df)

    if not product_col or not category_col or not value_col:
        return []

    working = items_df.copy()
    working[category_col] = working[category_col].astype("string").str.strip().fillna("Uncategorized")
    working[value_col] = pd.to_numeric(working[value_col], errors="coerce").fillna(0.0)

    grouped = working.groupby(category_col, dropna=False)[value_col].sum().sort_values(ascending=False)

    return [
        {
            "category": str(name),
            "revenue": float(value),
            "source": "catalog",
            "metric": value_col,
        }
        for name, value in grouped.items()
    ]


def catalog_product_contribution(items_df: pd.DataFrame, limit: int = 10) -> list[dict[str, object]]:
    top_items = catalog_top_products(items_df, limit=limit)
    total = sum(float(item.get("revenue", 0.0)) for item in top_items)

    output: list[dict[str, object]] = []
    for item in top_items:
        revenue = float(item.get("revenue", 0.0))
        pct = (revenue / total * 100.0) if total else 0.0
        output.append(
            {
                "product": item.get("product", "Unknown Product"),
                "revenue": revenue,
                "contribution_pct": round(pct, 2),
                "source": "catalog",
                "metric": item.get("metric", "value"),
            }
        )

    return output
