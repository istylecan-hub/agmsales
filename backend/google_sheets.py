# Google Sheets Service Account Integration for Advance Management
import os
import json
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from google.oauth2 import service_account
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/google-sheets", tags=["google-sheets"])

# Will be set from server.py
db = None

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

class SheetConfig(BaseModel):
    spreadsheetId: str
    sheetName: str = "Sheet1"
    range: str = "A:F"

def set_db(database):
    global db
    db = database

@router.post("/upload-service-account")
async def upload_service_account(file: UploadFile = File(...)):
    """Upload Google Service Account JSON key file"""
    try:
        content = await file.read()
        data = json.loads(content)
        
        # Validate service account JSON
        required_fields = ["type", "project_id", "private_key", "client_email"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing field: {field}")
        
        if data["type"] != "service_account":
            raise HTTPException(status_code=400, detail="Invalid file type. Need service_account JSON")
        
        # Save to database
        await db.service_account.update_one(
            {"type": "google_sheets"},
            {
                "$set": {
                    "credentials": data,
                    "client_email": data["client_email"],
                    "project_id": data["project_id"],
                    "uploaded_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        
        return {
            "success": True,
            "message": "Service Account uploaded successfully!",
            "client_email": data["client_email"],
            "project_id": data["project_id"]
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_status():
    """Check if Service Account is configured"""
    sa = await db.service_account.find_one({"type": "google_sheets"})
    if sa and sa.get("credentials"):
        return {
            "connected": True,
            "client_email": sa.get("client_email", ""),
            "project_id": sa.get("project_id", "")
        }
    return {"connected": False}

@router.delete("/disconnect")
async def disconnect():
    """Remove Service Account credentials"""
    await db.service_account.delete_one({"type": "google_sheets"})
    return {"success": True, "message": "Service Account removed"}

@router.get("/config")
async def get_config():
    """Get sheet configuration"""
    config = await db.sheet_config.find_one({"type": "advance"})
    if config:
        return {
            "spreadsheetId": config.get("spreadsheetId", ""),
            "sheetName": config.get("sheetName", "Sheet1"),
            "range": config.get("range", "A:F")
        }
    return {"spreadsheetId": "", "sheetName": "Sheet1", "range": "A:F"}

@router.post("/config")
async def save_config(config: SheetConfig):
    """Save sheet configuration"""
    await db.sheet_config.update_one(
        {"type": "advance"},
        {
            "$set": {
                "spreadsheetId": config.spreadsheetId,
                "sheetName": config.sheetName,
                "range": config.range,
                "updated_at": datetime.now(timezone.utc)
            }
        },
        upsert=True
    )
    return {"success": True}

@router.post("/test-connection")
async def test_connection():
    """Test connection to Google Sheets"""
    try:
        # Get service account
        sa = await db.service_account.find_one({"type": "google_sheets"})
        if not sa or not sa.get("credentials"):
            raise HTTPException(status_code=400, detail="Service Account not configured")
        
        # Get sheet config
        config = await db.sheet_config.find_one({"type": "advance"})
        if not config or not config.get("spreadsheetId"):
            raise HTTPException(status_code=400, detail="Sheet ID not configured")
        
        # Test read
        data = await read_sheet_data(config["spreadsheetId"], f"{config.get('sheetName', 'Sheet1')}!A1:A5")
        
        return {
            "success": True,
            "message": f"Connection successful! Found {len(data)} rows",
            "sample": data[:3] if data else []
        }
    except Exception as e:
        logger.error(f"Test connection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_sheets_service():
    """Get Google Sheets service using Service Account"""
    sa = await db.service_account.find_one({"type": "google_sheets"})
    if not sa or not sa.get("credentials"):
        raise HTTPException(status_code=401, detail="Service Account not configured")
    
    credentials = service_account.Credentials.from_service_account_info(
        sa["credentials"],
        scopes=SCOPES
    )
    
    service = build('sheets', 'v4', credentials=credentials)
    return service

async def read_sheet_data(spreadsheet_id: str, range_name: str):
    """Read data from Google Sheet using Service Account"""
    service = await get_sheets_service()
    
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()
    
    return result.get('values', [])
