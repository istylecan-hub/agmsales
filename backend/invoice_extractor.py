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
    elif "flipkart" in text_lower:
        return "Flipkart"
    return "Unknown"


def extract_flipkart_invoice(text: str, filename: str) -> Dict[str, Any]:
    """
    Specialized extraction for Flipkart invoices/credit notes.
    Handles three types:
    1. Commission/Tax Invoice (FKRKA prefix) - with GSTIN, IGST
    2. Credit Note (FKCKA prefix) - with GSTIN, IGST
    3. Commercial Credit Note (ICNDL prefix) - NO GSTIN, NO Tax
    """
    data = {
        "source_platform": "Flipkart",
        "document_type": "Invoice",
        "invoice_number": None,
        "invoice_date": None,
        "service_provider_name": "Flipkart Internet Private Limited",
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
        "_extraction_method": "flipkart_regex"
    }
    
    # Detect document type
    if "credit note" in text.lower():
        if "commercial credit note" in text.lower():
            data['document_type'] = "CommercialCreditNote"
        else:
            data['document_type'] = "CreditNote"
    elif "commission" in text.lower() or "tax invoice" in text.lower():
        data['document_type'] = "Invoice"
    
    # Extract Invoice/Credit Note Number
    # For Credit Notes, prioritize "Credit Note #" over "Original Invoice #"
    if "credit note" in text.lower():
        # For credit notes, look for Credit Note # first
        credit_note_match = re.search(r'Credit\s*Note\s*#:\s*([A-Z0-9]+)', text, re.IGNORECASE)
        if credit_note_match:
            data['invoice_number'] = credit_note_match.group(1).strip()
    
    # If not found yet, try other patterns
    if not data['invoice_number']:
        inv_patterns = [
            r'Invoice\s*#:\s*([A-Z0-9]+)',
            r'Credit\s*Note\s*#:\s*([A-Z0-9]+)',
            r'Invoice\s*No\.?\s*:?\s*([A-Z0-9]+)',
        ]
        for pattern in inv_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['invoice_number'] = match.group(1).strip()
                break
    
    # Extract Date - formats: "31-05-2025" or "31/05/2025"
    date_patterns = [
        r'(?:Invoice|Credit\s*Note)\s*Date:\s*(\d{2}[-/]\d{2}[-/]\d{4})',
        r'Date:\s*(\d{2}[-/]\d{2}[-/]\d{4})',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1).replace('-', '/')
            data['invoice_date'] = normalize_date(date_str)
            break
    
    # Extract Service Provider GSTIN (Flipkart's GSTIN in BILLED FROM section)
    # Flipkart's GSTIN is in Karnataka: 29AACCF0683K1ZD
    # NOTE: PDF extraction may have BILLED TO before BILLED FROM due to text flow
    
    gstin_pattern = r'(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1})'
    
    # Look for GSTIN after "BILLED FROM" 
    billed_from_section = re.search(r'BILLED\s*FROM:(.+?)(?:Original|E\.and|$)', text, re.IGNORECASE | re.DOTALL)
    if billed_from_section:
        provider_gstin_match = re.search(gstin_pattern, billed_from_section.group(1), re.IGNORECASE)
        if provider_gstin_match:
            data['service_provider_gstin'] = provider_gstin_match.group(1).upper()
    
    # Look for GSTIN after "BILLED TO" and before "IRN"
    billed_to_section = re.search(r'BILLED\s*TO:(.+?)(?:IRN:|CREDIT|BILLED\s*FROM|$)', text, re.IGNORECASE | re.DOTALL)
    if billed_to_section:
        receiver_gstin_match = re.search(gstin_pattern, billed_to_section.group(1), re.IGNORECASE)
        if receiver_gstin_match:
            data['service_receiver_gstin'] = receiver_gstin_match.group(1).upper()
    
    # Fallback: Look for all GSTINs and identify by state code
    # Flipkart's GSTIN starts with 29 (Karnataka)
    # Customer's GSTIN could be any state
    if not data['service_provider_gstin'] or not data['service_receiver_gstin']:
        all_gstins = re.findall(r'GSTIN:\s*' + gstin_pattern, text, re.IGNORECASE)
        for gstin in all_gstins:
            gstin = gstin.upper()
            if gstin.startswith('29') and 'AACCF0683K' in gstin:
                # This is Flipkart's GSTIN
                data['service_provider_gstin'] = gstin
            elif not data['service_receiver_gstin']:
                data['service_receiver_gstin'] = gstin
    
    # Extract Service Receiver Name (Business Name from BILLED TO section)
    receiver_patterns = [
        r'Business\s*Name:\s*([^\n]+)',
        r'BILLED\s*TO:.*?(?:Business\s*Name:|Display\s*Name:)\s*([^\n]+)',
    ]
    for pattern in receiver_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            data['service_receiver_name'] = match.group(1).strip()
            break
    
    # Extract Place of Supply/State Code
    pos_match = re.search(r'Place\s*of\s*Supply/State\s*Code:\s*([^\n,]+)', text, re.IGNORECASE)
    if pos_match:
        pos_text = pos_match.group(1).strip()
        # Extract state code like "IN-DL" -> "DL" or just "Delhi" -> extract code
        state_code_match = re.search(r'IN-([A-Z]{2})', pos_text)
        if state_code_match:
            data['place_of_supply_state_code'] = state_code_match.group(1)
        else:
            # Map common state names to codes
            state_map = {
                'delhi': '07', 'maharashtra': '27', 'karnataka': '29',
                'tamil nadu': '33', 'uttar pradesh': '09', 'gujarat': '24',
                'rajasthan': '08', 'west bengal': '19', 'telangana': '36'
            }
            for state, code in state_map.items():
                if state in pos_text.lower():
                    data['place_of_supply_state_code'] = code
                    break
    
    # Extract line items - Flipkart format has SAC codes, Description, Net Taxable Value, IGST Rate, IGST Amount, Total
    # For Commercial Credit Notes, format is simpler: Sr. No, Description, Net Amount
    
    if data['document_type'] == "CommercialCreditNote":
        # Simple format: Sr. No. Description Net Amount
        # Pattern: number followed by description and amount
        line_pattern = r'(\d+)\s+([A-Za-z\s]+(?:Fee|Discount|Recovery|Amount)?)\s+(\d+(?:,\d{3})*\.?\d*)\s*$'
        lines = text.split('\n')
        for line in lines:
            match = re.search(line_pattern, line.strip())
            if match:
                desc = match.group(2).strip()
                amount = normalize_amount(match.group(3))
                if amount and amount > 0:
                    data['line_items'].append({
                        "category_code_or_hsn": None,
                        "service_description": desc,
                        "fee_amount": amount,
                        "cgst_amount": None,
                        "sgst_amount": None,
                        "igst_amount": None,
                        "total_tax_amount": None,
                        "total_amount": amount,
                        "tax_rate_percent": None
                    })
        
        # Extract total for Commercial Credit Notes
        total_match = re.search(r'Total\s+(\d+(?:,\d{3})*\.?\d*)', text, re.IGNORECASE)
        if total_match:
            data['total_invoice_amount'] = normalize_amount(total_match.group(1))
            data['subtotal_fee_amount'] = data['total_invoice_amount']
    else:
        # Tax Invoice/Credit Note format with IGST
        # SAC codes are 6 digits like 998599, 996812, 998365
        # Pattern: SAC_CODE Description VALUE RATE TAX TOTAL
        
        # First, let's extract the line items table
        # Look for patterns like "998599 Collection Fee 5160.91 18.0 929.00 6089.91"
        line_patterns = [
            # SAC code at start, then description, then values
            r'(\d{6})\s+([A-Za-z\s]+(?:Fee|Recovery|Amount)?)\s+(\d+(?:,\d{3})*\.?\d*)\s+(\d+\.?\d*)\s+(\d+(?:,\d{3})*\.?\d*)\s+(\d+(?:,\d{3})*\.?\d*)',
            # Multi-line description handling (e.g., "Customer Add-ons\nAmount Recovery")
            r'(\d{6})\s+([A-Za-z][A-Za-z\s\-]+)\s*[\n\s]*([A-Za-z][A-Za-z\s]*)?[\n\s]*(\d+(?:,\d{3})*\.?\d*)\s+(\d+\.?\d*)\s+(\d+(?:,\d{3})*\.?\d*)\s+(\d+(?:,\d{3})*\.?\d*)',
        ]
        
        # Try to extract line items
        for pattern in line_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                for match in matches:
                    if len(match) == 6:
                        sac, desc, value, rate, tax, total = match
                        desc_clean = desc.strip()
                    elif len(match) == 7:
                        sac, desc1, desc2, value, rate, tax, total = match
                        desc_clean = f"{desc1.strip()} {desc2.strip() if desc2 else ''}".strip()
                    else:
                        continue
                    
                    fee = normalize_amount(value)
                    igst = normalize_amount(tax)
                    total_amt = normalize_amount(total)
                    tax_rate = normalize_amount(rate)
                    
                    if fee and fee > 0:
                        data['line_items'].append({
                            "category_code_or_hsn": sac.strip(),
                            "service_description": desc_clean,
                            "fee_amount": fee,
                            "cgst_amount": None,
                            "sgst_amount": None,
                            "igst_amount": igst,
                            "total_tax_amount": igst,
                            "total_amount": total_amt,
                            "tax_rate_percent": tax_rate
                        })
                break
        
        # If no line items found with complex pattern, try simpler extraction
        if not data['line_items']:
            # Extract SAC codes
            sac_codes = re.findall(r'\b(99\d{4})\b', text)
            unique_sacs = list(set(sac_codes))
            
            # Common Flipkart service descriptions
            # Common services: [
                'Collection Fee', 'Shipping Fee', 'Fixed Fee', 
                'Ad Services Fee', 'Customer Add-ons Amount Recovery',
                'Customer Add-ons Recovery', 'Amount Recovery'
            ]
            
            for sac in unique_sacs:
                data['line_items'].append({
                    "category_code_or_hsn": sac,
                    "service_description": None,
                    "fee_amount": None,
                    "cgst_amount": None,
                    "sgst_amount": None,
                    "igst_amount": None,
                    "total_tax_amount": None,
                    "total_amount": None,
                    "tax_rate_percent": 18.0  # Standard GST rate for services
                })
        
        # Extract totals from the Total row
        # Pattern: "Total 224684.89 40443.27 265128.16" or "Total 3073.63 553.25 3626.88"
        total_pattern = r'Total\s+(\d+(?:,\d{3})*\.?\d*)\s+(\d+(?:,\d{3})*\.?\d*)\s+(\d+(?:,\d{3})*\.?\d*)'
        total_match = re.search(total_pattern, text, re.IGNORECASE)
        if total_match:
            data['subtotal_fee_amount'] = normalize_amount(total_match.group(1))
            data['igst_amount'] = normalize_amount(total_match.group(2))
            data['total_tax_amount'] = normalize_amount(total_match.group(2))
            data['total_invoice_amount'] = normalize_amount(total_match.group(3))
        else:
            # Try alternate patterns
            subtotal_match = re.search(r'(?:Sub\s*Total|Taxable\s*Value|Net\s*Taxable)[:\s]*(?:Rs\.?|₹)?\s*(\d+(?:,\d{3})*\.?\d*)', text, re.IGNORECASE)
            if subtotal_match:
                data['subtotal_fee_amount'] = normalize_amount(subtotal_match.group(1))
            
            igst_match = re.search(r'IGST[:\s@\d%]*(?:Rs\.?|₹)?\s*(\d+(?:,\d{3})*\.?\d*)', text, re.IGNORECASE)
            if igst_match:
                data['igst_amount'] = normalize_amount(igst_match.group(1))
                data['total_tax_amount'] = data['igst_amount']
            
            grand_total_match = re.search(r'(?:Grand\s*)?Total[:\s]*(?:Rs\.?|₹)?\s*(\d+(?:,\d{3})*\.?\d*)', text, re.IGNORECASE)
            if grand_total_match:
                data['total_invoice_amount'] = normalize_amount(grand_total_match.group(1))
    
    return data

