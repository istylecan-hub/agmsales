"""File processing service - Enhanced with chunked processing and bulk insert."""
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from .utils import generate_row_hash, parse_date, parse_amount, parse_qty, split_master_sku, extract_sku_from_msku
from .sku_detection import detect_columns, detect_platform_from_filename, detect_platform_from_order_source
from .unmapped import update_unmapped_sku


async def process_order_file_chunked(db, file_id: str, platform: str, account: str, file_path: Path, chunk_size: int = 5000, batch_size: int = 1000):
    """
    Process order file with chunked reading and bulk insert.
    NO ROW LIMITS - processes entire file.
    """
    start_time = time.time()
    
    try:
        await db.orderhub_uploads.update_one({"id": file_id}, {"$set": {"status": "processing"}})
        
        filename = file_path.name
        actual_platform = platform
        is_base = "base" in filename.lower()
        
        if not platform or platform == "unknown":
            actual_platform = detect_platform_from_filename(filename)
        
        # Get master SKUs (load once)
        master_skus = {doc["sku"].lower(): doc["master_sku"] async for doc in db.orderhub_master_skus.find({}, {"_id": 0})}
        
        total_rows = 0
        rows_inserted = 0
        duplicates = 0
        errors_list = []
        
        # Read file in chunks for memory efficiency
        file_ext = file_path.suffix.lower()
        
        if file_ext in [".xlsx", ".xls"]:
            # Excel files - read all at once (pandas doesn't support chunked Excel reading)
            df_full = pd.read_excel(file_path)
            total_rows = len(df_full)
            
            # Process in chunks
            for chunk_start in range(0, len(df_full), chunk_size):
                chunk_end = min(chunk_start + chunk_size, len(df_full))
                df = df_full.iloc[chunk_start:chunk_end]
                
                inserted, dups = await _process_chunk(
                    db, df, file_id, actual_platform, account, is_base, master_skus, filename, batch_size
                )
                rows_inserted += inserted
                duplicates += dups
                
                # Update progress
                await db.orderhub_uploads.update_one({"id": file_id}, {"$set": {
                    "rows_processed": chunk_end,
                    "rows_inserted": rows_inserted,
                    "duplicates_skipped": duplicates
                }})
        else:
            # CSV files - use chunked reading for memory efficiency
            first_chunk = True
            detection = None
            
            for df_chunk in pd.read_csv(file_path, chunksize=chunk_size, encoding='utf-8', on_bad_lines='skip'):
                if first_chunk:
                    detection = detect_columns(df_chunk, actual_platform, filename)
                    first_chunk = False
                
                total_rows += len(df_chunk)
                
                inserted, dups = await _process_chunk(
                    db, df_chunk, file_id, actual_platform, account, is_base, master_skus, filename, batch_size, detection
                )
                rows_inserted += inserted
                duplicates += dups
                
                # Update progress
                await db.orderhub_uploads.update_one({"id": file_id}, {"$set": {
                    "rows_processed": total_rows,
                    "rows_inserted": rows_inserted,
                    "duplicates_skipped": duplicates
                }})
        
        processing_time = round(time.time() - start_time, 2)
        
        await db.orderhub_uploads.update_one({"id": file_id}, {"$set": {
            "status": "completed", 
            "platform": actual_platform if not is_base else "MIXED",
            "total_rows": total_rows, 
            "rows_inserted": rows_inserted, 
            "duplicates_skipped": duplicates,
            "processing_time_seconds": processing_time,
            "row_limit_applied": False,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }})
        
    except Exception as e:
        await db.orderhub_uploads.update_one({"id": file_id}, {"$set": {
            "status": "failed", 
            "errors": [str(e)],
            "row_limit_applied": False
        }})


async def _process_chunk(db, df, file_id: str, platform: str, account: str, is_base: bool, master_skus: dict, filename: str, batch_size: int, detection=None):
    """Process a single chunk of data with bulk insert."""
    
    if detection is None:
        detection = detect_columns(df, platform, filename)
    
    cols = detection["columns"]
    use_msku = detection.get("use_msku_extraction", False)
    
    sku_col = cols.get("sku")
    if not sku_col:
        for col in df.columns:
            if df[col].dtype == object:
                sku_col = col
                break
    
    if not sku_col:
        return 0, 0
    
    rows_inserted = 0
    duplicates = 0
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
            
            row_platform = platform
            if is_base and cols.get("order_source"):
                src = row.get(cols.get("order_source"))
                row_platform = detect_platform_from_order_source(src)["platform"]
            
            row_hash = generate_row_hash({"date": order_date.isoformat(), "sku": sku, "amount": amount}, row_platform, account)
            
            # Check for duplicate
            existing = await db.orderhub_orders.find_one({"row_hash": row_hash})
            if existing:
                duplicates += 1
                continue
            
            master_sku = master_skus.get(sku.lower(), "UNMAPPED")
            if master_sku == "UNMAPPED":
                await update_unmapped_sku(db, sku, row_platform, qty, amount, filename, master_skus)
            
            parts = split_master_sku(master_sku)
            orders_batch.append({
                "id": str(uuid.uuid4()), 
                "order_date": order_date.isoformat(), 
                "sku": sku,
                "master_sku": master_sku, 
                **parts, 
                "qty": qty, 
                "amount": amount, 
                "state": state,
                "platform": row_platform, 
                "account": account, 
                "file_id": file_id,
                "row_hash": row_hash, 
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            rows_inserted += 1
            
            # Bulk insert when batch is full
            if len(orders_batch) >= batch_size:
                await db.orderhub_orders.insert_many(orders_batch)
                orders_batch = []
                
        except Exception:
            continue
    
    # Insert remaining batch
    if orders_batch:
        await db.orderhub_orders.insert_many(orders_batch)
    
    return rows_inserted, duplicates


# Keep old function for backward compatibility
async def process_order_file(db, file_id: str, platform: str, account: str, file_path: Path):
    """Backward compatible wrapper."""
    await process_order_file_chunked(db, file_id, platform, account, file_path, 5000, 1000)
