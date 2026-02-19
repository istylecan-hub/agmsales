# Invoice Extractor Module for AGM Sales App
# Extracts structured data from PDF invoices using AI

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import asyncio
import aiofiles
import json
import re
import csv

# PDF processing
import PyPDF2
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

# Excel processing
import openpyxl
from openpyxl.utils import get_column_letter

# LLM integration
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

logger = logging.getLogger(__name__)

# File storage directories
ROOT_DIR = Path(__file__).parent
UPLOAD_DIR = ROOT_DIR / "uploads"
EXPORT_DIR = ROOT_DIR / "exports"
UPLOAD_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

# Max file size (25MB)
MAX_FILE_SIZE = 25 * 1024 * 1024

# Create router
invoice_router = APIRouter(prefix="/api/invoice")

# ============== PYDANTIC MODELS ==============

class LineItem(BaseModel):
    category_code_or_hsn: Optional[str] = None
    service_description: Optional[str] = None
    fee_amount: Optional[float] = None
    cgst_amount: Optional[float] = None
    sgst_amount: Optional[float] = None
    igst_amount: Optional[float] = None
    total_tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    tax_rate_percent: Optional[float] = None

class InvoiceData(BaseModel):
    source_platform: str = "Unknown"
    document_type: str = "Invoice"
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    service_provider_name: Optional[str] = None
    service_provider_gstin: Optional[str] = None
    service_receiver_name: Optional[str] = None
    service_receiver_gstin: Optional[str] = None
    place_of_supply_state_code: Optional[str] = None
    currency: str = "INR"
    subtotal_fee_amount: Optional[float] = None
    cgst_amount: Optional[float] = None
    sgst_amount: Optional[float] = None
    igst_amount: Optional[float] = None
    total_tax_amount: Optional[float] = None
    total_invoice_amount: Optional[float] = None
    line_items: List[LineItem] = []

class UploadResponse(BaseModel):
    job_id: str
    files: List[Dict[str, str]]

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    total_files: int
    processed_files: int
    failed_files: int
    files: List[Dict[str, Any]]

# Database reference (will be set from main server)
db = None

def set_database(database):
    global db
    db = database

# ============== PDF EXTRACTION HELPERS ==============

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using PyPDF2, with OCR fallback."""
    text = ""
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
    except Exception as e:
        logger.error(f"PyPDF2 extraction failed: {e}")
    
    # If text is too short or empty, try OCR
    if len(text.strip()) < 100 and PDF2IMAGE_AVAILABLE and PYTESSERACT_AVAILABLE:
        logger.info("Low text detected, attempting OCR...")
        try:
            images = convert_from_path(file_path)
            for image in images:
                ocr_text = pytesseract.image_to_string(image)
                text += ocr_text + "\n"
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
    
    return text.strip()

def normalize_amount(value: Any) -> Optional[float]:
    """Normalize amount strings to float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    if isinstance(value, str):
        cleaned = re.sub(r'[₹,$,\s]', '', value)
        cleaned = cleaned.replace(',', '')
        try:
            return round(float(cleaned), 2)
        except ValueError:
            return None
    return None

def normalize_date(date_str: str) -> Optional[str]:
    """Normalize date to dd/mm/yyyy format."""
    if not date_str:
        return None
    
    date_formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", 
        "%d %B %Y", "%Y/%m/%d", "%m/%d/%Y", "%d.%m.%Y"
    ]
    
    for fmt in date_formats:
        try:
            parsed = datetime.strptime(date_str.strip(), fmt)
            return parsed.strftime("%d/%m/%Y")
        except ValueError:
            continue
    
    return date_str

def detect_platform(text: str) -> str:
    """Detect source platform from invoice text."""
    text_lower = text.lower()
    if "amazon seller services" in text_lower or "amazon.in" in text_lower:
        return "Amazon"
    elif "meesho" in text_lower:
        return "Meesho"
    elif "fashnear" in text_lower:
        return "Fashnear"
    return "Unknown"

# ============== REGEX-BASED FALLBACK EXTRACTOR ==============

