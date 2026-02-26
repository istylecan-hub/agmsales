# Universal Invoice Extractor - 4-Stage Hybrid Pipeline
# Stage A: PDF Text + OCR + Layout signals
# Stage B: Template detection
# Stage C: Template-specific parsing
# Stage D: LLM fallback (when needed)

import re
import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field, asdict

# PDF processing
import pdfplumber
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Import template-specific parsers
from parsers import (
    BaseParser, NormalizedInvoice, LineItem, ValidationResult,
    AmazonParser, FlipkartParser, MeeshoParser, VMartParser,
    AceVectorParser, MyntraParser, FashnearParser, JioMartParser, GenericParser
)

logger = logging.getLogger(__name__)


# ==================== STAGE A: Document Content Extraction ====================

@dataclass
class DocumentContent:
    """Result of document content extraction"""
    pages_text: List[str] = field(default_factory=list)
    full_text: str = ""
    is_scanned: bool = False
    confidence: float = 1.0
    anchors_found: List[str] = field(default_factory=list)
    extraction_method: str = "pdfplumber"
    page_count: int = 0
    tables_found: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def extract_document_content(pdf_path: str) -> DocumentContent:
    """
    Stage A: Extract text content from PDF with OCR fallback.
    
    Strategy:
    1. Try pdfplumber first (best for structured PDFs with tables)
    2. If text is insufficient, try PyPDF2
    3. If still insufficient and OCR available, use OCR
    """
    result = DocumentContent()
    
    try:
        # Method 1: pdfplumber (preferred for tables)
        with pdfplumber.open(pdf_path) as pdf:
            result.page_count = len(pdf.pages)
            
            for page in pdf.pages:
                # Extract text
                page_text = page.extract_text() or ""
                result.pages_text.append(page_text)
                
                # Count tables
                tables = page.extract_tables()
                result.tables_found += len(tables) if tables else 0
            
            result.full_text = "\n".join(result.pages_text)
            result.extraction_method = "pdfplumber"
        
        # Check if extraction was successful
        if len(result.full_text.strip()) < 100:
            # Try PyPDF2 as fallback
            if PYPDF2_AVAILABLE:
                result = _extract_with_pypdf2(pdf_path, result)
        
        # Detect key anchors
        result.anchors_found = _detect_anchors(result.full_text)
        
        # Check if we need OCR
        needs_ocr = (
            len(result.full_text.strip()) < 100 or 
            len(result.anchors_found) < 2
        )
        
        if needs_ocr and OCR_AVAILABLE:
            logger.info(f"Text extraction insufficient ({len(result.full_text)} chars), attempting OCR...")
            result = _extract_with_ocr(pdf_path, result)
            result.is_scanned = True
        
        # Calculate confidence based on anchors found
        if len(result.anchors_found) >= 5:
            result.confidence = 1.0
        elif len(result.anchors_found) >= 3:
            result.confidence = 0.8
        elif len(result.anchors_found) >= 1:
            result.confidence = 0.6
        else:
            result.confidence = 0.4
        
    except Exception as e:
        logger.error(f"Document extraction failed: {e}")
        result.confidence = 0.0
    
    return result


def _extract_with_pypdf2(pdf_path: str, result: DocumentContent) -> DocumentContent:
    """Fallback extraction using PyPDF2"""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            pages_text = []
            for page in reader.pages:
                text = page.extract_text() or ""
                pages_text.append(text)
            
            combined_text = "\n".join(pages_text)
            
            # Only use if better than pdfplumber result
            if len(combined_text.strip()) > len(result.full_text.strip()):
                result.pages_text = pages_text
                result.full_text = combined_text
                result.extraction_method = "pypdf2"
    except Exception as e:
        logger.error(f"PyPDF2 extraction failed: {e}")
    
    return result


def _extract_with_ocr(pdf_path: str, result: DocumentContent) -> DocumentContent:
    """OCR fallback for scanned PDFs"""
    try:
        images = convert_from_path(pdf_path)
        ocr_pages = []
        
        for image in images:
            ocr_text = pytesseract.image_to_string(image)
            ocr_pages.append(ocr_text)
        
        ocr_full_text = "\n".join(ocr_pages)
        
        # Use OCR result if it's better
        if len(ocr_full_text.strip()) > len(result.full_text.strip()):
            result.pages_text = ocr_pages
            result.full_text = ocr_full_text
            result.extraction_method = "ocr"
            result.anchors_found = _detect_anchors(ocr_full_text)
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
    
    return result


