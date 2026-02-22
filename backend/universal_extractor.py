# Universal Invoice Extractor - Final Production Version
# Supports: Flipkart, Amazon, Meesho, V-Mart, Snapdeal/AceVector

import re
from typing import Dict, Any, List, Optional
from datetime import datetime

# SAC Code to Description mapping
SAC_DESCRIPTIONS = {
    "998365": "Commission/Marketplace Fee",
    "998599": "Fixed Closing Fee",
    "996812": "Courier/Delivery Service",
    "996799": "Logistics/Shipping Fee",
    "998314": "Advertising Service",
    "996211": "Business Services",
    "997212": "Warehousing/Fulfillment",
    "996729": "Support Services",
    "998313": "Marketing Service",
}

PLATFORM_PROVIDERS = {
    "flipkart": "Flipkart Internet Private Limited",
    "amazon": "Amazon Seller Services Private Limited",
    "meesho": "Meesho Technologies Private Limited",
    "vmart": "V-Mart Retail Limited",
    "snapdeal": "AceVector Limited",
}


def normalize_amount(amount_str: str) -> Optional[float]:
    """Convert string amount to float."""
    if not amount_str:
        return None
    try:
        cleaned = re.sub(r'[₹,\s]', '', str(amount_str))
        cleaned = cleaned.replace('INR', '').replace('Rs.', '').replace('Rs', '').strip()
        if cleaned:
            return round(float(cleaned), 2)
    except (ValueError, TypeError):
        pass
    return None


def normalize_date(date_str: str) -> Optional[str]:
    """Normalize date to dd/mm/yyyy."""
    if not date_str:
        return None
    
    date_str = date_str.strip()
    formats = ['%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y', '%Y-%m-%d', '%d-%m-%y', '%d/%m/%y']
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%d/%m/%Y')
        except ValueError:
            continue
    return date_str


def detect_platform(text: str) -> str:
    """Detect invoice platform."""
    text_lower = text.lower()
    
    if "v-mart" in text_lower or "v mart" in text_lower or "vmart" in text_lower:
        return "VMart"
    elif "flipkart" in text_lower:
        return "Flipkart"
    elif "amazon seller services" in text_lower or "amazon.in" in text_lower:
        return "Amazon"
    elif "meesho" in text_lower:
        return "Meesho"
    elif "acevector" in text_lower or "snapdeal" in text_lower:
        return "Snapdeal"
    
    return "Unknown"


def extract_gstin(text: str) -> List[str]:
    """Extract all GSTINs from text."""
    pattern = r'\b(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1})\b'
    matches = re.findall(pattern, text, re.IGNORECASE)
    return list(dict.fromkeys([g.upper() for g in matches]))


def extract_invoice_number(text: str, platform: str) -> Optional[str]:
    """Extract invoice number."""
    patterns = {
        'Flipkart': [r'(FKCKA\d+)', r'(FKRKA\d+)', r'(ICNDL\d+)', r'Credit\s*Note\s*#[:\s]*([A-Z0-9]+)', r'Invoice\s*#[:\s]*([A-Z0-9]+)'],
        'Amazon': [r'Invoice\s*Number[:\s]*([A-Z]{2}-\d+-\d+)', r'(KA-\d+-\d+)', r'(DL-\d+-\d+)'],
        'Meesho': [r'(TI/\d+/\d+/\d+)', r'Invoice\s*No[:\.\s]*(TI/[^\s]+)'],
        'VMart': [r'(COM/\d+/IN\d+)', r'Invoice\s*No[:\.\s]*(COM/[^\s]+)'],
        'Snapdeal': [r'(\d+[A-Z]+/IN/\d+)', r'Invoice\s*Number[:\s]*(\d+)'],
    }
    
    if platform in patterns:
        for pattern in patterns[platform]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    
    # Generic fallback
    generic = [r'Invoice\s*(?:No\.?|Number|#)[:\s]*([A-Z0-9/\-]+)']
    for pattern in generic:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            inv = match.group(1).strip()
            if inv.lower() not in ['date', 'details', 'tax'] and len(inv) >= 4:
                return inv
    
    return None


