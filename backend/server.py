from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone

# Import Invoice Extractor module
from invoice_extractor import invoice_router, set_database as set_invoice_db


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection with error handling
mongo_url = os.environ.get('MONGO_URL', '')
db_name = os.environ.get('DB_NAME', 'agm_sales')

# Initialize client and db as None, connect lazily
client = None
db = None

async def get_database():
    global client, db
    if client is None:
        try:
            client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
            db = client[db_name]
            # Test connection
            await client.admin.command('ping')
            logging.info("MongoDB connected successfully")
            # Set database for invoice extractor module
            set_invoice_db(db)
        except Exception as e:
            logging.warning(f"MongoDB connection failed: {e}. App will still run (frontend uses localStorage).")
            client = None
            db = None
    return db

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

# Health check endpoint for Kubernetes deployment
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Backend is running"}

@api_router.get("/health")
async def api_health_check():
    return {"status": "healthy", "message": "API is running"}

# ============== EMPLOYEE MASTER CRUD ==============

class EmployeeModel(BaseModel):
    code: str
    name: str
    department: Optional[str] = None
    salary: float
    dateOfJoining: Optional[str] = None
    status: str = "active"
    onlySundayNoOT: bool = False

class EmployeeResponse(BaseModel):
    success: bool
    message: str
    data: Optional[List[dict]] = None

@api_router.get("/employees")
async def get_all_employees():
    """Get all employees from MongoDB"""
    database = await get_database()
    if database is None:
        return {"success": False, "message": "Database not connected", "data": []}
    
    try:
        employees = await database.employees.find({}, {"_id": 0}).to_list(1000)
        return {"success": True, "message": "Employees loaded", "data": employees}
    except Exception as e:
        logging.error(f"Error loading employees: {e}")
        return {"success": False, "message": str(e), "data": []}

@api_router.post("/employees")
async def save_employees(employees: List[EmployeeModel]):
    """Save/Replace all employees in MongoDB"""
    database = await get_database()
    if database is None:
        return {"success": False, "message": "Database not connected"}
    
    try:
        # Delete all existing employees and insert new ones
        await database.employees.delete_many({})
        if employees:
            employees_dict = [emp.model_dump() for emp in employees]
            await database.employees.insert_many(employees_dict)
        return {"success": True, "message": f"Saved {len(employees)} employees"}
    except Exception as e:
        logging.error(f"Error saving employees: {e}")
        return {"success": False, "message": str(e)}

@api_router.post("/employees/add")
async def add_employee(employee: EmployeeModel):
    """Add a single employee"""
    database = await get_database()
    if database is None:
        return {"success": False, "message": "Database not connected"}
    
    try:
        # Check if employee exists
        existing = await database.employees.find_one({"code": employee.code})
        if existing:
            return {"success": False, "message": "Employee code already exists"}
        
        await database.employees.insert_one(employee.model_dump())
        return {"success": True, "message": "Employee added"}
    except Exception as e:
        logging.error(f"Error adding employee: {e}")
        return {"success": False, "message": str(e)}

@api_router.put("/employees/{code}")
async def update_employee(code: str, employee: EmployeeModel):
    """Update an employee"""
    database = await get_database()
    if database is None:
        return {"success": False, "message": "Database not connected"}
    
    try:
        result = await database.employees.update_one(
            {"code": code},
            {"$set": employee.model_dump()}
        )
        if result.modified_count > 0:
            return {"success": True, "message": "Employee updated"}
        return {"success": False, "message": "Employee not found"}
    except Exception as e:
        logging.error(f"Error updating employee: {e}")
        return {"success": False, "message": str(e)}

@api_router.delete("/employees/{code}")
async def delete_employee_api(code: str):
    """Delete an employee"""
    database = await get_database()
    if database is None:
        return {"success": False, "message": "Database not connected"}
    
    try:
        result = await database.employees.delete_one({"code": code})
        if result.deleted_count > 0:
            return {"success": True, "message": "Employee deleted"}
        return {"success": False, "message": "Employee not found"}
    except Exception as e:
        logging.error(f"Error deleting employee: {e}")
        return {"success": False, "message": str(e)}


# ============== SALARY HISTORY CRUD ==============

class EmployeeSalaryRecord(BaseModel):
    """Individual employee salary record for a month"""
    code: str
    name: str
    department: Optional[str] = ""
    baseSalary: float = 0
    presentDays: float = 0
    absentDays: float = 0
    sandwichDays: float = 0
    sundayWorking: float = 0
    otHours: float = 0
    shortHours: float = 0
    netOTHours: float = 0
    totalPayableDays: float = 0
    totalSalary: float = 0
    perDaySalary: float = 0
    otAmount: float = 0
    deductions: float = 0
    
    class Config:
        extra = "ignore"  # Ignore extra fields

class SalaryRecordCreate(BaseModel):
    """Payload to save monthly salary data"""
    month: int  # 1-12
    year: int
    daysInMonth: int = 30
    employees: List[EmployeeSalaryRecord]
    totalPayout: float = 0
    config: Optional[dict] = None  # Store salary config used
    
    class Config:
        extra = "ignore"  # Ignore extra fields