# ============== UNIVERSAL SMART EXTRACTOR ==============

def extract_all_amounts(text: str) -> List[float]:
    """Extract all monetary amounts from text"""
    # Match various amount formats: 1,234.56 or 1234.56 or Rs. 1,234 or ₹1234
    patterns = [
        r'(?:Rs\.?|INR|₹)\s*([\d,]+\.?\d*)',
        r'([\d,]+\.\d{2})\b',  # Numbers with exactly 2 decimal places
        r'\b(\d{1,3}(?:,\d{3})+\.?\d*)\b',  # Comma-formatted numbers
    ]
    amounts = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for m in matches:
            amt = normalize_amount(m)
            if amt and amt > 0:
                amounts.append(amt)
    return sorted(list(set(amounts)), reverse=True)

def extract_line_items_universal(text: str) -> List[Dict]:
    """Universal line item extractor that works with any invoice format"""
    line_items = []
    lines = text.split('\n')
    
    # Common service/fee keywords
    service_keywords = [
        'commission', 'fee', 'shipping', 'delivery', 'handling', 'service',
        'charges', 'penalty', 'incentive', 'subscription', 'marketing',
        'advertising', 'ad ', 'ads ', 'fulfilment', 'fulfillment', 'pick',
        'pack', 'storage', 'collection', 'payment', 'gateway', 'tech fee',
        'platform', 'closing', 'fixed', 'weight', 'forward', 'reverse',
        'return', 'refund', 'recovery', 'adjustment', 'discount', 'credit',
        'debit', 'charge', 'cost', 'value', 'amount', 'total'
    ]
    
    # Pattern 1: Description followed by amount (most common)
    # e.g., "Commission Fee    1234.56"
    # e.g., "Shipping Charges Rs. 500.00"
    for line in lines:
        line_clean = line.strip()
        if not line_clean or len(line_clean) < 5:
            continue
            
        # Check if line contains service keyword
        has_keyword = any(kw in line_clean.lower() for kw in service_keywords)
        
        if has_keyword:
            # Extract amounts from this line
            amounts = extract_all_amounts(line_clean)
            
            # Extract description (text before first number)
            desc_match = re.match(r'^([A-Za-z\s\-&/()]+)', line_clean)
            description = desc_match.group(1).strip() if desc_match else None
            
            # Extract HSN/SAC code if present
            hsn_match = re.search(r'\b(99\d{4}|\d{4})\b', line_clean)
            hsn_code = hsn_match.group(1) if hsn_match else None
            
            if description and amounts:
                # Last amount is usually total, second-last might be tax
                total = amounts[0] if amounts else None
                tax = amounts[1] if len(amounts) > 1 else None
                fee = amounts[2] if len(amounts) > 2 else (amounts[1] if len(amounts) > 1 else amounts[0] if amounts else None)
                
                line_items.append({
                    "category_code_or_hsn": hsn_code,
                    "service_description": description,
                    "fee_amount": fee,
                    "cgst_amount": None,
                    "sgst_amount": None,
                    "igst_amount": tax if tax and tax != total else None,
                    "total_tax_amount": tax if tax and tax != total else None,
                    "total_amount": total,
                    "tax_rate_percent": None
                })
    
    # Pattern 2: Table format with HSN/SAC codes
    # Look for rows with SAC code followed by description and amounts
    sac_pattern = r'(99\d{4})\s+(.+?)\s+([\d,]+\.?\d*)'
    sac_matches = re.findall(sac_pattern, text)
    for sac, desc, amount in sac_matches:
        if not any(item.get('category_code_or_hsn') == sac for item in line_items):
            line_items.append({
                "category_code_or_hsn": sac,
                "service_description": desc.strip()[:50],  # Limit description length
                "fee_amount": normalize_amount(amount),
                "cgst_amount": None,
                "sgst_amount": None,
                "igst_amount": None,
                "total_tax_amount": None,
                "total_amount": normalize_amount(amount),
                "tax_rate_percent": None
            })
    
    # If still no line items, try to extract any descriptive lines with amounts
    if not line_items:
        for line in lines:
            line_clean = line.strip()
            # Skip very short lines and headers
            if len(line_clean) < 10 or line_clean.upper() == line_clean:
                continue
            
            amounts = extract_all_amounts(line_clean)
            if amounts and amounts[0] > 10:  # Ignore tiny amounts
                # Get text part
                text_part = re.sub(r'[\d,\.₹]+', '', line_clean).strip()
                if len(text_part) > 3:
                    line_items.append({
                        "category_code_or_hsn": None,
                        "service_description": text_part[:60],
                        "fee_amount": amounts[-1] if len(amounts) > 1 else amounts[0],
                        "cgst_amount": None,
                        "sgst_amount": None,
                        "igst_amount": None,
                        "total_tax_amount": None,
                        "total_amount": amounts[0],
                        "tax_rate_percent": None
                    })
    
    return line_items