def extract_date(text: str) -> Optional[str]:
    """Extract invoice date."""
    patterns = [
        r'Invoice\s*Date[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
        r'Date[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return normalize_date(match.group(1))
    return None


def extract_amazon_data(text: str) -> Dict[str, Any]:
    """Extract data from Amazon invoice."""
    # Amazon has clear "Subtotal of fees amount" format
    fee_match = re.search(r'Subtotal\s+of\s+fees\s+amount[:\s]*(?:INR|Rs\.?)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
    igst_match = re.search(r'Subtotal\s+for\s+IGST[:\s]*(?:INR|Rs\.?)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
    cgst_match = re.search(r'Subtotal\s+for\s+CGST[:\s]*(?:INR|Rs\.?)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
    sgst_match = re.search(r'Subtotal\s+for\s+SGST[:\s]*(?:INR|Rs\.?)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
    total_match = re.search(r'Total\s+Invoice\s+amount[:\s]*(?:INR|Rs\.?)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
    
    fee = normalize_amount(fee_match.group(1)) if fee_match else None
    igst = normalize_amount(igst_match.group(1)) if igst_match else None
    cgst = normalize_amount(cgst_match.group(1)) if cgst_match else None
    sgst = normalize_amount(sgst_match.group(1)) if sgst_match else None
    total = normalize_amount(total_match.group(1)) if total_match else None
    
    # Get description from line items
    desc_match = re.search(r'998599[^\n]*(Fixed\s+Closing\s+Fee|Closing\s+Fee|Pick\s*&\s*Pack|Weight\s+Handling)', text, re.IGNORECASE)
    description = desc_match.group(1).strip() if desc_match else "Fixed Closing Fee"
    
    sac_match = re.search(r'\b(998599|996812|998314)\b', text)
    sac_code = sac_match.group(1) if sac_match else "998599"
    
    tax = igst if igst else ((cgst or 0) + (sgst or 0)) if (cgst or sgst) else None
    
    return {
        'fee': fee,
        'cgst': cgst,
        'sgst': sgst,
        'igst': igst,
        'tax': tax,
        'total': total,
        'description': description,
        'sac_code': sac_code
    }


def extract_flipkart_data(text: str) -> Dict[str, Any]:
    """Extract data from Flipkart invoice."""
    # Look for Total row: "Total 224684.89 40443.27 265128.16"
    total_pattern = r'Total\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)'
    total_match = re.search(total_pattern, text, re.IGNORECASE)
    
    if total_match:
        fee = normalize_amount(total_match.group(1))
        tax = normalize_amount(total_match.group(2))
        total = normalize_amount(total_match.group(3))
    else:
        # Fallback: look for individual totals
        fee_match = re.search(r'(?:Total|Subtotal)[:\s]*(?:INR|Rs\.?)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
        fee = normalize_amount(fee_match.group(1)) if fee_match else None
        tax = None
        total = fee
    
    # Find SAC codes
    sac_codes = re.findall(r'\b(998599|996812|998365|996729)\b', text)
    sac_code = sac_codes[0] if sac_codes else None
    
    return {
        'fee': fee,
        'tax': tax,
        'total': total,
        'sac_code': sac_code,
        'description': SAC_DESCRIPTIONS.get(sac_code, "Service Fee") if sac_code else "Service Fee"
    }


def extract_meesho_vmart_data(text: str, platform: str) -> List[Dict[str, Any]]:
    """Extract data from Meesho/V-Mart invoices."""
    items = []
    lines = text.split('\n')
    processed_sacs = set()
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        
        # Look for SAC code
        sac_match = re.search(r'\b(99\d{4}|996\d{3})\b', line_clean)
        if sac_match:
            sac_code = sac_match.group(1)
            if sac_code in processed_sacs:
                continue
            
            # Extract amounts from line
            amounts = re.findall(r'(\d{1,3}(?:,\d{3})*\.\d{2})', line_clean.replace(sac_code, ''))
            amounts = [normalize_amount(a) for a in amounts if normalize_amount(a)]
            
            if amounts:
                sorted_amounts = sorted(amounts)
                if len(sorted_amounts) >= 3:
                    fee, tax, total = sorted_amounts[0], sorted_amounts[1], sorted_amounts[-1]
                elif len(sorted_amounts) == 2:
                    fee, total = sorted_amounts[0], sorted_amounts[1]
                    tax = round(total - fee, 2) if total > fee else None
                else:
                    total = sorted_amounts[0]
                    fee = round(total / 1.18, 2)
                    tax = round(total - fee, 2)
                
                items.append({
                    'sac_code': sac_code,
                    'description': SAC_DESCRIPTIONS.get(sac_code, f"Service ({sac_code})"),
                    'fee': fee,
                    'tax': tax,
                    'total': total
                })
                processed_sacs.add(sac_code)
    
    return items


def extract_snapdeal_data(text: str) -> Dict[str, Any]:
    """Extract data from Snapdeal/AceVector invoice."""
    # Look for Monetization Fee pattern
    fee_match = re.search(r'(?:Monetization|Commission)[^\d]*([\d,]+\.?\d*)', text, re.IGNORECASE)
    total_match = re.search(r'Total[:\s]*(?:INR|Rs\.?)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
    
    fee = normalize_amount(fee_match.group(1)) if fee_match else None
    total = normalize_amount(total_match.group(1)) if total_match else None
    
    if total and not fee:
        fee = round(total / 1.18, 2)
    
    tax = round(total - fee, 2) if total and fee and total > fee else None
    
    return {
        'fee': fee,
        'tax': tax,
        'total': total,
        'description': 'Monetization Fee',
        'sac_code': None
    }


def extract_receiver_name(text: str, platform: str) -> Optional[str]:
    """Extract receiver/buyer name."""
    patterns = [
        r'(?:Bill\s*to|Billed\s*To|Buyer)[:\s]*(?:Name[:\s]*)?([A-Z][A-Za-z\s]+?)(?:\n|Address|GSTIN)',
        r'Display\s*Name[:\s]*([A-Z][A-Za-z\s]+?)(?:\n|Address)',
        r'Business\s*Name[:\s]*([A-Z][A-Za-z\s]+?)(?:\n|Address)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            name = match.group(1).strip()
            if len(name) > 2 and len(name) < 50:
                return name
    return None


def universal_extract(text: str, filename: str) -> Dict[str, Any]:
    """Main extraction function."""
    
    platform = detect_platform(text)
    gstins = extract_gstin(text)
    
    result = {
        "source_platform": platform,
        "document_type": "CreditNote" if "credit note" in text.lower() else "Invoice",
        "invoice_number": extract_invoice_number(text, platform),
        "invoice_date": extract_date(text),
        "service_provider_name": PLATFORM_PROVIDERS.get(platform.lower()),
        "service_provider_gstin": gstins[0] if gstins else None,
        "service_receiver_name": extract_receiver_name(text, platform),
        "service_receiver_gstin": gstins[1] if len(gstins) > 1 else None,
        "place_of_supply_state_code": None,
        "currency": "INR",
        "subtotal_fee_amount": None,
        "cgst_amount": None,
        "sgst_amount": None,
        "igst_amount": None,
        "total_tax_amount": None,
        "total_invoice_amount": None,
        "line_items": [],
        "_extraction_method": "universal_v3"
    }
    
    # Platform-specific extraction
    if platform == "Amazon":
        data = extract_amazon_data(text)
        result['subtotal_fee_amount'] = data['fee']
        result['cgst_amount'] = data.get('cgst')
        result['sgst_amount'] = data.get('sgst')
        result['igst_amount'] = data.get('igst')
        result['total_tax_amount'] = data['tax']
        result['total_invoice_amount'] = data['total']
        
        if data['total']:
            result['line_items'].append({
                "category_code_or_hsn": data['sac_code'],
                "service_description": data['description'],
                "fee_amount": data['fee'],
                "cgst_amount": data.get('cgst'),
                "sgst_amount": data.get('sgst'),
                "igst_amount": data.get('igst'),
                "total_tax_amount": data['tax'],
                "total_amount": data['total'],
                "tax_rate_percent": 18.0
            })
    
    elif platform == "Flipkart":
        data = extract_flipkart_data(text)
        result['subtotal_fee_amount'] = data['fee']
        result['igst_amount'] = data['tax']
        result['total_tax_amount'] = data['tax']
        result['total_invoice_amount'] = data['total']
        
        if data['total']:
            result['line_items'].append({
                "category_code_or_hsn": data['sac_code'],
                "service_description": data['description'],
                "fee_amount": data['fee'],
                "cgst_amount": None,
                "sgst_amount": None,
                "igst_amount": data['tax'],
                "total_tax_amount": data['tax'],
                "total_amount": data['total'],
                "tax_rate_percent": 18.0
            })
    
    elif platform in ["Meesho", "VMart"]:
        items = extract_meesho_vmart_data(text, platform)
        for item in items:
            result['line_items'].append({
                "category_code_or_hsn": item['sac_code'],
                "service_description": item['description'],
                "fee_amount": item['fee'],
                "cgst_amount": None,
                "sgst_amount": None,
                "igst_amount": item['tax'],
                "total_tax_amount": item['tax'],
                "total_amount": item['total'],
                "tax_rate_percent": 18.0
            })
        
        if items:
            result['subtotal_fee_amount'] = sum(i['fee'] or 0 for i in items)
            result['igst_amount'] = sum(i['tax'] or 0 for i in items)
            result['total_tax_amount'] = result['igst_amount']
            result['total_invoice_amount'] = sum(i['total'] or 0 for i in items)
    
    elif platform == "Snapdeal":
        data = extract_snapdeal_data(text)
        result['subtotal_fee_amount'] = data['fee']
        result['igst_amount'] = data['tax']
        result['total_tax_amount'] = data['tax']
        result['total_invoice_amount'] = data['total']
        
        if data['total']:
            result['line_items'].append({
                "category_code_or_hsn": data['sac_code'],
                "service_description": data['description'],
                "fee_amount": data['fee'],
                "cgst_amount": None,
                "sgst_amount": None,
                "igst_amount": data['tax'],
                "total_tax_amount": data['tax'],
                "total_amount": data['total'],
                "tax_rate_percent": 18.0
            })
    
    else:
        # Generic extraction for unknown platforms
        total_match = re.search(r'(?:Grand\s*)?Total[:\s]*(?:INR|Rs\.?)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
        if total_match:
            total = normalize_amount(total_match.group(1))
            result['total_invoice_amount'] = total
            if total:
                fee = round(total / 1.18, 2)
                tax = round(total - fee, 2)
                result['subtotal_fee_amount'] = fee
                result['igst_amount'] = tax
                result['total_tax_amount'] = tax
                result['line_items'].append({
                    "category_code_or_hsn": None,
                    "service_description": "Service Fee",
                    "fee_amount": fee,
                    "cgst_amount": None,
                    "sgst_amount": None,
                    "igst_amount": tax,
                    "total_tax_amount": tax,
                    "total_amount": total,
                    "tax_rate_percent": 18.0
                })
    
    return result