def extract_with_regex(text: str, filename: str) -> Dict[str, Any]:
    """Fallback extraction using regex patterns when LLM is unavailable."""
    data = {
        "source_platform": detect_platform(text),
        "document_type": "CreditNote" if "credit note" in text.lower() else "Invoice",
        "invoice_number": None,
        "invoice_date": None,
        "service_provider_name": None,
        "service_provider_gstin": None,
        "service_receiver_name": None,
        "service_receiver_gstin": None,
        "place_of_supply_state_code": None,
        "currency": "INR",
        "subtotal_fee_amount": None,
        "cgst_amount": None,
        "sgst_amount": None,
        "igst_amount": None,
        "total_tax_amount": None,
        "total_invoice_amount": None,
        "line_items": [],
        "_extraction_method": "regex_fallback"
    }
    
    # Extract invoice number patterns
    inv_patterns = [
        r'Invoice\s*(?:No|Number|#)?[:\s]*([A-Z0-9\-/]+)',
        r'INV[:\s\-]*([A-Z0-9\-/]+)',
        r'Bill\s*No[:\s]*([A-Z0-9\-/]+)',
    ]
    for pattern in inv_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['invoice_number'] = match.group(1).strip()
            break
    
    # Extract date patterns
    date_patterns = [
        r'(?:Invoice\s*)?Date[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})',
        r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['invoice_date'] = normalize_date(match.group(1))
            break
    
    # Extract GSTIN (15 character alphanumeric)
    gstin_pattern = r'\b(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1})\b'
    gstin_matches = re.findall(gstin_pattern, text, re.IGNORECASE)
    if len(gstin_matches) >= 1:
        data['service_provider_gstin'] = gstin_matches[0].upper()
    if len(gstin_matches) >= 2:
        data['service_receiver_gstin'] = gstin_matches[1].upper()
    
    # Extract company names based on platform
    if data['source_platform'] == 'Amazon':
        data['service_provider_name'] = 'Amazon Seller Services Private Limited'
    elif data['source_platform'] == 'Meesho':
        data['service_provider_name'] = 'Meesho Technologies Pvt Ltd'
    elif data['source_platform'] == 'Fashnear':
        data['service_provider_name'] = 'Fashnear Technologies Pvt Ltd'
    
    # Extract amounts
    amount_patterns = {
        'subtotal': r'(?:Sub\s*total|Taxable\s*Value)[:\s]*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)',
        'cgst': r'CGST[:\s@\d%]*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)',
        'sgst': r'SGST[:\s@\d%]*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)',
        'igst': r'IGST[:\s@\d%]*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)',
        'total_tax': r'(?:Total\s*)?(?:Tax|GST)[:\s]*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)',
        'total': r'(?:Grand\s*)?Total[:\s]*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)',
    }
    
    for key, pattern in amount_patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = normalize_amount(match.group(1))
            if key == 'subtotal':
                data['subtotal_fee_amount'] = amount
            elif key == 'cgst':
                data['cgst_amount'] = amount
            elif key == 'sgst':
                data['sgst_amount'] = amount
            elif key == 'igst':
                data['igst_amount'] = amount
            elif key == 'total_tax':
                data['total_tax_amount'] = amount
            elif key == 'total':
                data['total_invoice_amount'] = amount
    
    # Extract HSN codes
    hsn_pattern = r'\b(99\d{4})\b'
    hsn_matches = re.findall(hsn_pattern, text)
    
    if hsn_matches:
        for hsn in set(hsn_matches):
            data['line_items'].append({
                "category_code_or_hsn": hsn,
                "service_description": None,
                "fee_amount": None,
                "cgst_amount": None,
                "sgst_amount": None,
                "igst_amount": None,
                "total_tax_amount": None,
                "total_amount": None,
                "tax_rate_percent": None
            })
    
    return data

# ============== LLM EXTRACTION ==============

async def extract_invoice_with_llm(text: str, filename: str, api_key: str) -> Dict[str, Any]:
    """Use GPT-5.2 to extract structured invoice data."""
    
    if not LLM_AVAILABLE or not api_key:
        logger.info("LLM not available, using regex extraction")
        return extract_with_regex(text, filename)
    
    system_prompt = """You are an expert invoice data extractor. Extract structured data from invoice text.

IMPORTANT RULES:
1. Do NOT hallucinate. If a field is not found, use null.
2. For dates, normalize to dd/mm/yyyy format.
3. For amounts, remove commas and return numeric values with 2 decimals.
4. Detect platform: "Amazon" if Amazon Seller Services, "Meesho" if Meesho Technologies, "Fashnear" if Fashnear Technologies, else "Unknown".
5. document_type should be "Invoice" or "CreditNote".

Return ONLY valid JSON matching this schema:
{
    "source_platform": "Amazon|Meesho|Fashnear|Unknown",
    "document_type": "Invoice|CreditNote",
    "invoice_number": "string or null",
    "invoice_date": "dd/mm/yyyy or null",
    "service_provider_name": "string or null",
    "service_provider_gstin": "string or null",
    "service_receiver_name": "string or null",
    "service_receiver_gstin": "string or null",
    "place_of_supply_state_code": "2-digit code or null",
    "currency": "INR",
    "subtotal_fee_amount": number or null,
    "cgst_amount": number or null,
    "sgst_amount": number or null,
    "igst_amount": number or null,
    "total_tax_amount": number or null,
    "total_invoice_amount": number or null,
    "line_items": [
        {
            "category_code_or_hsn": "string or null",
            "service_description": "string or null",
            "fee_amount": number or null,
            "cgst_amount": number or null,
            "sgst_amount": number or null,
            "igst_amount": number or null,
            "total_tax_amount": number or null,
            "total_amount": number or null,
            "tax_rate_percent": number or null
        }
    ]
}"""

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"invoice-extraction-{uuid.uuid4()}",
            system_message=system_prompt
        ).with_model("openai", "gpt-5.2")
        
        user_message = UserMessage(
            text=f"Extract structured invoice data from this invoice text:\n\n{text[:15000]}"
        )
        
        response = await chat.send_message(user_message)
        
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            data = json.loads(json_match.group())
            data['source_platform'] = data.get('source_platform') or detect_platform(text)
            data['invoice_date'] = normalize_date(data.get('invoice_date'))
            
            for field in ['subtotal_fee_amount', 'cgst_amount', 'sgst_amount', 'igst_amount', 'total_tax_amount', 'total_invoice_amount']:
                data[field] = normalize_amount(data.get(field))
            
            if 'line_items' in data and data['line_items']:
                for item in data['line_items']:
                    for field in ['fee_amount', 'cgst_amount', 'sgst_amount', 'igst_amount', 'total_tax_amount', 'total_amount', 'tax_rate_percent']:
                        item[field] = normalize_amount(item.get(field))
            
            data['_extraction_method'] = 'llm'
            return data
        else:
            raise ValueError("No valid JSON found in LLM response")
            
    except Exception as e:
        logger.error(f"LLM extraction failed for {filename}: {e}")
        fallback_data = extract_with_regex(text, filename)
        fallback_data['_llm_error'] = str(e)
        return fallback_data

