"""OrderHub Dashboard API."""
import calendar
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Query

router = APIRouter(prefix="/orderhub/dashboard", tags=["OrderHub Dashboard"])

db = None

def set_db(database):
    global db
    db = database


@router.get("/summary")
async def get_summary(start_date: Optional[str] = None, end_date: Optional[str] = None, platform: Optional[str] = None):
    if db is None:
        return {"total_orders": 0, "total_revenue": 0, "unique_skus": 0, "platforms_count": 0, "unmapped_skus": 0, "files_uploaded": 0}
    
    match = {}
    if start_date:
        match["order_date"] = {"$gte": start_date}
    if end_date:
        match.setdefault("order_date", {})["$lte"] = end_date
    if platform:
        match["platform"] = platform
    
    pipeline = [{"$match": match}, {"$group": {
        "_id": None, "total_orders": {"$sum": "$qty"}, "total_revenue": {"$sum": "$amount"},
        "unique_skus": {"$addToSet": "$sku"}, "unique_platforms": {"$addToSet": "$platform"}
    }}]
    
    result = await db.orderhub_orders.aggregate(pipeline).to_list(1)
    stats = result[0] if result else {}
    
    unmapped = await db.orderhub_orders.count_documents({"master_sku": "UNMAPPED"})
    files = await db.orderhub_uploads.count_documents({})
    
    return {
        "total_orders": stats.get("total_orders", 0),
        "total_revenue": round(stats.get("total_revenue", 0), 2),
        "unique_skus": len(stats.get("unique_skus", [])),
        "platforms_count": len(stats.get("unique_platforms", [])),
        "unmapped_skus": unmapped,
        "files_uploaded": files
    }


@router.get("/enterprise-summary")
async def get_enterprise_summary(start_date: Optional[str] = None, end_date: Optional[str] = None, platform: Optional[str] = None):
    if db is None:
        return {}
    
    match = {}
    if start_date:
        match["order_date"] = {"$gte": start_date}
    if end_date:
        match.setdefault("order_date", {})["$lte"] = end_date
    if platform:
        match["platform"] = platform
    
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    month_start = now.replace(day=1).strftime("%Y-%m-%d")
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    days_passed = now.day
    seven_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    fourteen_ago = (now - timedelta(days=14)).strftime("%Y-%m-%d")
    
    # Total
    total_pipe = [{"$match": match}, {"$group": {"_id": None, "orders": {"$sum": "$qty"}, "revenue": {"$sum": "$amount"}, "count": {"$sum": 1}}}]
    total = (await db.orderhub_orders.aggregate(total_pipe).to_list(1)) or [{}]
    total = total[0]
    
    # Today
    today_pipe = [{"$match": {"order_date": {"$regex": f"^{today}"}}}, {"$group": {"_id": None, "orders": {"$sum": "$qty"}, "revenue": {"$sum": "$amount"}}}]
    today_r = (await db.orderhub_orders.aggregate(today_pipe).to_list(1)) or [{}]
    today_r = today_r[0]
    
    # Growth
    last7_pipe = [{"$match": {"order_date": {"$gte": seven_ago}}}, {"$group": {"_id": None, "revenue": {"$sum": "$amount"}}}]
    last7 = (await db.orderhub_orders.aggregate(last7_pipe).to_list(1)) or [{}]
    prev7_pipe = [{"$match": {"order_date": {"$gte": fourteen_ago, "$lt": seven_ago}}}, {"$group": {"_id": None, "revenue": {"$sum": "$amount"}}}]
    prev7 = (await db.orderhub_orders.aggregate(prev7_pipe).to_list(1)) or [{}]
    growth = round(((last7[0].get("revenue", 0) - prev7[0].get("revenue", 0)) / prev7[0].get("revenue", 1)) * 100, 1) if prev7[0].get("revenue") else 0
    
    # Monthly projection
    month_pipe = [{"$match": {"order_date": {"$gte": month_start}}}, {"$group": {"_id": None, "revenue": {"$sum": "$amount"}}}]
    month_r = (await db.orderhub_orders.aggregate(month_pipe).to_list(1)) or [{}]
    projected = round((month_r[0].get("revenue", 0) / days_passed) * days_in_month, 2) if days_passed > 0 else 0
    
    # Top SKU
    top_sku_pipe = [{"$match": match}, {"$group": {"_id": "$sku", "qty": {"$sum": "$qty"}, "revenue": {"$sum": "$amount"}}}, {"$sort": {"revenue": -1}}, {"$limit": 1}]
    top_sku = (await db.orderhub_orders.aggregate(top_sku_pipe).to_list(1)) or [{}]
    
    # Top Platform
    top_plat_pipe = [{"$match": match}, {"$group": {"_id": "$platform", "qty": {"$sum": "$qty"}, "revenue": {"$sum": "$amount"}}}, {"$sort": {"revenue": -1}}, {"$limit": 1}]
    top_plat = (await db.orderhub_orders.aggregate(top_plat_pipe).to_list(1)) or [{}]
    
    unmapped = await db.orderhub_orders.count_documents({"master_sku": "UNMAPPED"})
    
    return {
        "total_orders": total.get("orders", 0),
        "total_revenue": round(total.get("revenue", 0), 2),
        "avg_order_value": round(total.get("revenue", 0) / total.get("count", 1), 2) if total.get("count") else 0,
        "today_orders": today_r.get("orders", 0),
        "today_revenue": round(today_r.get("revenue", 0), 2),
        "growth_7_days_percent": growth,
        "projected_monthly_sales": projected,
        "top_selling_sku": {"sku": top_sku[0].get("_id"), "qty": top_sku[0].get("qty", 0), "revenue": round(top_sku[0].get("revenue", 0), 2)} if top_sku[0].get("_id") else None,
        "top_platform": {"platform": top_plat[0].get("_id"), "qty": top_plat[0].get("qty", 0), "revenue": round(top_plat[0].get("revenue", 0), 2)} if top_plat[0].get("_id") else None,
        "unmapped_sku_count": unmapped
    }
