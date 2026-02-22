# Universal Invoice Extractor - Final Version
# Supports: Flipkart, Amazon, Meesho, V-Mart, AceVector/Snapdeal, and any other platform

import re
from typing import Dict, Any, List, Optional
from datetime import datetime

# ============== SAC/HSN CODE TO DESCRIPTION MAPPING ==============
SAC_DESCRIPTIONS = {
    # Commission & Marketplace Fees
    "998365": "Commission/Marketplace Fee",
    "996211": "Business & Production Services",
    
    # Logistics & Shipping
    "996799": "Logistics/Shipping Fee",
    "996812": "Courier/Delivery Service",
    "996511": "Transportation Fee",
    "997212": "Warehousing/Fulfillment",
    
    # Payment & Collection
    "998599": "Payment/Collection Fee",
    
    # Advertising & Marketing
    "998314": "Advertising Service",
    "998313": "Marketing Service",
    
    # Other Services
    "998361": "Business Support Service",
    "998399": "Other Business Services",
}

# Platform-specific provider names
PLATFORM_PROVIDERS = {
    "flipkart": "Flipkart Internet Private Limited",
    "amazon": "Amazon Seller Services Private Limited",
    "meesho": "Meesho Technologies Private Limited",
    "vmart": "V-Mart Retail Limited",
    "acevector": "AceVector Limited",
    "snapdeal": "AceVector Limited",
}


def normalize_amount(amount_str: str) -> Optional[float]:
    """Convert string amount to float, handling various formats."""
    if not amount_str:
        return None
    try:
        # Remove currency symbols, commas, spaces
        cleaned = re.sub(r'[₹,\s]', '', str(amount_str))
        cleaned = cleaned.replace('INR', '').replace('Rs.', '').replace('Rs', '').strip()
        if cleaned:
            return round(float(cleaned), 2)
    except (ValueError, TypeError):
        pass
    return None


