"""OrderHub Master SKU API - NO artificial limits."""
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Query, HTTPException

router = APIRouter(prefix="/orderhub/master-skus", tags=["OrderHub Master SKUs"])

db = None

def set_db(database):
    global db
    db = database


@router.get("")
async def get_master_skus(search: Optional[str] = None, limit: int = Query(default=1000, le=50000)):
    """Get master SKUs - increased limit to 50000"""
    if db is None:
        return []
    query = {}
    if search:
        query["$or"] = [
            {"sku": {"$regex": search, "$options": "i"}},
            {"master_sku": {"$regex": search, "$options": "i"}}
        ]
    return await db.orderhub_master_skus.find(query, {"_id": 0}).to_list(limit)


@router.get("/count")
async def get_master_sku_count():
    """Get total count of master SKUs"""
    if db is None:
        return {"count": 0}
    count = await db.orderhub_master_skus.count_documents({})
    return {"count": count}


@router.post("")
async def create_master_sku(sku: str = Query(...), master_sku: str = Query(...), product_name: Optional[str] = None):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    existing = await db.orderhub_master_skus.find_one({"sku": sku}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="SKU already exists")
    
    record = {
        "id": str(uuid.uuid4()), "sku": sku, "master_sku": master_sku,
        "product_name": product_name or "", "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.orderhub_master_skus.insert_one(record)
    return {"id": record["id"], "message": "Created"}


@router.put("/{sku}")
async def update_master_sku(sku: str, master_sku: str = Query(...)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    result = await db.orderhub_master_skus.update_one({"sku": sku}, {"$set": {"master_sku": master_sku}})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Updated"}


@router.delete("/{sku_id}")
async def delete_master_sku(sku_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    result = await db.orderhub_master_skus.delete_one({"id": sku_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Deleted"}


@router.post("/bulk-delete")
async def bulk_delete_master_skus(sku_ids: list = Query(...)):
    """Bulk delete master SKUs"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    result = await db.orderhub_master_skus.delete_many({"id": {"$in": sku_ids}})
    return {"deleted": result.deleted_count}
