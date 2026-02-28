"""OrderHub Reports API."""
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Query

router = APIRouter(prefix="/orderhub/reports", tags=["OrderHub Reports"])

db = None

def set_db(database):
    global db
    db = database


@router.get("/sku")
async def report_by_sku(start_date: Optional[str] = None, end_date: Optional[str] = None, platform: Optional[str] = None, limit: int = Query(default=1000, le=50000)):
    if db is None:
        return []
    match = {}
    if start_date:
        match["order_date"] = {"$gte": start_date}
    if end_date:
        match.setdefault("order_date", {})["$lte"] = end_date
    if platform:
        match["platform"] = platform
    
    pipeline = [
        {"$match": match},
        {"$group": {"_id": "$sku", "total_qty": {"$sum": "$qty"}, "total_amount": {"$sum": "$amount"}, "master_sku": {"$first": "$master_sku"}, "platforms": {"$addToSet": "$platform"}}},
        {"$sort": {"total_amount": -1}}, {"$limit": limit},
        {"$project": {"_id": 0, "sku": "$_id", "master_sku": 1, "total_qty": 1, "total_amount": {"$round": ["$total_amount", 2]}, "platforms": 1}}
    ]
    return await db.orderhub_orders.aggregate(pipeline).to_list(limit)


@router.get("/master-sku")
async def report_by_master_sku(start_date: Optional[str] = None, end_date: Optional[str] = None, platform: Optional[str] = None, limit: int = Query(default=1000, le=50000)):
    if db is None:
        return []
    match = {}
    if start_date:
        match["order_date"] = {"$gte": start_date}
    if end_date:
        match.setdefault("order_date", {})["$lte"] = end_date
    if platform:
        match["platform"] = platform
    
    pipeline = [
        {"$match": match},
        {"$group": {"_id": "$master_sku", "total_qty": {"$sum": "$qty"}, "total_amount": {"$sum": "$amount"}, "skus": {"$addToSet": "$sku"}}},
        {"$sort": {"total_amount": -1}}, {"$limit": limit},
        {"$project": {"_id": 0, "master_sku": "$_id", "total_qty": 1, "total_amount": {"$round": ["$total_amount", 2]}, "sku_count": {"$size": "$skus"}}}
    ]
    return await db.orderhub_orders.aggregate(pipeline).to_list(limit)


@router.get("/platform")
async def report_by_platform(start_date: Optional[str] = None, end_date: Optional[str] = None):
    if db is None:
        return []
    match = {}
    if start_date:
        match["order_date"] = {"$gte": start_date}
    if end_date:
        match.setdefault("order_date", {})["$lte"] = end_date
    
    pipeline = [
        {"$match": match},
        {"$group": {"_id": "$platform", "total_qty": {"$sum": "$qty"}, "total_amount": {"$sum": "$amount"}}},
        {"$sort": {"total_amount": -1}},
        {"$project": {"_id": 0, "platform": "$_id", "total_qty": 1, "total_amount": {"$round": ["$total_amount", 2]}}}
    ]
    return await db.orderhub_orders.aggregate(pipeline).to_list(100)


@router.get("/state")
async def report_by_state(start_date: Optional[str] = None, end_date: Optional[str] = None, platform: Optional[str] = None):
    if db is None:
        return []
    match = {}
    if start_date:
        match["order_date"] = {"$gte": start_date}
    if end_date:
        match.setdefault("order_date", {})["$lte"] = end_date
    if platform:
        match["platform"] = platform
    
    pipeline = [
        {"$match": match},
        {"$group": {"_id": "$state", "total_qty": {"$sum": "$qty"}, "total_amount": {"$sum": "$amount"}}},
        {"$sort": {"total_amount": -1}},
        {"$project": {"_id": 0, "state": {"$ifNull": ["$_id", "Unknown"]}, "total_qty": 1, "total_amount": {"$round": ["$total_amount", 2]}}}
    ]
    return await db.orderhub_orders.aggregate(pipeline).to_list(100)


@router.get("/date-trend")
async def report_date_trend(start_date: Optional[str] = None, end_date: Optional[str] = None, platform: Optional[str] = None, group_by: str = Query(default="day")):
    if db is None:
        return []
    match = {}
    if start_date:
        match["order_date"] = {"$gte": start_date}
    if end_date:
        match.setdefault("order_date", {})["$lte"] = end_date
    if platform:
        match["platform"] = platform
    
    date_group = {"$substr": ["$order_date", 0, 7]} if group_by == "month" else {"$substr": ["$order_date", 0, 10]}
    
    pipeline = [
        {"$match": match},
        {"$group": {"_id": date_group, "total_qty": {"$sum": "$qty"}, "total_amount": {"$sum": "$amount"}}},
        {"$sort": {"_id": 1}},
        {"$project": {"_id": 0, "date": "$_id", "total_qty": 1, "total_amount": {"$round": ["$total_amount", 2]}}}
    ]
    return await db.orderhub_orders.aggregate(pipeline).to_list(365)
