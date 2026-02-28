"""OrderHub Admin API - Complete Reset Controls & Data Management."""
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException

router = APIRouter(prefix="/orderhub/admin", tags=["OrderHub Admin"])

db = None

def set_db(database):
    global db
    db = database


# ==================== PART 2: DATA RESET CONTROLS ====================

@router.post("/reset-orders")
async def reset_orders(confirm: bool = Query(default=False)):
    """
    Delete ALL Order Hub order data.
    Affects: orderhub_orders, orderhub_uploads, orderhub_unmapped_skus
    Does NOT affect: Master SKUs, Invoice Extractor, Salary Module
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    # PART 3: Safe mode - require confirmation
    if not confirm:
        return {
            "warning": "This will permanently delete ALL Order Hub order data. Other modules (Invoice Extractor, Salary) are NOT affected.",
            "action_required": "Set confirm=true to proceed",
            "tables_affected": ["orderhub_orders", "orderhub_uploads", "orderhub_unmapped_skus"],
            "tables_NOT_affected": ["orderhub_master_skus", "invoice_*", "salary_*", "employees", "jobs"]
        }
    
    # Get counts before deletion
    orders_count = await db.orderhub_orders.count_documents({})
    uploads_count = await db.orderhub_uploads.count_documents({})
    unmapped_count = await db.orderhub_unmapped_skus.count_documents({})
    
    # Delete order data ONLY (not master SKUs)
    await db.orderhub_orders.delete_many({})
    await db.orderhub_uploads.delete_many({})
    await db.orderhub_unmapped_skus.delete_many({})
    
    return {
        "status": "success",
        "message": "Order Hub order data reset complete",
        "deleted": {
            "orders": orders_count,
            "uploads": uploads_count,
            "unmapped_skus": unmapped_count
        },
        "preserved": {
            "master_skus": await db.orderhub_master_skus.count_documents({})
        },
        "other_modules_affected": False,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/reset-master")
async def reset_master_skus(confirm: bool = Query(default=False)):
    """
    Delete ALL Master SKU mappings.
    Sets all orders' master_sku to 'UNMAPPED'.
    Does NOT affect: Order data, Invoice Extractor, Salary Module
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    # PART 3: Safe mode - require confirmation
    if not confirm:
        return {
            "warning": "This will delete ALL Master SKU mappings. All orders will become UNMAPPED. Other modules are NOT affected.",
            "action_required": "Set confirm=true to proceed",
            "tables_affected": ["orderhub_master_skus"],
            "side_effects": ["All orders will have master_sku='UNMAPPED'"],
            "tables_NOT_affected": ["orderhub_orders (data preserved)", "invoice_*", "salary_*"]
        }
    
    # Get count before deletion
    master_count = await db.orderhub_master_skus.count_documents({})
    
    # Delete all master SKUs
    await db.orderhub_master_skus.delete_many({})
    
    # Update all orders to UNMAPPED
    orders_updated = await db.orderhub_orders.update_many(
        {},
        {"$set": {"master_sku": "UNMAPPED", "style_code": "", "color_code": "", "size_code": ""}}
    )
    
    # Recalculate unmapped SKUs
    from ..services.unmapped import rebuild_unmapped_from_orders
    unmapped_result = await rebuild_unmapped_from_orders(db)
    
    return {
        "status": "success",
        "message": "Master SKU data reset complete",
        "deleted": {
            "master_skus": master_count
        },
        "orders_reset_to_unmapped": orders_updated.modified_count,
        "unmapped_skus_created": unmapped_result.get("created", 0),
        "other_modules_affected": False,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/delete-upload/{file_id}")
async def delete_specific_upload(file_id: str, confirm: bool = Query(default=False)):
    """
    Delete data from a specific upload only.
    Does NOT affect: Other uploads, Master SKUs, Invoice Extractor, Salary Module
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    # Find the upload
    file_doc = await db.orderhub_uploads.find_one({"id": file_id}, {"_id": 0})
    if not file_doc:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    # PART 3: Safe mode - require confirmation
    if not confirm:
        # Get count of orders from this upload
        orders_count = await db.orderhub_orders.count_documents({"file_id": file_id})
        
        return {
            "warning": f"This will delete upload '{file_doc.get('original_filename')}' and {orders_count} associated orders.",
            "action_required": "Set confirm=true to proceed",
            "upload_details": {
                "file_id": file_id,
                "filename": file_doc.get("original_filename"),
                "platform": file_doc.get("platform"),
                "orders_to_delete": orders_count
            },
            "other_modules_affected": False
        }
    
    # Delete orders from this upload
    orders_deleted = await db.orderhub_orders.delete_many({"file_id": file_id})
    
    # Delete the upload record
    await db.orderhub_uploads.delete_one({"id": file_id})
    
    # Recalculate unmapped SKUs
    from ..services.unmapped import refresh_unmapped_counts
    await refresh_unmapped_counts(db)
    
    return {
        "status": "success",
        "message": f"Upload '{file_doc.get('original_filename')}' deleted",
        "deleted": {
            "orders": orders_deleted.deleted_count,
            "upload_record": 1
        },
        "file_id": file_id,
        "other_modules_affected": False,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.delete("/reset-all")
async def reset_all_orderhub(confirm: str = Query(...)):
    """
    COMPLETE RESET - Delete ALL Order Hub data.
    Affects: Orders, Uploads, Unmapped SKUs, Master SKUs
    Does NOT affect: Invoice Extractor, Salary Module
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    if confirm != "CONFIRM_DELETE_ALL":
        return {
            "warning": "This will PERMANENTLY delete ALL Order Hub data including Master SKUs.",
            "action_required": "Set confirm=CONFIRM_DELETE_ALL to proceed",
            "tables_affected": ["orderhub_orders", "orderhub_uploads", "orderhub_unmapped_skus", "orderhub_master_skus"],
            "tables_NOT_affected": ["invoice_*", "salary_*", "employees", "jobs", "job_files"]
        }
    
    # Get counts
    orders = await db.orderhub_orders.count_documents({})
    files = await db.orderhub_uploads.count_documents({})
    unmapped = await db.orderhub_unmapped_skus.count_documents({})
    master = await db.orderhub_master_skus.count_documents({})
    
    # Delete ALL Order Hub data
    await db.orderhub_orders.delete_many({})
    await db.orderhub_uploads.delete_many({})
    await db.orderhub_unmapped_skus.delete_many({})
    await db.orderhub_master_skus.delete_many({})
    
    return {
        "status": "success",
        "message": "Complete Order Hub reset done",
        "deleted": {
            "orders": orders,
            "uploads": files,
            "unmapped_skus": unmapped,
            "master_skus": master
        },
        "other_modules_affected": False,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ==================== EXISTING ENDPOINTS ====================

@router.delete("/delete-file/{file_id}")
async def delete_file(file_id: str):
    """Legacy endpoint - use /delete-upload/{file_id} with confirm=true instead"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    file_doc = await db.orderhub_uploads.find_one({"id": file_id}, {"_id": 0})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    orders_deleted = await db.orderhub_orders.delete_many({"file_id": file_id})
    await db.orderhub_uploads.delete_one({"id": file_id})
    
    return {"message": f"Deleted {orders_deleted.deleted_count} orders", "file_id": file_id}


@router.delete("/delete-by-date-range")
async def delete_by_date(start_date: str = Query(...), end_date: str = Query(...), platform: Optional[str] = None, confirm: bool = Query(default=False)):
    """Delete orders by date range."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    query = {"order_date": {"$gte": start_date, "$lte": end_date}}
    if platform:
        query["platform"] = platform
    
    if not confirm:
        count = await db.orderhub_orders.count_documents(query)
        return {
            "warning": f"This will delete {count} orders from {start_date} to {end_date}",
            "action_required": "Set confirm=true to proceed"
        }
    
    result = await db.orderhub_orders.delete_many(query)
    return {"message": f"Deleted {result.deleted_count} orders", "other_modules_affected": False}


@router.get("/data-summary")
async def data_summary():
    """Get Order Hub data summary."""
    if db is None:
        return {"total_orders": 0, "total_files": 0, "unmapped_skus": 0, "master_skus": 0, "files": []}
    
    orders = await db.orderhub_orders.count_documents({})
    files_count = await db.orderhub_uploads.count_documents({})
    unmapped = await db.orderhub_unmapped_skus.count_documents({"status": "UNMAPPED"})
    master = await db.orderhub_master_skus.count_documents({})
    
    files = await db.orderhub_uploads.find({}, {"_id": 0, "id": 1, "original_filename": 1, "platform": 1, "rows_inserted": 1, "created_at": 1, "status": 1}).sort("created_at", -1).to_list(500)
    
    return {
        "total_orders": orders, 
        "total_files": files_count, 
        "unmapped_skus": unmapped, 
        "master_skus": master, 
        "files": files,
        "artificial_row_limit": False
    }


@router.post("/remap-unmapped")
async def remap_unmapped():
    """Remap unmapped SKUs using current master SKU list."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    from ..services.unmapped import remap_unmapped_skus
    result = await remap_unmapped_skus(db)
    return result
