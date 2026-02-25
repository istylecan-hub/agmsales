"""OrderHub Platforms & Forecast API."""
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter

router = APIRouter(prefix="/orderhub", tags=["OrderHub Platforms"])

db = None

DEFAULT_PLATFORMS = [
    {"name": "Meesho", "code": "meesho"},
    {"name": "Amazon", "code": "amazon"},
    {"name": "Flipkart", "code": "flipkart"},
    {"name": "Myntra", "code": "myntra"},
    {"name": "Ajio", "code": "ajio"},
    {"name": "Amazon Flex", "code": "amazon_flex"},
    {"name": "Base Orders", "code": "base"}
]

def set_db(database):
    global db
    db = database


@router.get("/platforms")
async def get_platforms():
    if db is None:
        return DEFAULT_PLATFORMS
    
    for p in DEFAULT_PLATFORMS:
        existing = await db.orderhub_platforms.find_one({"code": p["code"]}, {"_id": 0})
        if not existing:
            await db.orderhub_platforms.insert_one({
                "id": str(uuid.uuid4()), "name": p["name"], "code": p["code"],
                "created_at": datetime.now(timezone.utc).isoformat()
            })
    
    return await db.orderhub_platforms.find({}, {"_id": 0}).to_list(100)


@router.get("/forecast/production-plan")
async def get_production_plan():
    if db is None:
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "production_plan": []}
    
    from ..services.forecast import calculate_weighted_forecast, get_production_recommendation
    
    thirty_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    
    pipeline = [
        {"$match": {"order_date": {"$gte": thirty_ago}, "style_code": {"$ne": ""}}},
        {"$group": {
            "_id": {"date": {"$substr": ["$order_date", 0, 10]}, "style": "$style_code", "color": "$color_code", "size": "$size_code"},
            "qty": {"$sum": "$qty"}, "revenue": {"$sum": "$amount"}
        }},
        {"$sort": {"_id.date": 1}}
    ]
    
    daily_data = await db.orderhub_orders.aggregate(pipeline).to_list(None)
    
    sku_daily = {}
    for d in daily_data:
        key = (d["_id"]["style"], d["_id"]["color"], d["_id"]["size"])
        if key not in sku_daily:
            sku_daily[key] = []
        sku_daily[key].append({"date": d["_id"]["date"], "total_qty": d["qty"], "total_revenue": d["revenue"]})
    
    plan = []
    for (style, color, size), daily in sku_daily.items():
        forecast = calculate_weighted_forecast(daily, 15)
        plan.append({
            "style_code": style, "color_code": color, "size_code": size,
            "forecast_15_days_qty": forecast["forecast_qty"],
            "forecast_15_days_revenue": forecast["forecast_revenue"],
            "trend": forecast["trend"],
            "recommendation": get_production_recommendation(forecast["forecast_qty"])
        })
    
    plan.sort(key=lambda x: x["forecast_15_days_qty"], reverse=True)
    
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "total_items": len(plan), "production_plan": plan}
