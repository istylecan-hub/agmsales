"""SKU and column detection engine."""
import re
from typing import Dict, Any
import pandas as pd
from .utils import normalize_column_name, normalize_column_strict

COLUMN_MAPPINGS = {
    "date": ["order date", "orderdate", "order_date", "purchase date", "date", "invoice date", "created date", "ship date", "sale date"],
    "sku": ["sku", "seller sku", "sellersku", "seller_sku", "product sku", "style code", "item code", "msku", "merchant sku", "asin", "product code", "article code"],
    "qty": ["qty", "quantity", "ordered qty", "units", "order qty", "shipped qty", "item quantity", "count", "pcs"],
    "amount": ["amount", "price", "order value", "total", "value", "sale amount", "selling price", "revenue", "total price", "net amount", "total amount", "mrp"],
    "state": ["state", "shipping state", "ship state", "delivery state", "region", "buyer state", "province"],
    "msku": ["msku", "merchant sku", "merchantsku", "merchant_sku"],
    "order_source": ["order source", "ordersource", "source", "platform", "channel", "sales channel"]
}

PLATFORM_PATTERNS = {
    "amazon": ["amazon", "amz", "seller central", "fba"],
    "meesho": ["meesho"],
    "flipkart": ["flipkart", "fk"],
    "myntra": ["myntra"],
    "ajio": ["ajio"],
    "amazon_flex": ["flex", "amazon flex"],
    "base": ["base", "manual"]
}

MYNTRA_SKU_PRIORITY = ["seller_sku_code", "sellerskucode", "seller sku code", "seller_sku", "sellersku"]


def detect_platform_from_filename(filename: str) -> str:
    filename_lower = filename.lower()
    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            if pattern in filename_lower:
                return platform
    return "unknown"


def detect_platform_from_order_source(order_source: str) -> Dict[str, str]:
    if not order_source or pd.isna(order_source):
        return {"platform": "UNKNOWN", "method": "ORDER_SOURCE_EMPTY"}
    value = str(order_source).strip().lower()
    value = re.sub(r'\s+', ' ', value).strip()
    
    if "meesho" in value:
        return {"platform": "meesho", "method": "ORDER_SOURCE_KEYWORD"}
    elif value.startswith("fk") or "flipkart" in value:
        return {"platform": "flipkart", "method": "ORDER_SOURCE_KEYWORD"}
    elif value.startswith("amz") or "amazon" in value:
        return {"platform": "amazon", "method": "ORDER_SOURCE_KEYWORD"}
    elif "myntra" in value:
        return {"platform": "myntra", "method": "ORDER_SOURCE_KEYWORD"}
    elif "ajio" in value:
        return {"platform": "ajio", "method": "ORDER_SOURCE_KEYWORD"}
    return {"platform": "UNKNOWN", "method": "ORDER_SOURCE_NO_MATCH"}


def detect_sku_pattern(column_data: pd.Series) -> bool:
    if column_data.empty:
        return False
    sku_pattern = re.compile(r'^[A-Za-z0-9][A-Za-z0-9\-_]{1,29}$')
    valid_count = sum(1 for val in column_data.dropna() if sku_pattern.match(str(val).strip()) and 2 <= len(str(val).strip()) <= 30)
    total_count = len(column_data.dropna())
    return (valid_count / total_count) > 0.2 if total_count > 0 else False


def detect_columns(df: pd.DataFrame, platform: str = "", filename: str = "") -> Dict[str, Any]:
    detected = {"columns": {}, "detection_log": [], "auto_detected_sku": False, "use_msku_extraction": False, "is_base_orders": False, "is_myntra": False}
    
    filename_lower = filename.lower() if filename else ""
    is_base = "base" in filename_lower
    is_myntra = "myntra" in filename_lower
    detected["is_base_orders"] = is_base
    detected["is_myntra"] = is_myntra
    
    col_mapping = {normalize_column_name(str(col)): str(col) for col in df.columns if normalize_column_name(str(col))}
    col_mapping_strict = {normalize_column_strict(str(col)): str(col) for col in df.columns if normalize_column_strict(str(col))}
    
    # Myntra SKU priority
    if is_myntra:
        for priority_col in MYNTRA_SKU_PRIORITY:
            priority_strict = normalize_column_strict(priority_col)
            if priority_strict in col_mapping_strict:
                detected["columns"]["sku"] = col_mapping_strict[priority_strict]
                detected["detection_log"].append(f"sku: MYNTRA_PRIORITY '{col_mapping_strict[priority_strict]}'")
                break
    
    # Standard detection
    for target, variations in COLUMN_MAPPINGS.items():
        if target == "sku" and is_myntra and detected["columns"].get("sku"):
            continue
        if detected["columns"].get(target):
            continue
        detected["columns"][target] = None
        
        for var in variations:
            var_strict = normalize_column_strict(var)
            if var_strict in col_mapping_strict:
                detected["columns"][target] = col_mapping_strict[var_strict]
                detected["detection_log"].append(f"{target}: matched '{col_mapping_strict[var_strict]}'")
                break
            if var in col_mapping:
                detected["columns"][target] = col_mapping[var]
                detected["detection_log"].append(f"{target}: matched '{col_mapping[var]}'")
                break
    
    # MSKU fallback
    msku_col = detected["columns"].get("msku")
    if msku_col and not detected["columns"].get("sku"):
        detected["columns"]["sku"] = msku_col
        detected["use_msku_extraction"] = True
    
    # Auto-detect SKU
    if not detected["columns"].get("sku"):
        for col in df.columns:
            if df[col].dtype == object and detect_sku_pattern(df[col]):
                detected["columns"]["sku"] = col
                detected["auto_detected_sku"] = True
                break
    
    return detected
