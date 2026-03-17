# Advance Management API - CSV/Excel Upload
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import pandas as pd
import io
import re
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/advance", tags=["advance"])

# Will be set from server.py
db = None

def set_db(database):
    global db
    db = database

def normalize_name(name: str) -> str:
    """Normalize name for comparison"""
    if not name:
        return ""
    return re.sub(r'\s+', ' ', str(name).strip().lower())

def normalize_code(code) -> str:
    """Normalize employee code for comparison"""
    if not code:
        return ""
    return str(code).strip().lstrip('0')

@router.post("/upload")
async def upload_advances(file: UploadFile = File(...), employees_json: Optional[str] = Form(None)):
    """
    Upload CSV/Excel file with advance data
    
    Expected columns: Date, Name, Advance, No (Employee Code), Type, UID
    Only rows with Type = "Salary" (case-insensitive) will be processed
    UID is used for update/insert (upsert)
    """
    logger.info(f"=== ADVANCE UPLOAD ===")
    logger.info(f"Filename: {file.filename}")
    logger.info(f"employees_json provided: {employees_json is not None}")
    
    try:
        content = await file.read()
        
        # Parse file based on extension
        filename = file.filename.lower()
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Only CSV and Excel files supported")
        
        logger.info(f"Parsed {len(df)} rows, columns: {list(df.columns)}")
        
        # Normalize column names (lowercase, strip)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Find columns (flexible matching)
        col_map = {}
        for col in df.columns:
            if 'date' in col:
                col_map['date'] = col
            elif 'name' in col and 'sheet' not in col:
                col_map['name'] = col
            elif 'advance' in col or 'amount' in col:
                col_map['advance'] = col
            elif col in ['no', 'no.', 'emp', 'code', 'employee code', 'emp code']:
                col_map['code'] = col
            elif 'type' in col:
                col_map['type'] = col
            elif 'uid' in col or 'id' in col:
                col_map['uid'] = col
        
        logger.info(f"Column mapping: {col_map}")
        
        # Check required columns
        required = ['date', 'name', 'advance', 'code', 'type']
        missing = [r for r in required if r not in col_map]
        if missing:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing columns: {missing}. Found: {list(df.columns)}"
            )
        
        # Get employees - first try MongoDB, then use provided employees_json
        employees = await db.employees.find({}, {"_id": 0, "code": 1, "name": 1}).to_list(1000)
        logger.info(f"MongoDB employees count: {len(employees)}")
        
        # If no employees in MongoDB and employees_json provided, parse it
        if not employees and employees_json:
            try:
                employees = json.loads(employees_json)
                logger.info(f"Parsed {len(employees)} employees from request JSON")
            except Exception as e:
                logger.error(f"Failed to parse employees_json: {e}")
        
        if not employees:
            logger.error("No employees found in MongoDB or request")
            raise HTTPException(
                status_code=400, 
                detail="No employees found! Please ensure employees are loaded in the Employees page."
            )
        
        emp_map = {}
        for emp in employees:
            norm_code = normalize_code(emp.get('code', ''))
            norm_name = normalize_name(emp.get('name', ''))
            # Map by code+name combo
            emp_map[f"{norm_code}_{norm_name}"] = emp
            # Also map by code only for partial match check
            emp_map[f"code_{norm_code}"] = emp
        
        logger.info(f"Loaded {len(employees)} employees for matching")
        
        # Process rows
        matched = 0
        skipped = 0
        errors = 0
        updated = 0
        results = []
        
        for idx, row in df.iterrows():
            try:
                # Get values
                date_val = str(row[col_map['date']]) if pd.notna(row[col_map['date']]) else ""
                name_val = str(row[col_map['name']]) if pd.notna(row[col_map['name']]) else ""
                advance_val = row[col_map['advance']]
                code_val = str(row[col_map['code']]) if pd.notna(row[col_map['code']]) else ""
                type_val = str(row[col_map['type']]) if pd.notna(row[col_map['type']]) else ""
                uid_val = str(row[col_map['uid']]) if 'uid' in col_map and pd.notna(row[col_map['uid']]) else None
                
                # Filter: Only Type = "Salary" (case-insensitive)
                if type_val.strip().lower() != 'salary':
                    skipped += 1
                    continue
                
                # Validate required fields
                if not name_val or not code_val:
                    errors += 1
                    results.append({"row": idx + 2, "status": "error", "reason": "Missing name or code"})
                    continue
                
                # Parse amount
                try:
                    if isinstance(advance_val, (int, float)):
                        amount = float(advance_val)
                    else:
                        amount = float(re.sub(r'[^\d.]', '', str(advance_val)))
                    if amount <= 0:
                        errors += 1
                        results.append({"row": idx + 2, "status": "error", "reason": "Amount <= 0"})
                        continue
                except:
                    errors += 1
                    results.append({"row": idx + 2, "status": "error", "reason": "Invalid amount"})
                    continue
                
                # Match employee - both Name AND Code must match
                norm_code = normalize_code(code_val)
                norm_name = normalize_name(name_val)
                match_key = f"{norm_code}_{norm_name}"
                
                emp_match = emp_map.get(match_key)
                
                if not emp_match:
                    # Check if code exists but name doesn't match
                    emp_by_code = emp_map.get(f"code_{norm_code}")
                    if emp_by_code:
                        errors += 1
                        results.append({
                            "row": idx + 2, 
                            "status": "error", 
                            "reason": f"Code {code_val} found but name mismatch: '{name_val}' vs '{emp_by_code['name']}'"
                        })
                    else:
                        errors += 1
                        results.append({"row": idx + 2, "status": "error", "reason": f"Employee not found: {code_val} - {name_val}"})
                    continue
                
                # Create advance record
                advance_record = {
                    "date": date_val,
                    "name": emp_match['name'],
                    "employeeCode": emp_match['code'],
                    "amount": amount,
                    "type": "Salary",
                    "syncStatus": "Done",
                    "uploadedAt": datetime.now(timezone.utc)
                }
                
                # Upsert based on UID if provided, else based on date+code+amount
                if uid_val:
                    advance_record["uid"] = uid_val
                    result = await db.salary_advances.update_one(
                        {"uid": uid_val},
                        {"$set": advance_record},
                        upsert=True
                    )
                    if result.modified_count > 0:
                        updated += 1
                        results.append({"row": idx + 2, "status": "updated", "uid": uid_val})
                    else:
                        matched += 1
                        results.append({"row": idx + 2, "status": "inserted", "uid": uid_val})
                else:
                    # Check for duplicate (same date, code, amount)
                    existing = await db.salary_advances.find_one({
                        "date": date_val,
                        "employeeCode": emp_match['code'],
                        "amount": amount
                    })
                    if existing:
                        skipped += 1
                        results.append({"row": idx + 2, "status": "duplicate", "reason": "Already exists"})
                        continue
                    
                    await db.salary_advances.insert_one(advance_record)
                    matched += 1
                    results.append({"row": idx + 2, "status": "inserted"})
                
            except Exception as e:
                errors += 1
                results.append({"row": idx + 2, "status": "error", "reason": str(e)})
                logger.error(f"Error processing row {idx + 2}: {e}")
        
        # Log upload
        await db.advance_uploads.insert_one({
            "filename": file.filename,
            "timestamp": datetime.now(timezone.utc),
            "total_rows": len(df),
            "matched": matched,
            "updated": updated,
            "skipped": skipped,
            "errors": errors
        })
        
        logger.info(f"Upload complete - Matched: {matched}, Updated: {updated}, Skipped: {skipped}, Errors: {errors}")
        
        return {
            "success": True,
            "message": f"Processed {len(df)} rows",
            "matched": matched,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
            "details": results[:50]  # Return first 50 results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_advances(month: Optional[int] = None, year: Optional[int] = None):
    """Get all synced advances"""
    query = {"syncStatus": "Done"}
    
    advances = await db.salary_advances.find(
        query,
        {"_id": 0}
    ).sort("uploadedAt", -1).to_list(500)
    
    # Filter by month/year if provided
    if month and year:
        filtered = []
        for adv in advances:
            try:
                date_str = adv.get("date", "")
                for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d-%b-%Y", "%d %b %Y"]:
                    try:
                        adv_date = datetime.strptime(str(date_str), fmt)
                        if adv_date.month == month and adv_date.year == year:
                            filtered.append(adv)
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
        advances = filtered
    
    # Get stats
    total = len(advances)
    total_amount = sum(adv.get("amount", 0) for adv in advances)
    
    # Get last upload time
    last_upload = await db.advance_uploads.find_one(sort=[("timestamp", -1)])
    
    return {
        "advances": advances,
        "stats": {
            "total": total,
            "totalAmount": total_amount
        },
        "lastUpload": last_upload.get("timestamp") if last_upload else None
    }

@router.get("/employee/{employee_code}")
async def get_employee_advances(employee_code: str, month: Optional[int] = None, year: Optional[int] = None):
    """Get advances for a specific employee"""
    norm_code = normalize_code(employee_code)
    
    # Find all advances for this employee
    all_advances = await db.salary_advances.find(
        {"syncStatus": "Done"},
        {"_id": 0}
    ).to_list(1000)
    
    # Filter by employee code
    advances = [a for a in all_advances if normalize_code(a.get("employeeCode", "")) == norm_code]
    
    # Filter by month/year if provided
    if month and year:
        filtered = []
        for adv in advances:
            try:
                date_str = adv.get("date", "")
                for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d-%b-%Y"]:
                    try:
                        adv_date = datetime.strptime(str(date_str), fmt)
                        if adv_date.month == month and adv_date.year == year:
                            filtered.append(adv)
                        break
                    except ValueError:
                        continue
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

@router.delete("/{uid}")
async def delete_advance(uid: str):
    """Delete a specific advance by UID"""
    result = await db.salary_advances.delete_one({"uid": uid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Advance not found")
    return {"success": True, "deleted": 1}