class SalaryRecordUpdate(BaseModel):
    """Payload to update a specific employee's salary"""
    presentDays: Optional[float] = None
    absentDays: Optional[float] = None
    sandwichDays: Optional[float] = None
    sundayWorking: Optional[float] = None
    otHours: Optional[float] = None
    shortHours: Optional[float] = None
    netOTHours: Optional[float] = None
    totalPayableDays: Optional[float] = None
    totalSalary: Optional[float] = None
    otAmount: Optional[float] = None
    deductions: Optional[float] = None

@api_router.post("/salary/save")
async def save_monthly_salary(data: SalaryRecordCreate):
    """Save calculated salary for a month"""
    database = await get_database()
    if database is None:
        return {"success": False, "message": "Database not connected"}
    
    try:
        record_id = f"{data.year}-{str(data.month).zfill(2)}"
        
        salary_record = {
            "record_id": record_id,
            "month": data.month,
            "year": data.year,
            "daysInMonth": data.daysInMonth,
            "employees": [emp.model_dump() for emp in data.employees],
            "totalPayout": data.totalPayout,
            "employeeCount": len(data.employees),
            "config": data.config,
            "savedAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }
        
        # Upsert - update if exists, insert if not
        result = await database.salary_records.update_one(
            {"record_id": record_id},
            {"$set": salary_record},
            upsert=True
        )
        
        action = "updated" if result.matched_count > 0 else "saved"
        return {
            "success": True, 
            "message": f"Salary {action} for {data.month}/{data.year}",
            "record_id": record_id
        }
    except Exception as e:
        logging.error(f"Error saving salary: {e}")
        return {"success": False, "message": str(e)}

@api_router.get("/salary/history")
async def get_salary_history():
    """Get list of all saved salary months"""
    database = await get_database()
    if database is None:
        return {"success": False, "message": "Database not connected", "data": []}
    
    try:
        records = await database.salary_records.find(
            {},
            {"_id": 0, "record_id": 1, "month": 1, "year": 1, "totalPayout": 1, 
             "employeeCount": 1, "savedAt": 1, "updatedAt": 1}
        ).sort([("year", -1), ("month", -1)]).to_list(100)
        
        return {"success": True, "data": records}
    except Exception as e:
        logging.error(f"Error loading salary history: {e}")
        return {"success": False, "message": str(e), "data": []}

@api_router.get("/salary/history/{year}/{month}")
async def get_salary_for_month(year: int, month: int):
    """Get salary data for a specific month"""
    database = await get_database()
    if database is None:
        return {"success": False, "message": "Database not connected"}
    
    try:
        record_id = f"{year}-{str(month).zfill(2)}"
        record = await database.salary_records.find_one(
            {"record_id": record_id},
            {"_id": 0}
        )
        
        if record:
            return {"success": True, "data": record}
        return {"success": False, "message": "No salary record found for this month"}
    except Exception as e:
        logging.error(f"Error loading salary: {e}")
        return {"success": False, "message": str(e)}

@api_router.put("/salary/history/{year}/{month}/{emp_code}")
async def update_employee_salary(year: int, month: int, emp_code: str, update: SalaryRecordUpdate):
    """Update a specific employee's salary in a saved record"""
    database = await get_database()
    if database is None:
        return {"success": False, "message": "Database not connected"}
    
    try:
        record_id = f"{year}-{str(month).zfill(2)}"
        
        # Get current record
        record = await database.salary_records.find_one({"record_id": record_id})
        if not record:
            return {"success": False, "message": "Salary record not found"}
        
        # Find and update employee
        employees = record.get("employees", [])
        updated = False
        new_total = 0
        
        for emp in employees:
            if emp["code"] == emp_code:
                # Update only provided fields
                update_dict = update.model_dump(exclude_none=True)
                emp.update(update_dict)
                updated = True
            new_total += emp.get("totalSalary", 0)
        
        if not updated:
            return {"success": False, "message": "Employee not found in this record"}
        
        # Save updated record
        await database.salary_records.update_one(
            {"record_id": record_id},
            {
                "$set": {
                    "employees": employees,
                    "totalPayout": new_total,
                    "updatedAt": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        return {"success": True, "message": f"Updated salary for {emp_code}"}
    except Exception as e:
        logging.error(f"Error updating salary: {e}")
        return {"success": False, "message": str(e)}

@api_router.delete("/salary/history/{year}/{month}")
async def delete_salary_record(year: int, month: int):
    """Delete a saved salary record"""
    database = await get_database()
    if database is None:
        return {"success": False, "message": "Database not connected"}
    
    try:
        record_id = f"{year}-{str(month).zfill(2)}"
        result = await database.salary_records.delete_one({"record_id": record_id})
        
        if result.deleted_count > 0:
            return {"success": True, "message": f"Deleted salary record for {month}/{year}"}
        return {"success": False, "message": "Record not found"}
    except Exception as e:
        logging.error(f"Error deleting salary: {e}")
        return {"success": False, "message": str(e)}

@api_router.get("/salary/compare/{year1}/{month1}/{year2}/{month2}")
async def compare_salary_months(year1: int, month1: int, year2: int, month2: int):
    """Compare salary data between two months"""
    database = await get_database()
    if database is None:
        return {"success": False, "message": "Database not connected"}
    
    try:
        record_id1 = f"{year1}-{str(month1).zfill(2)}"
        record_id2 = f"{year2}-{str(month2).zfill(2)}"
        
        record1 = await database.salary_records.find_one({"record_id": record_id1}, {"_id": 0})
        record2 = await database.salary_records.find_one({"record_id": record_id2}, {"_id": 0})
        
        if not record1 or not record2:
            missing = []
            if not record1:
                missing.append(f"{month1}/{year1}")
            if not record2:
                missing.append(f"{month2}/{year2}")
            return {"success": False, "message": f"Missing records for: {', '.join(missing)}"}
        
        # Build comparison data
        comparison = {
            "month1": {"month": month1, "year": year1, "label": f"{month1}/{year1}"},
            "month2": {"month": month2, "year": year2, "label": f"{month2}/{year2}"},
            "summary": {
                "totalPayout1": record1.get("totalPayout", 0),
                "totalPayout2": record2.get("totalPayout", 0),
                "difference": record2.get("totalPayout", 0) - record1.get("totalPayout", 0),
                "employeeCount1": record1.get("employeeCount", 0),
                "employeeCount2": record2.get("employeeCount", 0)
            },
            "employees": []
        }
        
        # Create employee comparison
        emp1_map = {e["code"]: e for e in record1.get("employees", [])}
        emp2_map = {e["code"]: e for e in record2.get("employees", [])}
        all_codes = set(emp1_map.keys()) | set(emp2_map.keys())
        
        for code in all_codes:
            e1 = emp1_map.get(code, {})
            e2 = emp2_map.get(code, {})
            
            comparison["employees"].append({
                "code": code,
                "name": e2.get("name") or e1.get("name", "Unknown"),
                "salary1": e1.get("totalSalary", 0),
                "salary2": e2.get("totalSalary", 0),
                "difference": e2.get("totalSalary", 0) - e1.get("totalSalary", 0),
                "presentDays1": e1.get("presentDays", 0),
                "presentDays2": e2.get("presentDays", 0),
                "otHours1": e1.get("otHours", 0),
                "otHours2": e2.get("otHours", 0)
            })
        
        return {"success": True, "data": comparison}
    except Exception as e:
        logging.error(f"Error comparing salary: {e}")
        return {"success": False, "message": str(e)}

@api_router.get("/salary/employee/{emp_code}/growth")
async def get_employee_growth(emp_code: str):
    """Get salary growth history for an employee"""
    database = await get_database()
    if database is None:
        return {"success": False, "message": "Database not connected"}
    
    try:
        # Get all salary records sorted by date
        records = await database.salary_records.find(
            {},
            {"_id": 0, "record_id": 1, "month": 1, "year": 1, "employees": 1}
        ).sort([("year", 1), ("month", 1)]).to_list(100)
        
        growth_data = []
        for record in records:
            for emp in record.get("employees", []):
                if emp["code"] == emp_code:
                    growth_data.append({
                        "month": record["month"],
                        "year": record["year"],
                        "label": f"{record['month']}/{record['year']}",
                        "totalSalary": emp.get("totalSalary", 0),
                        "presentDays": emp.get("presentDays", 0),
                        "otHours": emp.get("otHours", 0),
                        "baseSalary": emp.get("baseSalary", 0)
                    })
                    break
        
        if not growth_data:
            return {"success": False, "message": f"No salary history found for employee {emp_code}"}
        
        # Calculate growth metrics
        if len(growth_data) >= 2:
            first = growth_data[0]["totalSalary"]
            last = growth_data[-1]["totalSalary"]
            total_growth = last - first
            avg_monthly_growth = total_growth / (len(growth_data) - 1) if len(growth_data) > 1 else 0
        else:
            total_growth = 0
            avg_monthly_growth = 0
        
        return {
            "success": True,
            "data": {
                "employeeCode": emp_code,
                "history": growth_data,
                "totalGrowth": total_growth,
                "avgMonthlyGrowth": round(avg_monthly_growth, 2),
                "monthsTracked": len(growth_data)
            }
        }
    except Exception as e:
        logging.error(f"Error loading employee growth: {e}")
        return {"success": False, "message": str(e)}


@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    database = await get_database()
    if database is None:
        # Return a mock response if DB not available
        return StatusCheck(client_name=input.client_name)
    
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await database.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    database = await get_database()
    if database is None:
        return []
    
    # Exclude MongoDB's _id field from the query results
    status_checks = await database.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# Include the router in the main app
app.include_router(api_router)

# Include Invoice Extractor router
app.include_router(invoice_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_db_client():
    await get_database()

@app.on_event("shutdown")
async def shutdown_db_client():
    global client
    if client:
        client.close()