def _detect_anchors(text: str) -> List[str]:
    """Detect key invoice anchors in text"""
    anchors = []
    text_lower = text.lower()
    
    anchor_patterns = [
        ('invoice', r'invoice'),
        ('credit_note', r'credit\s*note'),
        ('gstin', r'\d{2}[a-z]{5}\d{4}[a-z]{1}[a-z\d]{1}z[a-z\d]{1}'),
        ('tax_invoice', r'tax\s*invoice'),
        ('total', r'total'),
        ('igst', r'igst'),
        ('cgst', r'cgst'),
        ('sgst', r'sgst'),
        ('sac_code', r'99\d{4}'),
        ('hsn_code', r'hsn'),
        ('date', r'date'),
        ('amount', r'amount'),
        ('bill_to', r'bill\s*(?:to|ed)'),
        ('place_of_supply', r'place\s*of\s*supply'),
    ]
    
    for anchor_name, pattern in anchor_patterns:
        if re.search(pattern, text_lower):
            anchors.append(anchor_name)
    
    return anchors


# ==================== STAGE B: Template Detection ====================

# Template detection anchors
TEMPLATE_ANCHORS = {
    'AMAZON_TAX_INVOICE': [
        'amazon seller services',
        'amazon.in',
        'AAICA3918J'
    ],
    'AMAZON_CREDIT_NOTE': [
        'amazon seller services',
        'credit note number',
        'AAICA3918J'
    ],
    'FLIPKART_COMMISSION_TAX_INVOICE': [
        'flipkart internet',
        'AACCF0683K',
        'commission'
    ],
    'FLIPKART_CREDIT_NOTE': [
        'flipkart internet',
        'credit note',
        'FKCKA'
    ],
    'FLIPKART_COMMERCIAL_CREDIT_NOTE': [
        'flipkart internet',
        'commercial credit note',
        'ICNDL'
    ],
    'MEESHO_TAX_INVOICE': [
        'meesho technologies',
        'AARCM9332R',
        'TI/'
    ],
    'MEESHO_CREDIT_NOTE': [
        'meesho technologies',
        'credit note',
        'AARCM9332R'
    ],
    'VMART_TAX_INVOICE': [
        'v-mart retail',
        'AABCV7206K',
        'COM/'
    ],
    'ACEVECTOR_TAX_INVOICE': [
        'acevector limited',
        'AABCJ8820B',
        'monetization'
    ],
    'MYNTRA_TAX_INVOICE': [
        'myntra designs',
        'AABCM1518R'
    ],
    'MYNTRA_CREDIT_NOTE': [
        'myntra designs',
        'credit note',
        'AABCM1518R'
    ],
    'FASHNEAR_TAX_INVOICE': [
        'fashnear technologies',
        'AADCF8221E'
    ],
    'FASHNEAR_CREDIT_NOTE': [
        'fashnear technologies',
        'credit note',
        'CN/'
    ],
    'JIOMART_TAX_INVOICE': [
        'reliance retail',
        'jiomart',
        'AAACR'
    ],
    'JIOMART_CREDIT_NOTE': [
        'reliance retail',
        'credit note',
        'jiomart'
    ],
}


def detect_template(full_text: str) -> str:
    """
    Stage B: Detect invoice template based on anchor keywords.
    
    Returns template_id string like:
    - AMAZON_TAX_INVOICE
    - AMAZON_CREDIT_NOTE
    - FLIPKART_COMMISSION_TAX_INVOICE
    - MEESHO_TAX_INVOICE
    - VMART_TAX_INVOICE
    - ACEVECTOR_TAX_INVOICE
    - MYNTRA_TAX_INVOICE
    - FASHNEAR_TAX_INVOICE
    - UNKNOWN_GENERIC_GST
    """
    text_lower = full_text.lower()
    
    # Score each template
    scores = {}
    for template_id, anchors in TEMPLATE_ANCHORS.items():
        score = 0
        for anchor in anchors:
            if anchor.lower() in text_lower:
                score += 1
        scores[template_id] = score
    
    # Find best match
    best_template = max(scores, key=scores.get)
    best_score = scores[best_template]
    
    # Require at least 2 anchors for a confident match
    if best_score >= 2:
        return best_template
    elif best_score == 1:
        # Check for document type qualifiers
        if 'credit note' in text_lower:
            if 'amazon' in text_lower:
                return 'AMAZON_CREDIT_NOTE'
            elif 'flipkart' in text_lower:
                if 'commercial' in text_lower:
                    return 'FLIPKART_COMMERCIAL_CREDIT_NOTE'
                return 'FLIPKART_CREDIT_NOTE'
            elif 'fashnear' in text_lower:
                return 'FASHNEAR_CREDIT_NOTE'
        return best_template
    
    return 'UNKNOWN_GENERIC_GST'


# ==================== STAGE C: Template-Specific Parsing ====================