# ============== FILE PROCESSING ==============

async def process_single_file(job_id: str, file_info: Dict, use_llm: bool = True, api_key: str = None) -> None:
    """Process a single PDF file."""
    if db is None:
        logger.error("Database not initialized")
        return
        
    file_id = file_info['id']
    filename = file_info['filename']
    original_filename = file_info['original_filename']
    file_path = UPLOAD_DIR / filename
    
    try:
        await db.invoice_job_files.update_one(
            {"id": file_id, "job_id": job_id},
            {"$set": {"status": "processing", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        text = extract_text_from_pdf(str(file_path))
        
        if not text:
            raise ValueError("Could not extract text from PDF")
        
        if use_llm and api_key:
            extraction_data = await extract_invoice_with_llm(text, original_filename, api_key)
        else:
            extraction_data = extract_with_regex(text, original_filename)
        
        extraction_data['_source_file'] = original_filename
        
        await db.invoice_job_files.update_one(
            {"id": file_id, "job_id": job_id},
            {
                "$set": {
                    "status": "done",
                    "extraction_data": extraction_data,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        await db.invoice_jobs.update_one(
            {"job_id": job_id},
            {"$inc": {"processed_files": 1}}
        )
        
        logger.info(f"Successfully processed: {original_filename}")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to process {original_filename}: {error_msg}")
        
        await db.invoice_job_files.update_one(
            {"id": file_id, "job_id": job_id},
            {
                "$set": {
                    "status": "failed",
                    "error_message": error_msg,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        await db.invoice_jobs.update_one(
            {"job_id": job_id},
            {"$inc": {"failed_files": 1, "processed_files": 1}}
        )

async def run_extraction_job(job_id: str, use_llm: bool = True, api_key: str = None) -> None:
    """Run the complete extraction job."""
    if db is None:
        logger.error("Database not initialized")
        return
        
    try:
        files = await db.invoice_job_files.find({"job_id": job_id}, {"_id": 0}).to_list(1000)
        
        await db.invoice_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"status": "processing"}}
        )
        
        # Process files sequentially to avoid rate limits
        for file_info in files:
            await process_single_file(job_id, file_info, use_llm, api_key)
        
        await db.invoice_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"status": "completed"}}
        )
        
        logger.info(f"Invoice Job {job_id} completed")
        
    except Exception as e:
        logger.error(f"Invoice Job {job_id} failed: {e}")
        await db.invoice_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"status": "failed"}}
        )