def extract_totals_universal(text: str) -> Dict[str, float]:
    """Universal total amount extractor"""
    totals = {
        'subtotal': None,
        'cgst': None,
        'sgst': None,
        'igst': None,
        'total_tax': None,
        'grand_total': None
    }
    
    # Patterns for different total formats
    patterns = {
        'grand_total': [
            r'Grand\s*Total[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Total\s*(?:Amount|Invoice|Payable)?[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Net\s*(?:Amount|Payable)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Amount\s*Payable[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ],
        'subtotal': [
            r'Sub\s*Total[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Taxable\s*(?:Value|Amount)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Net\s*Value[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Base\s*Amount[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ],
        'cgst': [
            r'CGST[:\s@]*(?:\d+%?)?[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Central\s*GST[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ],
        'sgst': [
            r'SGST[:\s@]*(?:\d+%?)?[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'State\s*GST[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ],
        'igst': [
            r'IGST[:\s@]*(?:\d+%?)?[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Integrated\s*GST[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ],
        'total_tax': [
            r'Total\s*(?:Tax|GST)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Tax\s*Amount[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ]
    }
    
    for key, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                totals[key] = normalize_amount(match.group(1))
                break
    
    # If no grand total found, look for the largest amount in the document
    if not totals['grand_total']:
        all_amounts = extract_all_amounts(text)
        if all_amounts:
            totals['grand_total'] = all_amounts[0]  # Largest amount
    
    # Calculate total_tax if not found
    if not totals['total_tax']:
        if totals['cgst'] and totals['sgst']:
            totals['total_tax'] = totals['cgst'] + totals['sgst']
        elif totals['igst']:
            totals['total_tax'] = totals['igst']
    
    return totals


# ============== REGEX-BASED FALLBACK EXTRACTOR ==============

def extract_with_regex(text: str, filename: str) -> Dict[str, Any]:
    """Universal extraction using smart regex patterns - works with any invoice format."""
    
    # Detect platform first
    platform = detect_platform(text)
    
    # Use specialized Flipkart extractor for Flipkart invoices
    if platform == "Flipkart":
        return extract_flipkart_invoice(text, filename)
    
    data = {
        "source_platform": platform,
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
        "_extraction_method": "universal_smart_regex"
    }
    
    # Extract invoice number - try multiple patterns
    inv_patterns = [
        r'Invoice\s*(?:No\.?|Number|#|:)\s*[:\s]*([A-Z0-9\-/]+)',
        r'(?:Tax\s*)?Invoice\s*[:\s]*([A-Z0-9\-/]+)',
        r'INV[:\s\-]*([A-Z0-9\-/]+)',
        r'Bill\s*(?:No\.?|Number|#)\s*[:\s]*([A-Z0-9\-/]+)',
        r'Document\s*(?:No\.?|Number)\s*[:\s]*([A-Z0-9\-/]+)',
        r'Credit\s*Note\s*(?:No\.?|#)\s*[:\s]*([A-Z0-9\-/]+)',
        r'Reference\s*(?:No\.?|Number)\s*[:\s]*([A-Z0-9\-/]+)',
    ]
    for pattern in inv_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            inv_num = match.group(1).strip()
            if len(inv_num) >= 4:  # Valid invoice numbers are at least 4 chars
                data['invoice_number'] = inv_num
                break
    
    # Extract date - multiple formats
    date_patterns = [
        r'(?:Invoice|Bill|Document)\s*Date[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        r'Date[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})',
        r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
        r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]*\d{4})',
        r'(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})',  # YYYY-MM-DD format
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['invoice_date'] = normalize_date(match.group(1))
            break
    
    # Extract GSTIN (15 character alphanumeric Indian GST number)
    gstin_pattern = r'\b(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1})\b'
    gstin_matches = re.findall(gstin_pattern, text, re.IGNORECASE)
    unique_gstins = list(dict.fromkeys([g.upper() for g in gstin_matches]))
    if len(unique_gstins) >= 1:
        data['service_provider_gstin'] = unique_gstins[0]
    if len(unique_gstins) >= 2:
        data['service_receiver_gstin'] = unique_gstins[1]
    
    # Extract company names based on platform
    if platform == 'Amazon':
        data['service_provider_name'] = 'Amazon Seller Services Private Limited'
    elif platform == 'Meesho':
        data['service_provider_name'] = 'Meesho Technologies Pvt Ltd'
    elif platform == 'Fashnear':
        data['service_provider_name'] = 'Fashnear Technologies Pvt Ltd'
    else:
        # Try to extract company name
        company_patterns = [
            r'(?:From|Seller|Provider|Billed\s*By)[:\s]*([A-Z][A-Za-z\s&]+(?:Pvt\.?|Private|Ltd\.?|Limited|Inc\.?|LLC)?)',
            r'([A-Z][A-Za-z\s&]+(?:Private\s*Limited|Pvt\.?\s*Ltd\.?|Limited|Inc\.?))',
        ]
        for pattern in company_patterns:
            match = re.search(pattern, text)
            if match:
                data['service_provider_name'] = match.group(1).strip()[:60]
                break
    
    # Extract totals using universal extractor
    totals = extract_totals_universal(text)
    data['subtotal_fee_amount'] = totals['subtotal']
    data['cgst_amount'] = totals['cgst']
    data['sgst_amount'] = totals['sgst']
    data['igst_amount'] = totals['igst']
    data['total_tax_amount'] = totals['total_tax']
    data['total_invoice_amount'] = totals['grand_total']
    
    # Extract line items using universal extractor
    data['line_items'] = extract_line_items_universal(text)
    
    # Only add HSN codes if no line items were found
    if not data['line_items']:
        hsn_pattern = r'\b(99\d{4})\b'
        hsn_matches = re.findall(hsn_pattern, text)
        
        for hsn in set(hsn_matches):
            data['line_items'].append({
                "category_code_or_hsn": hsn,
                "service_description": "Service Fee",
                "fee_amount": None,
                "cgst_amount": None,
                "sgst_amount": None,
                "igst_amount": None,
                "total_tax_amount": None,
                "total_amount": data['total_invoice_amount'],  # Use grand total if available
                "tax_rate_percent": 18.0
            })
    
    return data

# ============== LLM EXTRACTION ==============

async def extract_invoice_with_llm(text: str, filename: str, api_key: str) -> Dict[str, Any]:
    """Use GPT-5.2 to extract structured invoice data."""
    
    if not LLM_AVAILABLE or not api_key:
        logger.info("LLM not available, using regex extraction")
        return extract_with_regex(text, filename)
    
    system_prompt = """You are an expert invoice data extractor for Indian e-commerce platforms. Extract structured data from invoice text.

IMPORTANT RULES:
1. Do NOT hallucinate. If a field is not found, use null.
2. For dates, normalize to dd/mm/yyyy format.
3. For amounts, remove commas and return numeric values with 2 decimals.
4. Detect platform:
   - "Flipkart" if Flipkart Internet Private Limited
   - "Amazon" if Amazon Seller Services
   - "Meesho" if Meesho Technologies
   - "Fashnear" if Fashnear Technologies
   - Otherwise "Unknown"
5. document_type should be:
   - "Invoice" for Commission/Tax Invoice
   - "CreditNote" for Credit Note (with tax)
   - "CommercialCreditNote" for Commercial Credit Note (no tax)

FLIPKART INVOICE STRUCTURE:
- BILLED FROM: Flipkart Internet Private Limited with GSTIN (service provider)
- BILLED TO: Customer business details with GSTIN (service receiver)
- Invoice # or Credit Note #: The document number (e.g., FKRKA26000290632, FKCKA26000190312, ICNDL26000031306)
- Date: Invoice Date or Credit Note Date in DD-MM-YYYY format
- Line items table has: Service Accounting Codes (SAC like 998599, 996812), Description, Net Taxable Value, IGST Rate (usually 18%), IGST Amount, Total
- Common services: Collection Fee, Shipping Fee, Fixed Fee, Ad Services Fee, Customer Add-ons Amount Recovery
- Total row has: Total Net Taxable Value, Total IGST, Grand Total

Return ONLY valid JSON matching this schema:
{
    "source_platform": "Amazon|Meesho|Fashnear|Flipkart|Unknown",
    "document_type": "Invoice|CreditNote|CommercialCreditNote",
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
                except Exception:
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
