"""OrderHub utility functions."""
import hashlib
import re
from datetime import datetime
from typing import Dict
import pandas as pd


def generate_row_hash(row: dict, platform: str, account: str) -> str:
    hash_str = f"{row.get('date', '')}{row.get('sku', '')}{row.get('amount', 0)}{platform}{account}"
    return hashlib.sha256(hash_str.encode()).hexdigest()


def parse_date(date_val):
    if pd.isna(date_val):
        return None
    if isinstance(date_val, datetime):
        return date_val
    if isinstance(date_val, pd.Timestamp):
        return date_val.to_pydatetime()
    
    date_str = str(date_val).strip()
    formats = ["%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y",
               "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%d %b %Y", "%d %B %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def parse_amount(amount_val) -> float:
    if pd.isna(amount_val):
        return 0.0
    try:
        val = str(amount_val).replace(",", "").replace("₹", "").replace("$", "").strip()
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def parse_qty(qty_val) -> int:
    if pd.isna(qty_val):
        return 1
    try:
        return int(float(str(qty_val).strip()))
    except (ValueError, TypeError):
        return 1


def normalize_column_name(col: str) -> str:
    if not col or not isinstance(col, str):
        return ""
    normalized = col.lower().strip().replace("_", " ").replace("-", " ")
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
    return re.sub(r'\s+', ' ', normalized).strip()


def normalize_column_strict(col: str) -> str:
    if not col or not isinstance(col, str):
        return ""
    return re.sub(r'[^a-z0-9]', '', col.lower().strip())


def split_master_sku(master_sku: str) -> Dict[str, str]:
    result = {"style_code": "", "color_code": "", "size_code": ""}
    if not master_sku or pd.isna(master_sku) or master_sku == "UNMAPPED":
        return result
    parts = str(master_sku).strip().split("-")
    if len(parts) == 1:
        result["style_code"] = parts[0]
    elif len(parts) == 2:
        result["style_code"] = parts[0]
        result["size_code"] = parts[1]
    elif len(parts) == 3:
        result["style_code"] = parts[0]
        result["color_code"] = parts[1]
        result["size_code"] = parts[2]
    else:
        result["style_code"] = parts[0]
        result["size_code"] = parts[-1]
        result["color_code"] = "-".join(parts[1:-1])
    return result


def extract_sku_from_msku(msku: str) -> str:
    if not msku or pd.isna(msku):
        return ""
    msku = str(msku).strip()
    return msku.split("-")[0] if "-" in msku else msku
