from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List
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