# ============== EXPORT HELPERS ==============

def generate_csv(job_id: str, files_data: List[Dict]) -> str:
    """Generate CSV file with line items."""
    csv_path = EXPORT_DIR / f"{job_id}_invoice_line_items.csv"
    
    headers = [
        "Invoice Number", "Invoice Date", "Document Type", "Service Provider",
        "Provider GSTIN", "Service Receiver", "Receiver GSTIN", "Place of Supply",
        "Category Code/HSN", "Service Description", "Fee Amount (INR)",
        "CGST (INR)", "SGST (INR)", "IGST (INR)", "Total Tax (INR)",
        "Total Amount (INR)", "Source File"
    ]
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for file_data in files_data:
            if file_data.get('status') != 'done':
                continue
            
            data = file_data.get('extraction_data', {})
            line_items = data.get('line_items', [])
            
            if not line_items:
                writer.writerow([
                    data.get('invoice_number', ''),
                    data.get('invoice_date', ''),
                    data.get('document_type', ''),
                    data.get('service_provider_name', ''),
                    data.get('service_provider_gstin', ''),
                    data.get('service_receiver_name', ''),
                    data.get('service_receiver_gstin', ''),
                    data.get('place_of_supply_state_code', ''),
                    '', '', 
                    data.get('subtotal_fee_amount', ''),
                    data.get('cgst_amount', ''),
                    data.get('sgst_amount', ''),
                    data.get('igst_amount', ''),
                    data.get('total_tax_amount', ''),
                    data.get('total_invoice_amount', ''),
                    data.get('_source_file', file_data.get('original_filename', ''))
                ])
            else:
                for item in line_items:
                    writer.writerow([
                        data.get('invoice_number', ''),
                        data.get('invoice_date', ''),
                        data.get('document_type', ''),
                        data.get('service_provider_name', ''),
                        data.get('service_provider_gstin', ''),
                        data.get('service_receiver_name', ''),
                        data.get('service_receiver_gstin', ''),
                        data.get('place_of_supply_state_code', ''),
                        item.get('category_code_or_hsn', ''),
                        item.get('service_description', ''),
                        item.get('fee_amount', ''),
                        item.get('cgst_amount', ''),
                        item.get('sgst_amount', ''),
                        item.get('igst_amount', ''),
                        item.get('total_tax_amount', ''),
                        item.get('total_amount', ''),
                        data.get('_source_file', file_data.get('original_filename', ''))
                    ])
    
    return str(csv_path)

