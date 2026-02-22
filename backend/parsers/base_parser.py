# Base Parser with Normalized Schema
# All template-specific parsers inherit from this

import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class LineItem:
    """Normalized line item structure"""
    category_code_or_hsn: Optional[str] = None
    service_description: Optional[str] = None
    fee_amount: Optional[float] = None
    cgst_amount: Optional[float] = None
    sgst_amount: Optional[float] = None
    igst_amount: Optional[float] = None
    total_tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    tax_rate_percent: Optional[float] = None
    source_page: Optional[int] = None
    source_snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedInvoice:
    """Normalized invoice structure - strict schema"""
    # Header fields
    source_platform: str = "Unknown"
    document_type: str = "Invoice"  # Invoice, CreditNote, CommercialCreditNote
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None  # dd/mm/yyyy
    service_provider_name: Optional[str] = None
    service_provider_gstin: Optional[str] = None
    service_receiver_name: Optional[str] = None
    service_receiver_gstin: Optional[str] = None
    place_of_supply_state_code: Optional[str] = None
    
    # Totals
    subtotal_fee_amount: Optional[float] = None
    cgst_amount: Optional[float] = None
    sgst_amount: Optional[float] = None
    igst_amount: Optional[float] = None
    total_tax_amount: Optional[float] = None
    total_invoice_amount: Optional[float] = None
    
    # Line items
    line_items: List[LineItem] = field(default_factory=list)
    
    # Metadata
    template_id: str = "UNKNOWN_GENERIC_GST"
    extraction_method: str = "regex"
    currency: str = "INR"

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['line_items'] = [item.to_dict() if isinstance(item, LineItem) else item for item in self.line_items]
        return result


