"""OrderHub Upload API."""
import uuid
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
import pandas as pd
import io

router = APIRouter(prefix="/orderhub/upload", tags=["OrderHub Upload"])

# Will be set from server.py
db = None
UPLOAD_DIR = None

def set_db(database, upload_dir):
    global db, UPLOAD_DIR
    db = database
    UPLOAD_DIR = upload_dir


@router.post("/orders")
async def upload_orders(file: UploadFile = File(...), platform: str = Query(...), account: str = Query(default="")):
    from ..services.file_processor import process_order_file
    
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
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 100MB")
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    await db.orderhub_uploads.insert_one({
        "id": file_id, "filename": saved_name, "original_filename": file.filename,
        "platform": platform, "account": account, "status": "pending",
        "rows_processed": 0, "rows_inserted": 0, "errors": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    asyncio.create_task(process_order_file(db, file_id, platform, account, file_path))
    return {"file_id": file_id, "status": "pending", "message": "Processing started"}


@router.post("/master-sku")
async def upload_master_sku(file: UploadFile = File(...)):
    from ..services.unmapped import remap_unmapped_skus
    
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    content = await file.read()
    file_ext = Path(file.filename).suffix.lower()
    
    try:
        df = pd.read_excel(io.BytesIO(content)) if file_ext in [".xlsx", ".xls"] else pd.read_csv(io.BytesIO(content))
        
        sku_col, master_col = None, None
        for col in df.columns:
            cl = col.lower().strip()
            if cl in ["sku", "seller_sku", "seller sku"]:
                sku_col = col
            elif cl in ["master_sku", "master sku", "mastersku"]:
                master_col = col
        
        if not sku_col or not master_col:
            raise HTTPException(status_code=400, detail="Need 'sku' and 'master_sku' columns")
        
        inserted, updated = 0, 0
        for _, row in df.iterrows():
            sku = str(row[sku_col]).strip() if pd.notna(row[sku_col]) else ""
            master = str(row[master_col]).strip() if pd.notna(row[master_col]) else ""
            if not sku or not master:
                continue
            
            existing = await db.orderhub_master_skus.find_one({"sku": sku}, {"_id": 0})
            if existing:
                await db.orderhub_master_skus.update_one({"sku": sku}, {"$set": {"master_sku": master}})
                updated += 1
            else:
                await db.orderhub_master_skus.insert_one({
                    "id": str(uuid.uuid4()), "sku": sku, "master_sku": master,
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
                inserted += 1
        
        remap = await remap_unmapped_skus(db)
        return {"inserted": inserted, "updated": updated, "remapped": remap["total_mapped_now"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status/{file_id}")
async def get_status(file_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    doc = await db.orderhub_uploads.find_one({"id": file_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return doc


@router.get("/list")
async def get_uploads():
    if db is None:
        return []
    return await db.orderhub_uploads.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