def generate_excel(job_id: str, files_data: List[Dict]) -> str:
    """Generate Excel file with 5 sheets."""
    excel_path = EXPORT_DIR / f"{job_id}_invoice_data.xlsx"
    
    wb = openpyxl.Workbook()
    
    all_line_items = []
    for file_data in files_data:
        if file_data.get('status') != 'done':
            continue
        data = file_data.get('extraction_data', {})
        line_items = data.get('line_items', [])
        
        for item in line_items:
            all_line_items.append({
                'invoice_number': data.get('invoice_number', ''),
                'invoice_date': data.get('invoice_date', ''),
                'service_provider': data.get('service_provider_name', ''),
                'provider_gstin': data.get('service_provider_gstin', ''),
                'service_receiver': data.get('service_receiver_name', ''),
                'receiver_gstin': data.get('service_receiver_gstin', ''),
                'category_code': item.get('category_code_or_hsn', ''),
                'service_description': item.get('service_description', ''),
                'fee_amount': item.get('fee_amount') or 0,
                'cgst_amount': item.get('cgst_amount') or 0,
                'sgst_amount': item.get('sgst_amount') or 0,
                'igst_amount': item.get('igst_amount') or 0,
                'total_tax': item.get('total_tax_amount') or 0,
                'total_amount': item.get('total_amount') or 0,
                'document_type': data.get('document_type', 'Invoice'),
                'source_file': data.get('_source_file', '')
            })
        
        if not line_items:
            all_line_items.append({
                'invoice_number': data.get('invoice_number', ''),
                'invoice_date': data.get('invoice_date', ''),
                'service_provider': data.get('service_provider_name', ''),
                'provider_gstin': data.get('service_provider_gstin', ''),
                'service_receiver': data.get('service_receiver_name', ''),
                'receiver_gstin': data.get('service_receiver_gstin', ''),
                'category_code': '',
                'service_description': '',
                'fee_amount': data.get('subtotal_fee_amount') or 0,
                'cgst_amount': data.get('cgst_amount') or 0,
                'sgst_amount': data.get('sgst_amount') or 0,
                'igst_amount': data.get('igst_amount') or 0,
                'total_tax': data.get('total_tax_amount') or 0,
                'total_amount': data.get('total_invoice_amount') or 0,
                'document_type': data.get('document_type', 'Invoice'),
                'source_file': data.get('_source_file', '')
            })
    
    # Sheet 1: Invoice Data
    ws1 = wb.active
    ws1.title = "Invoice Data"
    ws1.append([
        "Invoice Number", "Invoice Date", "Service Provider", "Provider GSTIN",
        "Service Receiver", "Receiver GSTIN", "Category Code", "Service Description",
        "Fee Amount (INR)", "CGST (INR)", "SGST (INR)", "IGST (INR)",
        "Total Tax (INR)", "Total Amount (INR)"
    ])
    
    for item in all_line_items:
        ws1.append([
            item['invoice_number'], item['invoice_date'], item['service_provider'],
            item['provider_gstin'], item['service_receiver'], item['receiver_gstin'],
            item['category_code'], item['service_description'], item['fee_amount'],
            item['cgst_amount'], item['sgst_amount'], item['igst_amount'],
            item['total_tax'], item['total_amount']
        ])
    
    # Sheet 2: Service Summary
    ws2 = wb.create_sheet("Service Summary")
    ws2.append(["Service Description", "Fee Amount", "Tax Amount", "Total Amount"])
    
    service_summary = {}
    for item in all_line_items:
        desc = item['service_description'] or 'Other'
        if desc not in service_summary:
            service_summary[desc] = {'fee': 0, 'tax': 0, 'total': 0}
        service_summary[desc]['fee'] += item['fee_amount']
        service_summary[desc]['tax'] += item['total_tax']
        service_summary[desc]['total'] += item['total_amount']
    
    for desc, values in service_summary.items():
        ws2.append([desc, round(values['fee'], 2), round(values['tax'], 2), round(values['total'], 2)])
    
    # Sheet 3: Category Summary
    ws3 = wb.create_sheet("Category Summary")
    ws3.append(["Category Code", "Fee Amount", "Tax Amount", "Total Amount"])
    
    category_summary = {}
    for item in all_line_items:
        code = item['category_code'] or 'Other'
        if code not in category_summary:
            category_summary[code] = {'fee': 0, 'tax': 0, 'total': 0}
        category_summary[code]['fee'] += item['fee_amount']
        category_summary[code]['tax'] += item['total_tax']
        category_summary[code]['total'] += item['total_amount']
    
    for code, values in category_summary.items():
        ws3.append([code, round(values['fee'], 2), round(values['tax'], 2), round(values['total'], 2)])
    
    # Auto-adjust column widths
    for ws in [ws1, ws2, ws3]:
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            ws.column_dimensions[column_letter].width = min(max_length + 2, 50)
    
    wb.save(excel_path)
    return str(excel_path)

# ============== API ROUTES ==============

@invoice_router.get("/")
async def invoice_root():
    return {"message": "Invoice Extractor API", "status": "ready"}