@dataclass
class ValidationResult:
    """Result of totals reconciliation"""
    status: str = "ok"  # ok, warn, fail
    issues: List[str] = field(default_factory=list)
    fee_sum_matches: bool = True
    tax_sum_matches: bool = True
    total_matches: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseParser:
    """Base parser class - all template parsers inherit from this"""
    
    TEMPLATE_ID = "UNKNOWN_GENERIC_GST"
    PLATFORM_NAME = "Unknown"
    
    # Common SAC code descriptions
    SAC_DESCRIPTIONS = {
        "998365": "Commission/Marketplace Fee",
        "998599": "Fixed Closing Fee/Collection Fee",
        "996812": "Courier/Delivery Service",
        "996799": "Logistics/Shipping Fee",
        "998314": "Advertising Service",
        "996211": "Business Services",
        "997212": "Warehousing/Fulfillment",
        "996729": "Support Services",
        "998313": "Marketing Service",
        "998361": "Business Support Service",
        "996511": "Transportation Fee",
    }
    
    # State code mapping
    STATE_CODES = {
        "andhra pradesh": "37", "arunachal pradesh": "12", "assam": "18",
        "bihar": "10", "chhattisgarh": "22", "delhi": "07", "goa": "30",
        "gujarat": "24", "haryana": "06", "himachal pradesh": "02",
        "jharkhand": "20", "karnataka": "29", "kerala": "32",
        "madhya pradesh": "23", "maharashtra": "27", "manipur": "14",
        "meghalaya": "17", "mizoram": "15", "nagaland": "13", "odisha": "21",
        "punjab": "03", "rajasthan": "08", "sikkim": "11", "tamil nadu": "33",
        "telangana": "36", "tripura": "16", "uttar pradesh": "09",
        "uttarakhand": "05", "west bengal": "19", "puducherry": "34",
        "chandigarh": "04", "jammu and kashmir": "01", "ladakh": "38",
    }

    def __init__(self, text: str, pages_text: List[str] = None):
        self.text = text
        self.pages_text = pages_text or [text]
        self.result = NormalizedInvoice(
            source_platform=self.PLATFORM_NAME,
            template_id=self.TEMPLATE_ID
        )

    def parse(self) -> NormalizedInvoice:
        """Main parse method - override in subclasses"""
        raise NotImplementedError("Subclasses must implement parse()")

    def validate_and_reconcile(self) -> ValidationResult:
        """Validate totals reconciliation"""
        result = ValidationResult()
        tolerance = 0.5  # Allow 0.5 INR difference
        
        # Check line items sum vs subtotal
        if self.result.line_items:
            fee_sum = sum(
                (item.fee_amount or 0) if isinstance(item, LineItem) else (item.get('fee_amount') or 0)
                for item in self.result.line_items
            )
            if self.result.subtotal_fee_amount:
                diff = abs(fee_sum - self.result.subtotal_fee_amount)
                if diff > tolerance:
                    result.fee_sum_matches = False
                    result.issues.append(f"Fee sum mismatch: line_items={fee_sum:.2f}, subtotal={self.result.subtotal_fee_amount:.2f}")
            
            # Check tax sum
            tax_sum = sum(
                (item.total_tax_amount or 0) if isinstance(item, LineItem) else (item.get('total_tax_amount') or 0)
                for item in self.result.line_items
            )
            if self.result.total_tax_amount:
                diff = abs(tax_sum - self.result.total_tax_amount)
                if diff > tolerance:
                    result.tax_sum_matches = False
                    result.issues.append(f"Tax sum mismatch: line_items={tax_sum:.2f}, total_tax={self.result.total_tax_amount:.2f}")
        
        # Check subtotal + tax = total
        if self.result.subtotal_fee_amount and self.result.total_tax_amount and self.result.total_invoice_amount:
            expected_total = self.result.subtotal_fee_amount + self.result.total_tax_amount
            diff = abs(expected_total - self.result.total_invoice_amount)
            if diff > tolerance:
                result.total_matches = False
                result.issues.append(f"Total mismatch: subtotal+tax={expected_total:.2f}, total={self.result.total_invoice_amount:.2f}")
        
        # Set status
        if not result.fee_sum_matches or not result.tax_sum_matches or not result.total_matches:
            if len(result.issues) > 2:
                result.status = "fail"
            else:
                result.status = "warn"
        
        return result

    # ==================== HELPER METHODS ====================

    @staticmethod
    def normalize_amount(amount_str: Any) -> Optional[float]:
        """Convert string amount to float, handling Indian formats"""
        if amount_str is None:
            return None
        if isinstance(amount_str, (int, float)):
            return round(float(amount_str), 2)
        
        try:
            cleaned = str(amount_str)
            # Remove currency symbols and whitespace
            cleaned = re.sub(r'[₹$\s]', '', cleaned)
            cleaned = cleaned.replace('INR', '').replace('Rs.', '').replace('Rs', '')
            cleaned = cleaned.replace(',', '').strip()
            # Handle negative (credit notes)
            is_negative = '-' in cleaned or '(' in cleaned
            cleaned = cleaned.replace('-', '').replace('(', '').replace(')', '')
            
            if cleaned:
                value = round(float(cleaned), 2)
                return -value if is_negative else value
        except (ValueError, TypeError):
            pass
        return None

    @staticmethod
    def normalize_date(date_str: str) -> Optional[str]:
        """Normalize date to dd/mm/yyyy format"""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        formats = [
            '%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y', 
            '%Y-%m-%d', '%d-%m-%y', '%d/%m/%y',
            '%d %b %Y', '%d %B %Y', '%Y/%m/%d'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%d/%m/%Y')
            except ValueError:
                continue
        return date_str

    @staticmethod
    def extract_gstin(text: str) -> List[str]:
        """Extract all GSTINs from text"""
        pattern = r'\b(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1})\b'
        matches = re.findall(pattern, text, re.IGNORECASE)
        return list(dict.fromkeys([g.upper() for g in matches]))

    def extract_state_code(self, text: str) -> Optional[str]:
        """Extract state code from place of supply"""
        # Look for IN-XX format
        match = re.search(r'IN-([A-Z]{2})', text, re.IGNORECASE)
        if match:
            state_abbr = match.group(1).upper()
            # Map common abbreviations
            abbr_map = {
                'DL': '07', 'MH': '27', 'KA': '29', 'TN': '33',
                'UP': '09', 'GJ': '24', 'RJ': '08', 'WB': '19',
                'HR': '06', 'PB': '03', 'TG': '36', 'AP': '37'
            }
            return abbr_map.get(state_abbr, state_abbr)
        
        # Look for XX- format (like 07-Delhi)
        match = re.search(r'(\d{2})-?[A-Za-z]', text)
        if match:
            return match.group(1)
        
        # Look for state name
        text_lower = text.lower()
        for state, code in self.STATE_CODES.items():
            if state in text_lower:
                return code
        
        return None

    def get_sac_description(self, sac_code: str) -> str:
        """Get description for SAC code"""
        return self.SAC_DESCRIPTIONS.get(sac_code, f"Service ({sac_code})")
