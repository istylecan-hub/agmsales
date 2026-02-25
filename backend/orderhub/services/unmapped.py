"""Unmapped SKU management service."""
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional
from difflib import SequenceMatcher
import re
from .utils import split_master_sku


def normalize_sku_for_matching(sku: str) -> str:
    return re.sub(r'[^a-z0-9]', '', sku.lower()) if sku else ""


def calculate_sku_similarity(sku1: str, sku2: str) -> float:
    norm1, norm2 = normalize_sku_for_matching(sku1), normalize_sku_for_matching(sku2)
    if not norm1 or not norm2:
        return 0.0
    if norm1 == norm2:
        return 100.0
    if norm1 in norm2 or norm2 in norm1:
        return 90.0
    set1, set2 = set(norm1), set(norm2)
    char_sim = (len(set1 & set2) / len(set1 | set2) * 100) if set1 | set2 else 0
    seq_sim = SequenceMatcher(None, norm1, norm2).ratio() * 100
    return char_sim * 0.3 + seq_sim * 0.7


async def find_fuzzy_match(sku: str, master_skus: dict, threshold: float = 90.0) -> Optional[Dict]:
    if not sku or not master_skus:
        return None
    best_match, best_score = None, 0
    for key, value in master_skus.items():
        sim = calculate_sku_similarity(sku, key)
        if sim >= threshold and sim > best_score:
            best_score = sim
            best_match = {"matched_sku": key, "master_sku": value, "confidence": round(sim, 1)}
    return best_match


async def update_unmapped_sku(db, sku: str, platform: str, qty: int, amount: float, filename: str, master_skus: dict = None):
    now = datetime.now(timezone.utc).isoformat()
    existing = await db.orderhub_unmapped_skus.find_one({"sku": sku, "platform": platform}, {"_id": 0})
    
    if existing:
        await db.orderhub_unmapped_skus.update_one(
            {"sku": sku, "platform": platform},
            {"$inc": {"total_qty": qty, "total_revenue": amount}, "$set": {"last_seen_at": now}}
        )
    else:
        suggested = await find_fuzzy_match(sku, master_skus) if master_skus else None
        await db.orderhub_unmapped_skus.insert_one({
            "id": str(uuid.uuid4()), "sku": sku, "platform": platform,
            "first_seen_at": now, "last_seen_at": now,
            "total_qty": qty, "total_revenue": amount, "file_name": filename,
            "status": "UNMAPPED", "mapped_master_sku": None,
            "suggested_master_sku": suggested["master_sku"] if suggested else None,
            "suggestion_confidence": suggested["confidence"] if suggested else None
        })


async def remap_unmapped_skus(db) -> Dict[str, int]:
    master_skus = {doc["sku"].lower(): doc["master_sku"] async for doc in db.orderhub_master_skus.find({}, {"_id": 0})}
    total_unmapped, total_mapped = 0, 0
    
    async for unmapped in db.orderhub_unmapped_skus.find({"status": "UNMAPPED"}, {"_id": 0}):
        total_unmapped += 1
        sku_lower = unmapped["sku"].lower()
        if sku_lower in master_skus:
            master_val = master_skus[sku_lower]
            parts = split_master_sku(master_val)
            await db.orderhub_unmapped_skus.update_one({"id": unmapped["id"]}, {"$set": {"status": "MAPPED", "mapped_master_sku": master_val}})
            await db.orderhub_orders.update_many({"sku": unmapped["sku"], "master_sku": "UNMAPPED"}, {"$set": {"master_sku": master_val, **parts}})
            total_mapped += 1
    
    return {"total_unmapped": total_unmapped, "total_mapped_now": total_mapped, "remaining_unmapped": total_unmapped - total_mapped}
