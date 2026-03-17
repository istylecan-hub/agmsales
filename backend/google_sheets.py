# Google Sheets OAuth Integration for Advance Management
import os
import warnings
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials

router = APIRouter(prefix="/api/google-sheets", tags=["google-sheets"])

# Will be set from server.py
db = None

# OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://multimodule-erp-1.preview.emergentagent.com")
REDIRECT_URI = f"{FRONTEND_URL}/api/google-sheets/callback"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

class SheetConfig(BaseModel):
    spreadsheetId: str
    sheetName: str = "Sheet1"
    range: str = "A:F"

def set_db(database):
    global db
    db = database

def get_flow():
    """Create OAuth flow"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    return Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

@router.get("/login")
async def google_login():
    """Start Google OAuth login"""
    try:
        flow = get_flow()
        url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent'
        )
        
        # Store state in DB
        await db.oauth_states.insert_one({
            "state": state,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc).replace(minute=datetime.now().minute + 10)
        })
        
        return RedirectResponse(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/callback")
async def google_callback(code: str, state: str):
    """Handle Google OAuth callback"""
    try:
        # Verify state
        state_doc = await db.oauth_states.find_one({"state": state})
        if not state_doc:
            raise HTTPException(status_code=400, detail="Invalid state")
        
        # Delete used state
        await db.oauth_states.delete_one({"state": state})
        
        flow = get_flow()
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            flow.fetch_token(code=code)
        
        creds = flow.credentials
        
        # Check required scopes
        required_scopes = {"https://www.googleapis.com/auth/spreadsheets.readonly"}
        granted_scopes = set(creds.scopes or [])
        if not required_scopes.issubset(granted_scopes):
            missing = required_scopes - granted_scopes
            raise HTTPException(status_code=400, detail=f"Missing scopes: {missing}")
        
        # Save tokens
        await db.google_tokens.update_one(
            {"type": "sheets"},
            {
                "$set": {
                    "access_token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": list(creds.scopes),
                    "expires_at": datetime.now(timezone.utc).replace(hour=datetime.now().hour + 1),
                    "updated_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        
        return RedirectResponse(f"{FRONTEND_URL}/advance?connected=true")
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/advance?error={str(e)}")

@router.get("/status")
async def get_status():
    """Check if Google Sheets is connected"""
    token = await db.google_tokens.find_one({"type": "sheets"})
    return {"connected": token is not None and token.get("access_token") is not None}

@router.post("/disconnect")
async def disconnect():
    """Disconnect Google Sheets"""
    await db.google_tokens.delete_one({"type": "sheets"})
    return {"success": True}

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

async def get_sheets_credentials():
    """Get valid Google Sheets credentials with auto-refresh"""
    token = await db.google_tokens.find_one({"type": "sheets"})
    if not token:
        raise HTTPException(status_code=401, detail="Not connected to Google Sheets")
    
    creds = Credentials(
        token=token["access_token"],
        refresh_token=token.get("refresh_token"),
        token_uri=token.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token.get("client_id", GOOGLE_CLIENT_ID),
        client_secret=token.get("client_secret", GOOGLE_CLIENT_SECRET)
    )
    
    # Refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
        await db.google_tokens.update_one(
            {"type": "sheets"},
            {"$set": {"access_token": creds.token, "updated_at": datetime.now(timezone.utc)}}
        )
    
    return creds

async def read_sheet_data(spreadsheet_id: str, range_name: str):
    """Read data from Google Sheet"""
    creds = await get_sheets_credentials()
    service = build('sheets', 'v4', credentials=creds)
    
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()
    
    return result.get('values', [])

async def update_sheet_cell(spreadsheet_id: str, range_name: str, value: str):
    """Update a cell in Google Sheet (for sync status)"""
    # Note: This requires write permission - we'll skip for now since we have readonly
    pass
