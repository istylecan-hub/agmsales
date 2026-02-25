"""OrderHub Export API."""
import io
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import pandas as pd

router = APIRouter(prefix="/orderhub/export", tags=["OrderHub Export"])

db = None

def set_db(database):
    global db
    db = database


@router.get("/consolidated")
async def export_consolidated(start_date: Optional[str] = None, end_date: Optional[str] = None, platform: Optional[str] = None):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    match = {}
    if start_date:
        match["order_date"] = {"$gte": start_date}
    if end_date:
        match.setdefault("order_date", {})["$lte"] = end_date
    if platform:
        match["platform"] = platform
    
    orders = await db.orderhub_orders.find(match, {"_id": 0, "row_hash": 0}).to_list(100000)
    
    df = pd.DataFrame(orders) if orders else pd.DataFrame(columns=["order_date", "sku", "master_sku", "qty", "amount", "platform"])
    
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
                            headers={"Content-Disposition": "attachment; filename=orderhub_orders.csv"})
