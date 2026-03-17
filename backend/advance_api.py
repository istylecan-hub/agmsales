# Advance Management API
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import re

router = APIRouter(prefix="/api/advance", tags=["advance"])

# Will be set from server.py
db = None
read_sheet_data = None

def set_db(database):
    global db
    db = database

def set_sheet_reader(reader_func):
    global read_sheet_data
    read_sheet_data = reader_func

def normalize_name(name: str) -> str:
    """Normalize name for comparison"""
    if not name:
        return ""
    return re.sub(r'\s+', ' ', name.strip().lower())

def normalize_code(code) -> str:
    """Normalize employee code for comparison"""
    if not code:
        return ""
    return str(code).strip().lstrip('0')

@router.get("/list")
async def list_advances():
    """Get all synced advances"""
    advances = await db.salary_advances.find(
        {},
        {"_id": 0}
    ).sort("date", -1).to_list(500)
    
    # Get stats
    total = len(advances)
    matched = len([a for a in advances if a.get("syncStatus") == "Done"])
    pending = len([a for a in advances if a.get("syncStatus") == "Pending"])
    errors = len([a for a in advances if a.get("syncStatus") == "Error"])
    
    # Get last sync time
    last_sync_doc = await db.sync_logs.find_one(
        {"type": "advance"},
        sort=[("timestamp", -1)]
    )
    last_sync = last_sync_doc.get("timestamp") if last_sync_doc else None
    
    return {
        "advances": advances,
        "stats": {
            "total": total,
            "matched": matched,
            "pending": pending,
            "errors": errors
        },
        "lastSync": last_sync
    }

@router.post("/sync")
async def sync_advances():
    """Sync advances from Google Sheet"""
    try:
        # Get sheet config
        config = await db.sheet_config.find_one({"type": "advance"})
        if not config or not config.get("spreadsheetId"):
            raise HTTPException(status_code=400, detail="Sheet not configured")
        
        spreadsheet_id = config["spreadsheetId"]
        sheet_name = config.get("sheetName", "Sheet1")
        range_name = config.get("range", "A:F")
        full_range = f"{sheet_name}!{range_name}"
        
        # Read data from sheet
        rows = await read_sheet_data(spreadsheet_id, full_range)
        
        if not rows or len(rows) < 2:
            return {"success": True, "message": "No data found in sheet", "matched": 0, "errors": 0}
        
        # Get header row
        headers = [h.strip().lower() for h in rows[0]]
        
        # Find column indices
        date_idx = next((i for i, h in enumerate(headers) if 'date' in h), 0)
        name_idx = next((i for i, h in enumerate(headers) if 'name' in h), 1)
        advance_idx = next((i for i, h in enumerate(headers) if 'advance' in h or 'amount' in h), 2)
        code_idx = next((i for i, h in enumerate(headers) if 'no' in h or 'code' in h or 'emp' in h), 3)
        type_idx = next((i for i, h in enumerate(headers) if 'type' in h), 4)
        status_idx = next((i for i, h in enumerate(headers) if 'status' in h or 'sync' in h), 5)
        
        # Get all employees for matching
        employees = await db.employees.find({}, {"_id": 0, "code": 1, "name": 1}).to_list(1000)
        emp_map = {}
        for emp in employees:
            key = f"{normalize_code(emp['code'])}_{normalize_name(emp['name'])}"
            emp_map[key] = emp
            # Also map by code only
            emp_map[normalize_code(emp['code'])] = emp
        
        matched = 0
        errors = 0
        processed = []
        
        # Process data rows
        for row_idx, row in enumerate(rows[1:], start=2):
            try:
                # Pad row if needed
                while len(row) <= max(date_idx, name_idx, advance_idx, code_idx, type_idx, status_idx):
                    row.append("")
                
                date_val = row[date_idx] if date_idx < len(row) else ""
                name_val = row[name_idx] if name_idx < len(row) else ""
                advance_val = row[advance_idx] if advance_idx < len(row) else ""
                code_val = row[code_idx] if code_idx < len(row) else ""
                type_val = row[type_idx] if type_idx < len(row) else ""
                
                # Skip if not "Salary" type (case-insensitive)
                if type_val.strip().lower() != "salary":
                    continue
                
                # Validate required fields
                if not name_val or not code_val:
                    errors += 1
                    continue
                
                # Parse amount
                try:
                    amount = float(re.sub(r'[^\d.]', '', str(advance_val)))
                    if amount <= 0:
                        errors += 1
                        continue
                except Exception:
                    errors += 1
                    continue
                
                # Match employee - both name AND code must match
                norm_code = normalize_code(code_val)
                norm_name = normalize_name(name_val)
                match_key = f"{norm_code}_{norm_name}"
                
                emp_match = emp_map.get(match_key)
                
                if not emp_match:
                    # Try matching by code only as fallback
                    emp_by_code = emp_map.get(norm_code)
                    if emp_by_code:
                        # Code matches but name doesn't - reject
                        if normalize_name(emp_by_code['name']) != norm_name:
                            errors += 1
                            continue
                        emp_match = emp_by_code
                    else:
                        errors += 1
                        continue
                
                # Check for duplicate
                existing = await db.salary_advances.find_one({
                    "date": date_val,
                    "employeeCode": norm_code,
                    "amount": amount
                })
                
                if existing:
                    continue  # Skip duplicate
                
                # Insert advance record
                advance_record = {
                    "date": date_val,
                    "name": emp_match['name'],
                    "employeeCode": emp_match['code'],
                    "amount": amount,
                    "type": "Salary",
                    "syncStatus": "Done",
                    "sheetRow": row_idx,
                    "syncedAt": datetime.now(timezone.utc)
                }
                
                await db.salary_advances.insert_one(advance_record)
                matched += 1
                
                processed.append({
                    "date": date_val,
                    "name": emp_match['name'],
                    "employeeCode": emp_match['code'],
                    "amount": amount,
                    "syncStatus": "Done"
                })
                
            except Exception as e:
                errors += 1
                print(f"Error processing row {row_idx}: {e}")
        
        # Log sync
        await db.sync_logs.insert_one({
            "type": "advance",
            "timestamp": datetime.now(timezone.utc),
            "matched": matched,
            "errors": errors,
            "total_rows": len(rows) - 1
        })
        
        return {
            "success": True,
            "matched": matched,
            "errors": errors,
            "message": f"Synced {matched} advances, {errors} errors"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/employee/{employee_code}")
async def get_employee_advances(employee_code: str, month: Optional[int] = None, year: Optional[int] = None):
    """Get advances for a specific employee"""
    query = {"employeeCode": normalize_code(employee_code), "syncStatus": "Done"}
    
    advances = await db.salary_advances.find(
        query,
        {"_id": 0}
    ).sort("date", -1).to_list(100)
    
    # Filter by month/year if provided
    if month and year:
        filtered = []
        for adv in advances:
            try:
                # Parse date (try multiple formats)
                date_str = adv.get("date", "")
                adv_date = None
                for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"]:
                    try:
                        adv_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                
                if adv_date and adv_date.month == month and adv_date.year == year:
                    filtered.append(adv)
            except Exception:
                pass
        advances = filtered
    
    total = sum(adv.get("amount", 0) for adv in advances)
    
    return {
        "advances": advances,
        "total": total,
        "count": len(advances)
    }

@router.delete("/clear")
async def clear_advances():
    """Clear all advance records"""
    result = await db.salary_advances.delete_many({})
    return {"success": True, "deleted": result.deleted_count}
