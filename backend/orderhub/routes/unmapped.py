"""OrderHub Unmapped SKU API."""
import uuid
import io
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
import pandas as pd

router = APIRouter(prefix="/orderhub/unmapped", tags=["OrderHub Unmapped"])

db = None

def set_db(database):
    global db
    db = database


@router.get("/list")
async def get_unmapped(search: Optional[str] = None, platform: Optional[str] = None, status: Optional[str] = None, limit: int = Query(default=1000, le=50000)):
    if db is None:
        return []
    query = {}
    if search:
        query["sku"] = {"$regex": search, "$options": "i"}
    if platform:
        query["platform"] = platform
    if status:
        query["status"] = status
    return await db.orderhub_unmapped_skus.find(query, {"_id": 0}).sort("total_revenue", -1).to_list(limit)


@router.get("/summary")
async def get_summary():
    if db is None:
        return {"total_unmapped_skus": 0, "total_unmapped_qty": 0, "total_unmapped_revenue": 0}
    
    pipeline = [
        {"$match": {"status": "UNMAPPED"}},
        {"$group": {"_id": None, "count": {"$sum": 1}, "qty": {"$sum": "$total_qty"}, "revenue": {"$sum": "$total_revenue"}}}
    ]
    result = await db.orderhub_unmapped_skus.aggregate(pipeline).to_list(1)
    r = result[0] if result else {}
    return {
        "total_unmapped_skus": r.get("count", 0),
        "total_unmapped_qty": r.get("qty", 0),
        "total_unmapped_revenue": round(r.get("revenue", 0), 2)
    }


@router.get("/export")
async def export_unmapped(platform: Optional[str] = None):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    query = {"status": "UNMAPPED"}
    if platform:
        query["platform"] = platform
    
    skus = await db.orderhub_unmapped_skus.find(query, {"_id": 0}).sort("total_revenue", -1).to_list(10000)
    
    data = [{
        "sku": s.get("sku", ""), "master_sku": "", "platform": s.get("platform", ""),
        "total_qty": s.get("total_qty", 0), "total_revenue": round(s.get("total_revenue", 0), 2),
        "suggested_master_sku": s.get("suggested_master_sku", "")
    } for s in skus]
    
    df = pd.DataFrame(data)
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
                            headers={"Content-Disposition": "attachment; filename=unmapped_skus.csv"})


@router.post("/map-single")
async def map_single(sku: str = Query(...), master_sku: str = Query(...)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    from ..services.utils import split_master_sku
    
    unmapped = await db.orderhub_unmapped_skus.find_one({"sku": sku, "status": "UNMAPPED"}, {"_id": 0})
    if not unmapped:
        raise HTTPException(status_code=404, detail="Unmapped SKU not found")
    
    # Add to master SKUs
    existing = await db.orderhub_master_skus.find_one({"sku": sku}, {"_id": 0})
    if not existing:
        await db.orderhub_master_skus.insert_one({
            "id": str(uuid.uuid4()), "sku": sku, "master_sku": master_sku,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    else:
        await db.orderhub_master_skus.update_one({"sku": sku}, {"$set": {"master_sku": master_sku}})
    
    # Update unmapped status
    await db.orderhub_unmapped_skus.update_one({"sku": sku}, {"$set": {"status": "MAPPED", "mapped_master_sku": master_sku}})
    
    # Update orders
    parts = split_master_sku(master_sku)
    await db.orderhub_orders.update_many({"sku": sku, "master_sku": "UNMAPPED"}, {"$set": {"master_sku": master_sku, **parts}})
    
    return {"message": f"SKU '{sku}' mapped to '{master_sku}'"}


@router.post("/bulk-upload")
async def bulk_upload(file: UploadFile = File(...)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    from ..services.unmapped import remap_unmapped_skus
    
    content = await file.read()
    ext = file.filename.split(".")[-1].lower()
    
    try:
        df = pd.read_excel(io.BytesIO(content)) if ext in ["xlsx", "xls"] else pd.read_csv(io.BytesIO(content))
        
        sku_col, master_col = None, None
        for col in df.columns:
            cl = col.lower().strip()
            if cl in ["sku", "seller_sku"]:
                sku_col = col
            elif cl in ["master_sku", "master sku"]:
                master_col = col
        
        if not sku_col or not master_col:
            raise HTTPException(status_code=400, detail="Need 'sku' and 'master_sku' columns")
        
        count = 0
        for _, row in df.iterrows():
            sku = str(row[sku_col]).strip() if pd.notna(row[sku_col]) else ""
            master = str(row[master_col]).strip() if pd.notna(row[master_col]) else ""
            if not sku or not master:
                continue
            
            existing = await db.orderhub_master_skus.find_one({"sku": sku}, {"_id": 0})
            if existing:
                await db.orderhub_master_skus.update_one({"sku": sku}, {"$set": {"master_sku": master}})
            else:
                await db.orderhub_master_skus.insert_one({
                    "id": str(uuid.uuid4()), "sku": sku, "master_sku": master,
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
            count += 1
        
        remap = await remap_unmapped_skus(db)
        return {"mappings_processed": count, "remapped": remap["total_mapped_now"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
