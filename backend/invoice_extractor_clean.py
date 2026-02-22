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

# Import universal extractor
from universal_extractor import universal_extract, normalize_amount, normalize_date, detect_platform

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


# SAC Code to Description mapping (common e-commerce services)
SAC_DESCRIPTIONS = {
    "998365": "Commission/Marketplace Fee",
    "996799": "Logistics/Shipping Fee", 
    "998599": "Payment Gateway/Collection Fee",
    "996812": "Courier/Delivery Service",
    "998361": "Business Support Service",
    "998314": "Advertising Service",
    "998313": "Marketing Service",
    "997212": "Warehousing/Fulfillment",
    "996511": "Transportation Fee",
}


def extract_meesho_invoice(text: str, filename: str) -> Dict[str, Any]:
    """
    Specialized extraction for Meesho invoices.
    Meesho invoices have:
    - SAC codes: 998365 (Commission), 996799 (Logistics), 998599 (Payment)
    - IGST for inter-state, CGST+SGST for intra-state
    - Table format with HSN/SAC, Description, Taxable Value, Tax Rate, Tax Amount, Total
    """
    data = {
        "source_platform": "Meesho",
        "document_type": "Invoice",
        "invoice_number": None,
        "invoice_date": None,
        "service_provider_name": "Meesho Technologies Pvt Ltd",
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
        "_extraction_method": "meesho_regex"
    }
    
    # Detect document type
    if "credit note" in text.lower():
        data['document_type'] = "CreditNote"
    
    # Extract Invoice Number - Meesho format: TI/01/26/1599650 or similar
    inv_patterns = [
        r'Invoice\s*(?:No\.?|Number|#)[:\s]*([A-Z0-9/\-]+)',
        r'(TI/\d+/\d+/\d+)',  # Meesho specific format
        r'Document\s*No[:\s]*([A-Z0-9/\-]+)',
    ]
    for pattern in inv_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['invoice_number'] = match.group(1).strip()
            break
    
    # Extract Date
    date_patterns = [
        r'(?:Invoice|Document)\s*Date[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
        r'Date[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['invoice_date'] = normalize_date(match.group(1))
            break
    
    # Extract GSTINs
    gstin_pattern = r'(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1})'
    gstin_matches = re.findall(gstin_pattern, text, re.IGNORECASE)
    unique_gstins = list(dict.fromkeys([g.upper() for g in gstin_matches]))
    
    # Meesho's GSTIN usually starts with 29 (Karnataka)
    for gstin in unique_gstins:
        if gstin.startswith('29') and 'AARCM9332R' in gstin:
            data['service_provider_gstin'] = gstin
        elif not data['service_receiver_gstin']:
            data['service_receiver_gstin'] = gstin
    
    if not data['service_provider_gstin'] and unique_gstins:
        data['service_provider_gstin'] = unique_gstins[0]
    if not data['service_receiver_gstin'] and len(unique_gstins) > 1:
        data['service_receiver_gstin'] = unique_gstins[1]
    
    # Extract line items - Look for SAC code followed by amounts
    # Pattern: SAC_CODE ... AMOUNT ... TAX_RATE ... TAX_AMOUNT ... TOTAL
    lines = text.split('\n')
    
    for line in lines:
        line_clean = line.strip()
        
        # Look for SAC codes in the line
        for sac_code, description in SAC_DESCRIPTIONS.items():
            if sac_code in line_clean:
                # Remove SAC code from line to avoid it being counted as amount
                line_without_sac = line_clean.replace(sac_code, '')
                
                # Extract all amounts from this line in order of appearance
                amount_pattern = r'(\d+(?:,\d{3})*\.\d{2})'  # Match amounts with exactly 2 decimal places
                found_amounts = re.findall(amount_pattern, line_without_sac)
                amounts_in_order = [normalize_amount(a) for a in found_amounts if normalize_amount(a)]
                
                fee_amount = None
                tax_amount = None
                total_amount = None
                tax_rate = None
                
                # Get tax rate (usually 9 or 18)
                rate_match = re.search(r'@?\s*(\d+)\s*%', line_clean)
                if rate_match:
                    tax_rate = float(rate_match.group(1))
                
                # Amounts usually appear in order: Taxable Value, Tax Amount, Total
                if amounts_in_order:
                    if len(amounts_in_order) >= 3:
                        fee_amount = amounts_in_order[0]  # First = Taxable/Fee
                        tax_amount = amounts_in_order[1]  # Second = Tax
                        total_amount = amounts_in_order[2]  # Third = Total
                    elif len(amounts_in_order) == 2:
                        # Smaller is usually fee, check if larger = smaller * 1.18 (with tax)
                        smaller = min(amounts_in_order)
                        larger = max(amounts_in_order)
                        if abs(larger - smaller * 1.18) < larger * 0.05:  # ~18% tax
                            fee_amount = smaller
                            total_amount = larger
                            tax_amount = larger - smaller
                        else:
                            fee_amount = amounts_in_order[0]
                            total_amount = amounts_in_order[1]
                    elif len(amounts_in_order) == 1:
                        fee_amount = amounts_in_order[0]
                        total_amount = amounts_in_order[0]
                
                if fee_amount or total_amount:  # Only add if we found some amounts
                    data['line_items'].append({
                        "category_code_or_hsn": sac_code,
                        "service_description": description,
                        "fee_amount": fee_amount,
                        "cgst_amount": tax_amount / 2 if tax_amount and tax_rate == 9 else None,
                        "sgst_amount": tax_amount / 2 if tax_amount and tax_rate == 9 else None,
                        "igst_amount": tax_amount if tax_amount and (tax_rate == 18 or not tax_rate) else None,
                        "total_tax_amount": tax_amount,
                        "total_amount": total_amount,
                        "tax_rate_percent": tax_rate or 18.0
                    })
                break  # Found this SAC, move to next line
    
    # If no line items found, try simpler extraction
    if not data['line_items']:
        for sac_code, description in SAC_DESCRIPTIONS.items():
            if sac_code in text:
                # Find amount near SAC code
                pattern = rf'{sac_code}\s+.*?(\d+(?:,\d{{3}})*\.?\d*)'
                match = re.search(pattern, text)
                amount = normalize_amount(match.group(1)) if match else None
                
                data['line_items'].append({
                    "category_code_or_hsn": sac_code,
                    "service_description": description,
                    "fee_amount": amount,
                    "cgst_amount": None,
                    "sgst_amount": None,
                    "igst_amount": None,
                    "total_tax_amount": None,
                    "total_amount": amount,
                    "tax_rate_percent": 18.0
                })
    
    # Extract totals
    totals = extract_totals_universal(text)
    data['subtotal_fee_amount'] = totals['subtotal']
    data['cgst_amount'] = totals['cgst']
    data['sgst_amount'] = totals['sgst']
    data['igst_amount'] = totals['igst']
    data['total_tax_amount'] = totals['total_tax']
    data['total_invoice_amount'] = totals['grand_total']
    
    # If we have line items but no totals, calculate from line items
    if data['line_items'] and not data['total_invoice_amount']:
        data['subtotal_fee_amount'] = sum(item.get('fee_amount') or 0 for item in data['line_items'])
        data['total_tax_amount'] = sum(item.get('total_tax_amount') or 0 for item in data['line_items'])
        data['total_invoice_amount'] = sum(item.get('total_amount') or 0 for item in data['line_items'])
    
    return data


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
    
    # Use the new universal extractor for all platforms
    return universal_extract(text, filename)
