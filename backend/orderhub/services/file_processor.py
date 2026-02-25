"""File processing service."""
import uuid
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from .utils import generate_row_hash, parse_date, parse_amount, parse_qty, split_master_sku, extract_sku_from_msku
from .sku_detection import detect_columns, detect_platform_from_filename, detect_platform_from_order_source
from .unmapped import update_unmapped_sku


async def process_order_file(db, file_id: str, platform: str, account: str, file_path: Path):
    try:
        await db.orderhub_uploads.update_one({"id": file_id}, {"$set": {"status": "processing"}})
        
        # Read file
        df = None
        if file_path.suffix.lower() in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path)
        else:
            for enc in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    df = pd.read_csv(file_path, encoding=enc)
                    break
                except:
                    continue
            if df is None:
                df = pd.read_csv(file_path, encoding='utf-8', errors='ignore')
        
        total_rows = len(df)
        filename = file_path.name
        actual_platform = platform
        is_base = "base" in filename.lower()
        
        if not platform or platform == "unknown":
            actual_platform = detect_platform_from_filename(filename)
        
        detection = detect_columns(df, actual_platform, filename)
        cols = detection["columns"]
        use_msku = detection.get("use_msku_extraction", False)
        
        sku_col = cols.get("sku")
        if not sku_col:
            for col in df.columns:
                if df[col].dtype == object:
                    sku_col = col
                    break
        
        if not sku_col:
            raise ValueError("SKU column not found")
        
        # Get master SKUs
        master_skus = {doc["sku"].lower(): doc["master_sku"] async for doc in db.orderhub_master_skus.find({}, {"_id": 0})}
        
        rows_inserted, duplicates = 0, 0
        orders_batch = []
        
        for idx, row in df.iterrows():
            try:
                order_date = parse_date(row.get(cols.get("date"))) if cols.get("date") else None
                if not order_date:
                    order_date = datetime.now(timezone.utc)
                
                raw_sku = str(row[sku_col]).strip() if pd.notna(row[sku_col]) else ""
                sku = extract_sku_from_msku(raw_sku) if use_msku else raw_sku
                if not sku:
                    continue
                
                qty = parse_qty(row.get(cols.get("qty"), 1))
                amount = parse_amount(row.get(cols.get("amount"), 0))
                state = str(row.get(cols.get("state"), "")).strip() if cols.get("state") and pd.notna(row.get(cols.get("state"))) else ""
                
                row_platform = actual_platform
                if is_base and cols.get("order_source"):
                    src = row.get(cols.get("order_source"))
                    row_platform = detect_platform_from_order_source(src)["platform"]
                
                row_hash = generate_row_hash({"date": order_date.isoformat(), "sku": sku, "amount": amount}, row_platform, account)
                
                existing = await db.orderhub_orders.find_one({"row_hash": row_hash})
                if existing:
                    duplicates += 1
                    continue
                
                master_sku = master_skus.get(sku.lower(), "UNMAPPED")
                if master_sku == "UNMAPPED":
                    await update_unmapped_sku(db, sku, row_platform, qty, amount, filename, master_skus)
                
                parts = split_master_sku(master_sku)
                orders_batch.append({
                    "id": str(uuid.uuid4()), "order_date": order_date.isoformat(), "sku": sku,
                    "master_sku": master_sku, **parts, "qty": qty, "amount": amount, "state": state,
                    "platform": row_platform, "account": account, "file_id": file_id,
                    "row_hash": row_hash, "created_at": datetime.now(timezone.utc).isoformat()
                })
                rows_inserted += 1
                
                if len(orders_batch) >= 500:
                    await db.orderhub_orders.insert_many(orders_batch)
                    orders_batch = []
            except:
                continue
        
        if orders_batch:
            await db.orderhub_orders.insert_many(orders_batch)
        
        await db.orderhub_uploads.update_one({"id": file_id}, {"$set": {
            "status": "completed", "platform": actual_platform if not is_base else "MIXED",
            "total_rows": total_rows, "rows_inserted": rows_inserted, "duplicates_skipped": duplicates,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }})
    except Exception as e:
        await db.orderhub_uploads.update_one({"id": file_id}, {"$set": {"status": "failed", "errors": [str(e)]}})
