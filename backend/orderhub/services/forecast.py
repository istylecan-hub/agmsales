"""Forecast and production planning engine."""
from typing import Dict, Any


def calculate_weighted_forecast(daily_data: list, forecast_days: int = 15) -> Dict[str, Any]:
    if not daily_data:
        return {"forecast_qty": 0, "forecast_revenue": 0, "trend": "STABLE", "weighted_daily_qty": 0, "weighted_daily_revenue": 0}
    
    sorted_data = sorted(daily_data, key=lambda x: x.get("date", ""))
    last_7 = sorted_data[-7:] if len(sorted_data) >= 7 else sorted_data
    prev_days = sorted_data[:-7] if len(sorted_data) > 7 else []
    
    last_7_qty = sum(d.get("total_qty", 0) for d in last_7)
    last_7_revenue = sum(d.get("total_revenue", 0) for d in last_7)
    last_7_days_count = len(last_7) or 1
    
    prev_qty = sum(d.get("total_qty", 0) for d in prev_days)
    prev_revenue = sum(d.get("total_revenue", 0) for d in prev_days)
    prev_days_count = len(prev_days) or 1
    
    last_7_daily_qty = last_7_qty / last_7_days_count
    last_7_daily_revenue = last_7_revenue / last_7_days_count
    prev_daily_qty = prev_qty / prev_days_count if prev_days else last_7_daily_qty
    prev_daily_revenue = prev_revenue / prev_days_count if prev_days else last_7_daily_revenue
    
    weighted_daily_qty = (last_7_daily_qty * 0.6) + (prev_daily_qty * 0.4)
    weighted_daily_revenue = (last_7_daily_revenue * 0.6) + (prev_daily_revenue * 0.4)
    
    # Trend calculation
    trend = "STABLE"
    if len(sorted_data) >= 3:
        quantities = [d.get("total_qty", 0) for d in sorted_data[-14:]]
        n = len(quantities)
        if n > 1:
            x = list(range(n))
            sum_x, sum_y = sum(x), sum(quantities)
            sum_xy = sum(x[i] * quantities[i] for i in range(n))
            sum_x2 = sum(xi * xi for xi in x)
            denom = n * sum_x2 - sum_x * sum_x
            if denom != 0:
                slope = (n * sum_xy - sum_x * sum_y) / denom
                trend = "GROWING" if slope > 0.5 else "DECLINING" if slope < -0.5 else "STABLE"
    
    return {
        "forecast_qty": round(weighted_daily_qty * forecast_days),
        "forecast_revenue": round(weighted_daily_revenue * forecast_days, 2),
        "trend": trend,
        "weighted_daily_qty": round(weighted_daily_qty, 2),
        "weighted_daily_revenue": round(weighted_daily_revenue, 2)
    }


def get_production_recommendation(forecast_qty: int) -> str:
    if forecast_qty >= 25:
        return "PRODUCE_MORE"
    elif 10 <= forecast_qty < 25:
        return "NORMAL"
    elif 1 <= forecast_qty < 10:
        return "SLOW"
    return "STOP"