# Parser mapping
TEMPLATE_PARSERS = {
    'AMAZON_TAX_INVOICE': AmazonParser,
    'AMAZON_CREDIT_NOTE': AmazonParser,
    'FLIPKART_COMMISSION_TAX_INVOICE': FlipkartParser,
    'FLIPKART_CREDIT_NOTE': FlipkartParser,
    'FLIPKART_COMMERCIAL_CREDIT_NOTE': FlipkartParser,
    'MEESHO_TAX_INVOICE': MeeshoParser,
    'MEESHO_CREDIT_NOTE': MeeshoParser,
    'VMART_TAX_INVOICE': VMartParser,
    'VMART_CREDIT_NOTE': VMartParser,
    'ACEVECTOR_TAX_INVOICE': AceVectorParser,
    'ACEVECTOR_CREDIT_NOTE': AceVectorParser,
    'MYNTRA_TAX_INVOICE': MyntraParser,
    'MYNTRA_CREDIT_NOTE': MyntraParser,
    'FASHNEAR_TAX_INVOICE': FashnearParser,
    'FASHNEAR_CREDIT_NOTE': FashnearParser,
    'UNKNOWN_GENERIC_GST': GenericParser,
}


def parse_with_template(text: str, template_id: str, pages_text: List[str] = None) -> Tuple[NormalizedInvoice, ValidationResult]:
    """
    Stage C: Parse using template-specific parser.
    
    Returns tuple of (NormalizedInvoice, ValidationResult)
    """
    # Get appropriate parser
    parser_class = TEMPLATE_PARSERS.get(template_id, GenericParser)
    
    # Create parser instance
    parser = parser_class(text, pages_text)
    
    # Parse
    invoice = parser.parse()
    
    # Validate
    validation = parser.validate_and_reconcile()
    
    return invoice, validation


# ==================== STAGE D: LLM Fallback ====================

