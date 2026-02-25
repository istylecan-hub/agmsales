"""OrderHub Admin API."""
from typing import Optional
from fastapi import APIRouter, Query, HTTPException

router = APIRouter(prefix="/orderhub/admin", tags=["OrderHub Admin"])

db = None

def set_db(database):
    global db
    db = database


@router.delete("/delete-file/{file_id}")
async def delete_file(file_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    file_doc = await db.orderhub_uploads.find_one({"id": file_id}, {"_id": 0})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    orders_deleted = await db.orderhub_orders.delete_many({"file_id": file_id})
    await db.orderhub_uploads.delete_one({"id": file_id})
    
    return {"message": f"Deleted {orders_deleted.deleted_count} orders", "file_id": file_id}


@router.delete("/delete-by-date-range")
async def delete_by_date(start_date: str = Query(...), end_date: str = Query(...), platform: Optional[str] = None):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    query = {"order_date": {"$gte": start_date, "$lte": end_date}}
    if platform:
        query["platform"] = platform
    
    result = await db.orderhub_orders.delete_many(query)
    return {"message": f"Deleted {result.deleted_count} orders"}


@router.delete("/reset-all")
async def reset_all(confirm: str = Query(...)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    if confirm != "CONFIRM":
        raise HTTPException(status_code=400, detail="Type 'CONFIRM' to reset")
    
    orders = await db.orderhub_orders.count_documents({})
    files = await db.orderhub_uploads.count_documents({})
    unmapped = await db.orderhub_unmapped_skus.count_documents({})
    master = await db.orderhub_master_skus.count_documents({})
    
    await db.orderhub_orders.delete_many({})
    await db.orderhub_uploads.delete_many({})
    await db.orderhub_unmapped_skus.delete_many({})
    await db.orderhub_master_skus.delete_many({})
    
    return {"message": "Reset complete", "deleted": {"orders": orders, "files": files, "unmapped": unmapped, "master_skus": master}}


@router.get("/data-summary")
async def data_summary():
    if db is None:
        return {"total_orders": 0, "total_files": 0, "unmapped_skus": 0, "master_skus": 0, "files": []}
    
    orders = await db.orderhub_orders.count_documents({})
    files_count = await db.orderhub_uploads.count_documents({})
    unmapped = await db.orderhub_unmapped_skus.count_documents({"status": "UNMAPPED"})
    master = await db.orderhub_master_skus.count_documents({})
    
    files = await db.orderhub_uploads.find({}, {"_id": 0, "id": 1, "original_filename": 1, "platform": 1, "rows_inserted": 1, "created_at": 1, "status": 1}).sort("created_at", -1).to_list(100)
    
    return {"total_orders": orders, "total_files": files_count, "unmapped_skus": unmapped, "master_skus": master, "files": files}


@router.post("/remap-unmapped")
async def remap_unmapped():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    from ..services.unmapped import remap_unmapped_skus
    result = await remap_unmapped_skus(db)
    return result
