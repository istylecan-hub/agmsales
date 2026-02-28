"""OrderHub Upload API - Enhanced with no limits, chunked processing, bulk insert."""
import uuid
import asyncio
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
import pandas as pd
import io

router = APIRouter(prefix="/orderhub/upload", tags=["OrderHub Upload"])

# Configuration - NO ARTIFICIAL LIMITS
MAX_UPLOAD_SIZE_MB = 100  # 100MB max
CHUNK_SIZE = 5000  # Process 5000 rows at a time
BATCH_INSERT_SIZE = 1000  # Bulk insert batch size

# Will be set from server.py
db = None
UPLOAD_DIR = None

def set_db(database, upload_dir):
    global db, UPLOAD_DIR
    db = database
    UPLOAD_DIR = upload_dir


@router.post("/orders")
async def upload_orders(file: UploadFile = File(...), platform: str = Query(...), account: str = Query(default="")):
    """Upload order file - NO ROW LIMITS, chunked processing"""
    from ..services.file_processor import process_order_file_chunked
    
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    allowed = [".xlsx", ".xls", ".csv"]
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid file. Allowed: {allowed}")
    
    file_id = str(uuid.uuid4())
    saved_name = f"{file_id}{file_ext}"
    file_path = UPLOAD_DIR / saved_name
    
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    
    if file_size_mb > MAX_UPLOAD_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"File too large. Max {MAX_UPLOAD_SIZE_MB}MB, got {file_size_mb:.2f}MB")
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    await db.orderhub_uploads.insert_one({
        "id": file_id, 
        "filename": saved_name, 
        "original_filename": file.filename,
        "platform": platform, 
        "account": account, 
        "status": "pending",
        "file_size_mb": round(file_size_mb, 2),
        "rows_processed": 0, 
        "rows_inserted": 0, 
        "duplicates_skipped": 0,
        "errors": [],
        "row_limit_applied": False,  # NO ARTIFICIAL LIMIT
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Process in background with chunked processing
    asyncio.create_task(process_order_file_chunked(db, file_id, platform, account, file_path, CHUNK_SIZE, BATCH_INSERT_SIZE))
    
    return {
        "file_id": file_id, 
        "status": "pending", 
        "message": "Processing started",
        "file_size_mb": round(file_size_mb, 2),
        "chunk_size": CHUNK_SIZE,
        "batch_size": BATCH_INSERT_SIZE,
        "row_limit_applied": False
    }


@router.post("/master-sku")
async def upload_master_sku(file: UploadFile = File(...)):
    """Upload Master SKU file - NO ROW LIMITS, bulk processing"""
    from ..services.unmapped import remap_unmapped_skus
    
    start_time = time.time()
    
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    
    if file_size_mb > MAX_UPLOAD_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"File too large. Max {MAX_UPLOAD_SIZE_MB}MB")
    
    file_ext = Path(file.filename).suffix.lower()
    
    try:
        # Read entire file - NO head(100) or limit
        if file_ext in [".xlsx", ".xls"]:
            df = pd.read_excel(io.BytesIO(content))
        else:
            df = pd.read_csv(io.BytesIO(content))
        
        total_rows_read = len(df)
        
        sku_col, master_col = None, None
        for col in df.columns:
            cl = col.lower().strip()
            if cl in ["sku", "seller_sku", "seller sku", "sellersku"]:
                sku_col = col
            elif cl in ["master_sku", "master sku", "mastersku", "msku"]:
                master_col = col
        
        if not sku_col or not master_col:
            raise HTTPException(status_code=400, detail="Need 'sku' and 'master_sku' columns")
        
        inserted, updated, skipped = 0, 0, 0
        
        # Process in batches for better performance
        batch_size = BATCH_INSERT_SIZE
        insert_batch = []
        
        for idx, row in df.iterrows():
            sku = str(row[sku_col]).strip() if pd.notna(row[sku_col]) else ""
            master = str(row[master_col]).strip() if pd.notna(row[master_col]) else ""
            
            if not sku or not master:
                skipped += 1
                continue
            
            existing = await db.orderhub_master_skus.find_one({"sku": sku}, {"_id": 0})
            if existing:
                await db.orderhub_master_skus.update_one({"sku": sku}, {"$set": {"master_sku": master}})
                updated += 1
            else:
                insert_batch.append({
                    "id": str(uuid.uuid4()), 
                    "sku": sku, 
                    "master_sku": master,
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
                inserted += 1
            
            # Bulk insert when batch is full
            if len(insert_batch) >= batch_size:
                await db.orderhub_master_skus.insert_many(insert_batch)
                insert_batch = []
        
        # Insert remaining batch
        if insert_batch:
            await db.orderhub_master_skus.insert_many(insert_batch)
        
        # Remap unmapped SKUs
        remap = await remap_unmapped_skus(db)
        
        processing_time = round(time.time() - start_time, 2)
        
        return {
            "total_rows_read": total_rows_read,
            "rows_inserted": inserted,
            "rows_updated": updated,
            "rows_skipped": skipped,
            "remapped": remap["total_mapped_now"],
            "processing_time_seconds": processing_time,
            "row_limit_applied": False  # NO ARTIFICIAL LIMIT
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status/{file_id}")
async def get_status(file_id: str):
    """Get upload status with detailed info"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    doc = await db.orderhub_uploads.find_one({"id": file_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return doc


@router.get("/list")
async def get_uploads(limit: int = Query(default=100, le=1000)):
    """Get list of uploads - increased limit to 1000"""
    if db is None:
        return []
    return await db.orderhub_uploads.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