async def llm_fallback_extraction(text: str, template_id: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Stage D: LLM fallback for when regex parsing fails.
    
    Only used when:
    - Template is UNKNOWN_GENERIC_GST
    - Validation fails with status='fail'
    """
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except ImportError:
        logger.warning("LLM not available for fallback")
        return None
    
    if not api_key:
        logger.warning("No API key provided for LLM fallback")
        return None
    
    system_prompt = """You are an expert invoice data extractor for Indian GST invoices. Extract structured data from the invoice text.

IMPORTANT:
1. Do NOT hallucinate - if a field is not found, use null
2. Dates should be dd/mm/yyyy format
3. Amounts should be numeric with 2 decimal places
4. Extract ALL line items from the invoice table
5. Negative amounts indicate credit notes

Return ONLY valid JSON matching this schema:
{
    "source_platform": "string",
    "document_type": "Invoice|CreditNote",
    "invoice_number": "string or null",
    "invoice_date": "dd/mm/yyyy or null",
    "service_provider_name": "string or null",
    "service_provider_gstin": "string or null",
    "service_receiver_name": "string or null",
    "service_receiver_gstin": "string or null",
    "place_of_supply_state_code": "2-digit code or null",
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
        import uuid
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"invoice-llm-{uuid.uuid4()}",
            system_message=system_prompt
        ).with_model("openai", "gpt-5.2")
        
        user_message = UserMessage(
            text=f"Extract structured data from this invoice:\n\n{text[:12000]}"
        )
        
        response = await chat.send_message(user_message)
        
        # Parse JSON from response
        import json
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            data = json.loads(json_match.group())
            data['_extraction_method'] = 'llm'
            return data
        
    except Exception as e:
        logger.error(f"LLM fallback failed: {e}")
    
    return None


# ==================== MAIN EXTRACTION FUNCTION ====================

def validate_and_reconcile(invoice: NormalizedInvoice) -> ValidationResult:
    """
    Validate totals reconciliation.
    
    Checks:
    1. sum(line_items.fee_amount) ≈ subtotal_fee_amount
    2. sum(line_items.tax) ≈ total_tax_amount
    3. subtotal_fee_amount + total_tax_amount ≈ total_invoice_amount
    """
    result = ValidationResult()
    tolerance = 0.5  # Allow 0.5 INR difference
    
    # Check line items sum vs subtotal
    if invoice.line_items:
        fee_sum = sum(
            (item.fee_amount or 0) if isinstance(item, LineItem) else (item.get('fee_amount') or 0)
            for item in invoice.line_items
        )
        if invoice.subtotal_fee_amount:
            diff = abs(fee_sum - invoice.subtotal_fee_amount)
            if diff > tolerance:
                result.fee_sum_matches = False
                result.issues.append(f"Fee sum mismatch: items={fee_sum:.2f}, subtotal={invoice.subtotal_fee_amount:.2f}")
        
        # Check tax sum
        tax_sum = sum(
            (item.total_tax_amount or 0) if isinstance(item, LineItem) else (item.get('total_tax_amount') or 0)
            for item in invoice.line_items
        )
        if invoice.total_tax_amount:
            diff = abs(tax_sum - invoice.total_tax_amount)
            if diff > tolerance:
                result.tax_sum_matches = False
                result.issues.append(f"Tax sum mismatch: items={tax_sum:.2f}, total_tax={invoice.total_tax_amount:.2f}")
    
    # Check subtotal + tax = total
    if invoice.subtotal_fee_amount and invoice.total_tax_amount and invoice.total_invoice_amount:
        expected_total = invoice.subtotal_fee_amount + invoice.total_tax_amount
        diff = abs(expected_total - invoice.total_invoice_amount)
        if diff > tolerance:
            result.total_matches = False
            result.issues.append(f"Total mismatch: subtotal+tax={expected_total:.2f}, total={invoice.total_invoice_amount:.2f}")
    
    # Set status
    if not result.fee_sum_matches or not result.tax_sum_matches or not result.total_matches:
        if len(result.issues) > 2:
            result.status = "fail"
        else:
            result.status = "warn"
    
    return result


def universal_extract(text: str, filename: str, pages_text: List[str] = None) -> Dict[str, Any]:
    """
    Main extraction function using the 4-stage hybrid pipeline.
    
    Args:
        text: Full extracted text from PDF
        filename: Original filename for context
        pages_text: Optional list of text per page
    
    Returns:
        Dictionary with extracted invoice data
    """
    # Stage B: Detect template
    template_id = detect_template(text)
    logger.info(f"Detected template: {template_id} for {filename}")
    
    # Stage C: Parse with template-specific parser
    invoice, validation = parse_with_template(text, template_id, pages_text)
    
    # Build result dictionary
    result = invoice.to_dict()
    result['_template_id'] = template_id
    result['_extraction_method'] = invoice.extraction_method
    result['_validation'] = validation.to_dict()
    result['_source_file'] = filename
    
    return result


async def universal_extract_async(
    text: str, 
    filename: str, 
    pages_text: List[str] = None,
    use_llm: bool = True,
    api_key: str = None
) -> Dict[str, Any]:
    """
    Async version with LLM fallback support.
    """
    # Stage B: Detect template
    template_id = detect_template(text)
    logger.info(f"Detected template: {template_id} for {filename}")
    
    # Stage C: Parse with template-specific parser
    invoice, validation = parse_with_template(text, template_id, pages_text)
    
    # Stage D: LLM fallback if needed
    if use_llm and api_key:
        should_use_llm = (
            template_id == 'UNKNOWN_GENERIC_GST' or
            validation.status == 'fail' or
            not invoice.line_items
        )
        
        if should_use_llm:
            logger.info(f"Using LLM fallback for {filename} (template={template_id}, status={validation.status})")
            llm_result = await llm_fallback_extraction(text, template_id, api_key)
            
            if llm_result:
                # Merge LLM results (prefer LLM for missing fields)
                invoice_dict = invoice.to_dict()
                for key, value in llm_result.items():
                    if key.startswith('_'):
                        continue
                    if value is not None and (invoice_dict.get(key) is None or key == 'line_items'):
                        invoice_dict[key] = value
                
                # Re-validate
                temp_invoice = NormalizedInvoice(**{k: v for k, v in invoice_dict.items() if not k.startswith('_')})
                validation = validate_and_reconcile(temp_invoice)
                
                invoice_dict['_template_id'] = template_id
                invoice_dict['_extraction_method'] = 'hybrid_llm'
                invoice_dict['_validation'] = validation.to_dict()
                invoice_dict['_source_file'] = filename
                
                return invoice_dict
    
    # Build result dictionary
    result = invoice.to_dict()
    result['_template_id'] = template_id
    result['_extraction_method'] = invoice.extraction_method
    result['_validation'] = validation.to_dict()
    result['_source_file'] = filename
    
    return result


# ==================== HELPER FUNCTIONS (for backward compatibility) ====================

def normalize_amount(amount_str: Any) -> Optional[float]:
    """Convert string amount to float."""
    return BaseParser.normalize_amount(amount_str)


def normalize_date(date_str: str) -> Optional[str]:
    """Normalize date to dd/mm/yyyy."""
    return BaseParser.normalize_date(date_str)


def detect_platform(text: str) -> str:
    """Detect invoice platform (backward compatible)."""
    template_id = detect_template(text)
    
    if 'AMAZON' in template_id:
        return 'Amazon'
    elif 'FLIPKART' in template_id:
        return 'Flipkart'
    elif 'MEESHO' in template_id:
        return 'Meesho'
    elif 'VMART' in template_id:
        return 'V-Mart'
    elif 'ACEVECTOR' in template_id:
        return 'AceVector'
    elif 'MYNTRA' in template_id:
        return 'Myntra'
    elif 'FASHNEAR' in template_id:
        return 'Fashnear'
    
    return 'Unknown'