def normalize_date(date_str: str) -> Optional[str]:
    """Normalize date to dd/mm/yyyy format."""
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    formats = [
        '%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y',
        '%Y-%m-%d', '%Y/%m/%d',
        '%d-%m-%y', '%d/%m/%y',
        '%d %b %Y', '%d %B %Y',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%d/%m/%Y')
        except ValueError:
            continue
    
    return date_str


def detect_platform(text: str) -> str:
    """Detect source platform from invoice text."""
    text_lower = text.lower()
    
    # Check V-Mart first (specific company name)
    if "v-mart" in text_lower or "v mart" in text_lower or "vmart" in text_lower:
        return "VMart"
    # Check Meesho
    elif "meesho" in text_lower:
        return "Meesho"
    elif "flipkart" in text_lower:
        return "Flipkart"
    elif "amazon seller services" in text_lower or "amazon.in" in text_lower:
        return "Amazon"
    elif "acevector" in text_lower or "snapdeal" in text_lower:
        return "Snapdeal"
    elif "fashnear" in text_lower:
        return "Fashnear"
    
    return "Unknown"


def extract_gstin(text: str) -> List[str]:
    """Extract all GSTINs from text."""
    pattern = r'\b(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1})\b'
    matches = re.findall(pattern, text, re.IGNORECASE)
    return list(dict.fromkeys([g.upper() for g in matches]))  # Remove duplicates, preserve order


def extract_invoice_number(text: str, platform: str) -> Optional[str]:
    """Extract invoice number based on platform."""
    
    # Platform-specific patterns first (more reliable)
    platform_patterns = {
        'Flipkart': [
            r'Credit\s*Note\s*#[:\s]*([A-Z0-9]+)',
            r'Invoice\s*#[:\s]*([A-Z0-9]+)',
            r'(FKCKA\d+)',
            r'(FKRKA\d+)',
            r'(ICNDL\d+)',
        ],
        'Amazon': [
            r'Invoice\s*No[:\.\s]*([A-Z]{2}-\d+-\d+)',
            r'(KA-\d+-\d+)',
            r'(DL-\d+-\d+)',
            r'([A-Z]{2}-\d{4}-\d+)',
        ],
        'Meesho': [
            r'Invoice\s*No[:\.\s]*(TI/\d+/\d+/\d+)',
            r'(TI/\d+/\d+/\d+)',
        ],
        'VMart': [
            r'Invoice\s*No[:\.\s]*(COM/\d+/IN\d+)',
            r'(COM/\d+/IN\d+)',
        ],
        'Snapdeal': [
            r'Invoice\s*No[:\.\s]*(\d+[A-Z]+/IN/\d+)',
            r'(\d+[A-Z]+/IN/\d+)',
            r'Invoice\s*Number[:\s]*(\d+)',
        ],
    }
    
    # Try platform-specific patterns first
    if platform in platform_patterns:
        for pattern in platform_patterns[platform]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                inv_num = match.group(1).strip()
                if len(inv_num) >= 4:
                    return inv_num
    
    # Generic patterns
    generic_patterns = [
        r'(?:Invoice|Credit\s*Note)\s*(?:No\.?|Number|#)[:\s]*([A-Z0-9/\-]+)',
        r'Document\s*(?:No\.?|Number)[:\s]*([A-Z0-9/\-]+)',
    ]
    
    for pattern in generic_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            inv_num = match.group(1).strip()
            # Filter out common false matches
            if inv_num.lower() not in ['date', 'details', 'tax', 'invoice'] and len(inv_num) >= 4:
                return inv_num
    
    return None


def extract_date(text: str) -> Optional[str]:
    """Extract invoice/credit note date."""
    patterns = [
        r'(?:Credit\s*Note|Invoice|Document)\s*Date[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
        r'Date[d]?[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',  # YYYY-MM-DD
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return normalize_date(match.group(1))
    
    return None


def extract_amounts_from_line(line: str) -> List[float]:
    """Extract all amounts with 2 decimal places from a line."""
    # Match amounts like 1234.56 or 1,234.56
    pattern = r'(\d{1,3}(?:,\d{3})*\.?\d{0,2}|\d+\.\d{2})'
    matches = re.findall(pattern, line)
    amounts = []
    for m in matches:
        amt = normalize_amount(m)
        if amt and amt > 0:
            amounts.append(amt)
    return amounts


def extract_line_items(text: str, platform: str) -> List[Dict[str, Any]]:
    """Extract line items with descriptions and amounts."""
    line_items = []
    lines = text.split('\n')
    
    # Track SAC codes we've already processed
    processed_sacs = set()
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean or len(line_clean) < 5:
            continue
        
        # Skip header/footer lines
        skip_keywords = ['total', 'amount in words', 'subtotal', 'grand total', 
                         'bank', 'account', 'ifsc', 'pan:', 'cin:', 'gstin:',
                         'signature', 'authorized', 'note:', 'disclaimer']
        if any(kw in line_clean.lower() for kw in skip_keywords):
            continue
        
        # Look for SAC/HSN code in line
        sac_match = re.search(r'\b(99\d{4}|996\d{3}|997\d{3}|998\d{3})\b', line_clean)
        
        if sac_match:
            sac_code = sac_match.group(1)
            
            # Skip if already processed (avoid duplicates)
            if sac_code in processed_sacs:
                continue
            
            # Remove SAC code from line for amount extraction
            line_without_sac = line_clean.replace(sac_code, '')
            
            # Get description from SAC mapping or from line
            description = SAC_DESCRIPTIONS.get(sac_code)
            
            if not description:
                # Try to extract description from line
                desc_match = re.search(r'([A-Za-z][A-Za-z\s&\-]+(?:Fee|Charges?|Services?|Recovery))', line_clean, re.IGNORECASE)
                if desc_match:
                    description = desc_match.group(1).strip()
            
            # Extract amounts
            amounts = extract_amounts_from_line(line_without_sac)
            
            # Filter out tax rates (usually small numbers like 9, 18)
            real_amounts = [a for a in amounts if a > 50]
            
            fee_amount = None
            tax_amount = None
            total_amount = None
            
            if real_amounts:
                if len(real_amounts) >= 3:
                    # Order: Fee, Tax, Total
                    fee_amount = real_amounts[0]
                    tax_amount = real_amounts[1]
                    total_amount = real_amounts[2]
                elif len(real_amounts) == 2:
                    # Smaller is fee, larger is total
                    sorted_amts = sorted(real_amounts)
                    fee_amount = sorted_amts[0]
                    total_amount = sorted_amts[1]
                    # Calculate tax
                    if total_amount > fee_amount:
                        tax_amount = round(total_amount - fee_amount, 2)
                elif len(real_amounts) == 1:
                    fee_amount = real_amounts[0]
                    total_amount = real_amounts[0]
            
            # Determine tax type (IGST vs CGST/SGST)
            cgst = None
            sgst = None
            igst = None
            
            if tax_amount:
                if 'igst' in line_clean.lower() or 'inter' in text.lower():
                    igst = tax_amount
                else:
                    # Default to IGST for inter-state (most common for e-commerce)
                    igst = tax_amount
            
            if fee_amount or total_amount:
                line_items.append({
                    "category_code_or_hsn": sac_code,
                    "service_description": description or f"Service ({sac_code})",
                    "fee_amount": fee_amount,
                    "cgst_amount": cgst,
                    "sgst_amount": sgst,
                    "igst_amount": igst,
                    "total_tax_amount": tax_amount,
                    "total_amount": total_amount,
                    "tax_rate_percent": 18.0
                })
                processed_sacs.add(sac_code)
    
    # If no line items found with SAC codes, try description-based extraction
    if not line_items:
        service_keywords = [
            ('commission', 'Commission Fee'),
            ('logistics', 'Logistics Fee'),
            ('shipping', 'Shipping Fee'),
            ('delivery', 'Delivery Fee'),
            ('fixed', 'Fixed Fee'),
            ('closing', 'Closing Fee'),
            ('collection', 'Collection Fee'),
            ('payment', 'Payment Gateway Fee'),
            ('gateway', 'Payment Gateway Fee'),
            ('advertisement', 'Advertisement Fee'),
            ('monetization', 'Monetization Fee'),
            ('marketing', 'Marketing Fee'),
            ('fulfilment', 'Fulfillment Fee'),
            ('fulfillment', 'Fulfillment Fee'),
            ('support', 'Support Services Fee'),
        ]
        
        for line in lines:
            line_lower = line.lower()
            for keyword, description in service_keywords:
                if keyword in line_lower and 'total' not in line_lower:
                    amounts = extract_amounts_from_line(line)
                    real_amounts = [a for a in amounts if a > 10]
                    
                    if real_amounts:
                        total = max(real_amounts)
                        fee = min(real_amounts) if len(real_amounts) > 1 else total
                        tax = round(total - fee, 2) if total > fee else None
                        
                        line_items.append({
                            "category_code_or_hsn": None,
                            "service_description": description,
                            "fee_amount": fee,
                            "cgst_amount": None,
                            "sgst_amount": None,
                            "igst_amount": tax,
                            "total_tax_amount": tax,
                            "total_amount": total,
                            "tax_rate_percent": 18.0
                        })
                        break  # Only one item per line
    
    return line_items


def extract_totals(text: str) -> Dict[str, Optional[float]]:
    """Extract total amounts from invoice."""
    totals = {
        'subtotal': None,
        'cgst': None,
        'sgst': None,
        'igst': None,
        'total_tax': None,
        'grand_total': None
    }
    
    patterns = {
        'grand_total': [
            r'Grand\s*Total[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Total\s*(?:Invoice|Amount|Payable)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Total[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ],
        'subtotal': [
            r'(?:Sub\s*)?Total\s*(?:Taxable|Fee)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Taxable\s*(?:Value|Amount)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ],
        'igst': [
            r'(?:Total\s*)?IGST[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'IGST\s*(?:Amount)?[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ],
        'cgst': [
            r'(?:Total\s*)?CGST[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ],
        'sgst': [
            r'(?:Total\s*)?SGST[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ],
    }
    
    for key, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amt = normalize_amount(match.group(1))
                if amt and amt > 0:
                    totals[key] = amt
                    break
    
    # Calculate total_tax if not found
    if not totals['total_tax']:
        if totals['cgst'] and totals['sgst']:
            totals['total_tax'] = totals['cgst'] + totals['sgst']
        elif totals['igst']:
            totals['total_tax'] = totals['igst']
    
    return totals


def extract_names(text: str, platform: str) -> Dict[str, Optional[str]]:
    """Extract provider and receiver names."""
    names = {
        'provider': PLATFORM_PROVIDERS.get(platform.lower()),
        'receiver': None
    }
    
    # Extract receiver name
    receiver_patterns = [
        r'(?:BILLED\s*TO|Bill\s*To|Ship\s*To)[:\s]*(?:Display\s*Name[:\s]*)?([A-Z][A-Za-z\s&]+?)(?:\n|Address|GSTIN)',
        r'(?:Business\s*Name|Customer)[:\s]*([A-Z][A-Za-z\s&]+?)(?:\n|Address|GSTIN)',
        r'Buyer[:\s]*([A-Z][A-Za-z\s&]+?)(?:\n|Address|GSTIN)',
    ]
    
    for pattern in receiver_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            names['receiver'] = match.group(1).strip()[:50]
            break
    
    return names


def universal_extract(text: str, filename: str) -> Dict[str, Any]:
    """
    Universal invoice extractor that works with any platform.
    
    Output columns:
    - Invoice Number
    - Invoice Date
    - Service Provider
    - Provider GSTIN
    - Service Receiver
    - Receiver GSTIN
    - Category Code (SAC/HSN)
    - Service Description
    - Fee Amount (INR)
    - CGST (INR)
    - SGST (INR)
    - IGST (INR)
    - Total Tax (INR)
    - Total Amount (INR)
    """
    
    # Detect platform
    platform = detect_platform(text)
    
    # Extract GSTINs
    gstins = extract_gstin(text)
    provider_gstin = gstins[0] if gstins else None
    receiver_gstin = gstins[1] if len(gstins) > 1 else None
    
    # Extract names
    names = extract_names(text, platform)
    
    # Extract invoice details
    invoice_number = extract_invoice_number(text, platform)
    invoice_date = extract_date(text)
    
    # Determine document type
    doc_type = "CreditNote" if "credit note" in text.lower() else "Invoice"
    
    # Extract line items
    line_items = extract_line_items(text, platform)
    
    # Extract totals
    totals = extract_totals(text)
    
    # Build result
    result = {
        "source_platform": platform,
        "document_type": doc_type,
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "service_provider_name": names['provider'],
        "service_provider_gstin": provider_gstin,
        "service_receiver_name": names['receiver'],
        "service_receiver_gstin": receiver_gstin,
        "place_of_supply_state_code": None,
        "currency": "INR",
        "subtotal_fee_amount": totals['subtotal'],
        "cgst_amount": totals['cgst'],
        "sgst_amount": totals['sgst'],
        "igst_amount": totals['igst'],
        "total_tax_amount": totals['total_tax'],
        "total_invoice_amount": totals['grand_total'],
        "line_items": line_items,
        "_extraction_method": "universal_v2"
    }
    
    # If no totals from patterns, calculate from line items
    if not result['total_invoice_amount'] and line_items:
        result['subtotal_fee_amount'] = sum(item.get('fee_amount') or 0 for item in line_items)
        result['total_tax_amount'] = sum(item.get('total_tax_amount') or 0 for item in line_items)
        result['total_invoice_amount'] = sum(item.get('total_amount') or 0 for item in line_items)
        result['igst_amount'] = sum(item.get('igst_amount') or 0 for item in line_items)
    
    return result