@invoice_router.post("/upload", response_model=UploadResponse)
async def upload_invoice_files(files: List[UploadFile] = File(...)):
    """Upload multiple PDF files for extraction."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    job_id = str(uuid.uuid4())
    uploaded_files = []
    
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type: {file.filename}. Only PDF files are allowed."
            )
        
        content = await file.read()
        
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} exceeds maximum size of 25MB"
            )
        
        file_id = str(uuid.uuid4())
        safe_filename = f"{file_id}.pdf"
        file_path = UPLOAD_DIR / safe_filename
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        file_info = {
            "id": file_id,
            "job_id": job_id,
            "filename": safe_filename,
            "original_filename": file.filename,
            "status": "pending",
            "error_message": None,
            "extraction_data": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.invoice_job_files.insert_one(file_info)
        
        uploaded_files.append({
            "id": file_id,
            "filename": file.filename,
            "status": "pending"
        })
    
    job_record = {
        "job_id": job_id,
        "total_files": len(uploaded_files),
        "processed_files": 0,
        "failed_files": 0,
        "status": "idle",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.invoice_jobs.insert_one(job_record)
    
    return UploadResponse(job_id=job_id, files=uploaded_files)

@invoice_router.post("/extract/{job_id}")
async def start_invoice_extraction(job_id: str, background_tasks: BackgroundTasks, use_llm: bool = True):
    """Start the extraction process for a job."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    job = await db.invoice_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get('status') == 'processing':
        raise HTTPException(status_code=400, detail="Job is already processing")
    
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    background_tasks.add_task(run_extraction_job, job_id, use_llm, api_key)
    
    return {"message": "Extraction started", "job_id": job_id, "use_llm": use_llm}

@invoice_router.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_invoice_job_status(job_id: str):
    """Get the status of an extraction job."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    job = await db.invoice_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    files = await db.invoice_job_files.find({"job_id": job_id}, {"_id": 0}).to_list(1000)
    
    return JobStatusResponse(
        job_id=job_id,
        status=job.get('status', 'idle'),
        total_files=job.get('total_files', 0),
        processed_files=job.get('processed_files', 0),
        failed_files=job.get('failed_files', 0),
        files=[{
            "id": f.get('id'),
            "filename": f.get('original_filename'),
            "status": f.get('status'),
            "error_message": f.get('error_message'),
            "extraction_data": f.get('extraction_data')
        } for f in files]
    )

@invoice_router.get("/export/csv/{job_id}")
async def export_invoice_csv(job_id: str):
    """Export extraction results as CSV."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    job = await db.invoice_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get('status') != 'completed':
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    files = await db.invoice_job_files.find({"job_id": job_id}, {"_id": 0}).to_list(1000)
    csv_path = generate_csv(job_id, files)
    
    def iterfile():
        with open(csv_path, 'rb') as f:
            yield from f
    
    filename = f"invoice_data_{job_id[:8]}.csv"
    return StreamingResponse(
        iterfile(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

@invoice_router.get("/export/excel/{job_id}")
async def export_invoice_excel(job_id: str):
    """Export extraction results as Excel."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    job = await db.invoice_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get('status') != 'completed':
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    files = await db.invoice_job_files.find({"job_id": job_id}, {"_id": 0}).to_list(1000)
    excel_path = generate_excel(job_id, files)
    
    def iterfile():
        with open(excel_path, 'rb') as f:
            yield from f
    
    filename = f"invoice_data_{job_id[:8]}.xlsx"
    return StreamingResponse(
        iterfile(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

@invoice_router.delete("/job/{job_id}")
async def delete_invoice_job(job_id: str):
    """Delete a job and its associated files."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    job = await db.invoice_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    files = await db.invoice_job_files.find({"job_id": job_id}, {"_id": 0}).to_list(1000)
    
    for file_info in files:
        file_path = UPLOAD_DIR / file_info.get('filename', '')
        if file_path.exists():
            file_path.unlink()
    
    csv_path = EXPORT_DIR / f"{job_id}_invoice_line_items.csv"
    excel_path = EXPORT_DIR / f"{job_id}_invoice_data.xlsx"
    if csv_path.exists():
        csv_path.unlink()
    if excel_path.exists():
        excel_path.unlink()
    
    await db.invoice_job_files.delete_many({"job_id": job_id})
    await db.invoice_jobs.delete_one({"job_id": job_id})
    
    return {"message": "Job deleted successfully"}
