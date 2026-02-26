# Base Parser with Enhanced GST Invoice Schema
# All template-specific parsers inherit from this

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class LineItem:
    """Enhanced normalized line item structure for GST invoices"""
    line_no: Optional[int] = None
    service_code_or_hsn: Optional[str] = None  # SAC/HSN code
    category_code_or_hsn: Optional[str] = None  # Alias for backward compatibility
    description: Optional[str] = None
    service_description: Optional[str] = None  # Alias for backward compatibility
    taxable_amount: Optional[float] = None  # Base amount before tax
    fee_amount: Optional[float] = None  # Alias for backward compatibility
    sgst_amount: Optional[float] = None
    cgst_amount: Optional[float] = None
    igst_amount: Optional[float] = None
    total_tax_amount: Optional[float] = None
    tax_rate_percent: Optional[float] = None
    total_line_amount: Optional[float] = None  # taxable + all taxes
    total_amount: Optional[float] = None  # Alias for backward compatibility
    is_negative: bool = False  # True for credit notes/refunds
    source_page: Optional[int] = None
    source_snippet: Optional[str] = None

    def __post_init__(self):
        # Sync aliased fields
        if self.taxable_amount and not self.fee_amount:
            self.fee_amount = self.taxable_amount
        elif self.fee_amount and not self.taxable_amount:
            self.taxable_amount = self.fee_amount
            
        if self.description and not self.service_description:
            self.service_description = self.description
        elif self.service_description and not self.description:
            self.description = self.service_description
            
        if self.service_code_or_hsn and not self.category_code_or_hsn:
            self.category_code_or_hsn = self.service_code_or_hsn
        elif self.category_code_or_hsn and not self.service_code_or_hsn:
            self.service_code_or_hsn = self.category_code_or_hsn
            
        if self.total_line_amount and not self.total_amount:
            self.total_amount = self.total_line_amount
        elif self.total_amount and not self.total_line_amount:
            self.total_line_amount = self.total_amount

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedInvoice:
    """Enhanced normalized invoice structure for Indian GST"""
    # Document metadata
    document_type: str = "Invoice"  # Invoice, CreditNote, DebitNote
    platform_name: str = "Unknown"
    source_platform: str = "Unknown"  # Alias for backward compatibility
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None  # YYYY-MM-DD format
    original_invoice_number: Optional[str] = None  # For credit notes
    original_invoice_date: Optional[str] = None  # For credit notes
    
    # Supplier info
    supplier_name: Optional[str] = None
    service_provider_name: Optional[str] = None  # Alias
    supplier_gstin: Optional[str] = None
    service_provider_gstin: Optional[str] = None  # Alias
    
    # Buyer info
    buyer_name: Optional[str] = None
    service_receiver_name: Optional[str] = None  # Alias
    buyer_gstin: Optional[str] = None
    service_receiver_gstin: Optional[str] = None  # Alias
    
    # Location
    place_of_supply: Optional[str] = None
    place_of_supply_state_code: Optional[str] = None  # Alias
    state_code: Optional[str] = None
    currency: str = "INR"
    
    # Totals
    subtotal: Optional[float] = None
    subtotal_fee_amount: Optional[float] = None  # Alias
    cgst_amount: Optional[float] = None
    sgst_amount: Optional[float] = None
    igst_amount: Optional[float] = None
    total_tax: Optional[float] = None
    total_tax_amount: Optional[float] = None  # Alias
    grand_total: Optional[float] = None
    total_invoice_amount: Optional[float] = None  # Alias
    
    # Line items
    line_items: List[LineItem] = field(default_factory=list)
    
    # Metadata
    template_id: str = "UNKNOWN_GENERIC_GST"
    extraction_method: str = "regex"

    def __post_init__(self):
        # Sync aliased fields
        self._sync_aliases()
    
    def _sync_aliases(self):
        """Sync new field names with legacy aliases"""
        # Platform
        if self.platform_name and self.platform_name != "Unknown":
            self.source_platform = self.platform_name
        elif self.source_platform and self.source_platform != "Unknown":
            self.platform_name = self.source_platform
            
        # Supplier
        if self.supplier_name and not self.service_provider_name:
            self.service_provider_name = self.supplier_name
        elif self.service_provider_name and not self.supplier_name:
            self.supplier_name = self.service_provider_name
            
        if self.supplier_gstin and not self.service_provider_gstin:
            self.service_provider_gstin = self.supplier_gstin
        elif self.service_provider_gstin and not self.supplier_gstin:
            self.supplier_gstin = self.service_provider_gstin
            
        # Buyer
        if self.buyer_name and not self.service_receiver_name:
            self.service_receiver_name = self.buyer_name
        elif self.service_receiver_name and not self.buyer_name:
            self.buyer_name = self.service_receiver_name
            
        if self.buyer_gstin and not self.service_receiver_gstin:
            self.service_receiver_gstin = self.buyer_gstin
        elif self.service_receiver_gstin and not self.buyer_gstin:
            self.buyer_gstin = self.service_receiver_gstin
            
        # Location
        if self.place_of_supply and not self.place_of_supply_state_code:
            self.place_of_supply_state_code = self.place_of_supply
        elif self.place_of_supply_state_code and not self.place_of_supply:
            self.place_of_supply = self.place_of_supply_state_code
            
        if self.state_code and not self.place_of_supply_state_code:
            self.place_of_supply_state_code = self.state_code
            
        # Totals
        if self.subtotal and not self.subtotal_fee_amount:
            self.subtotal_fee_amount = self.subtotal
        elif self.subtotal_fee_amount and not self.subtotal:
            self.subtotal = self.subtotal_fee_amount
            
        if self.total_tax and not self.total_tax_amount:
            self.total_tax_amount = self.total_tax
        elif self.total_tax_amount and not self.total_tax:
            self.total_tax = self.total_tax_amount
            
        if self.grand_total and not self.total_invoice_amount:
            self.total_invoice_amount = self.grand_total
        elif self.total_invoice_amount and not self.grand_total:
            self.grand_total = self.total_invoice_amount

    def to_dict(self) -> Dict[str, Any]:
        self._sync_aliases()
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
    line_items_validated: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseParser:
    """Enhanced base parser class for Indian GST invoices"""
    
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
        "997319": "Technical Services",
        "998316": "Support Service Fees",
        "998311": "Management Consulting",
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
        "andaman and nicobar": "35", "dadra and nagar haveli": "26",
        "daman and diu": "25", "lakshadweep": "31",
    }
    
    # State code to abbreviation
    STATE_ABBR = {
        '01': 'JK', '02': 'HP', '03': 'PB', '04': 'CH', '05': 'UK',
        '06': 'HR', '07': 'DL', '08': 'RJ', '09': 'UP', '10': 'BR',
        '11': 'SK', '12': 'AR', '13': 'NL', '14': 'MN', '15': 'MZ',
        '16': 'TR', '17': 'ML', '18': 'AS', '19': 'WB', '20': 'JH',
        '21': 'OR', '22': 'CG', '23': 'MP', '24': 'GJ', '25': 'DD',
        '26': 'DN', '27': 'MH', '29': 'KA', '30': 'GA', '31': 'LD',
        '32': 'KL', '33': 'TN', '34': 'PY', '35': 'AN', '36': 'TG',
        '37': 'AP', '38': 'LA',
    }

    def __init__(self, text: str, pages_text: List[str] = None):
        self.text = text
        self.pages_text = pages_text or [text]
        self.result = NormalizedInvoice(
            source_platform=self.PLATFORM_NAME,
            platform_name=self.PLATFORM_NAME,
            template_id=self.TEMPLATE_ID
        )

    def parse(self) -> NormalizedInvoice:
        """Main parse method - override in subclasses"""
        raise NotImplementedError("Subclasses must implement parse()")

    def validate_and_reconcile(self) -> ValidationResult:
        """Enhanced validation with line item checks"""
        result = ValidationResult()
        tolerance = 1.0  # Allow 1 INR difference for rounding
        
        # Validate each line item
        for i, item in enumerate(self.result.line_items):
            if isinstance(item, LineItem):
                taxable = item.taxable_amount or item.fee_amount or 0
                tax = (item.cgst_amount or 0) + (item.sgst_amount or 0) + (item.igst_amount or 0)
                total = item.total_line_amount or item.total_amount or 0
                
                if taxable > 0 and total > 0:
                    expected = taxable + tax
                    if abs(expected - total) > tolerance:
                        result.line_items_validated = False
                        result.issues.append(f"Line {i+1}: taxable({taxable})+tax({tax})={expected} != total({total})")
        
        # Check line items sum vs subtotal
        if self.result.line_items:
            fee_sum = sum(
                (item.taxable_amount or item.fee_amount or 0) if isinstance(item, LineItem) 
                else (item.get('taxable_amount') or item.get('fee_amount') or 0)
                for item in self.result.line_items
            )
            subtotal = self.result.subtotal or self.result.subtotal_fee_amount
            if subtotal and abs(fee_sum - subtotal) > tolerance:
                result.fee_sum_matches = False
                result.issues.append(f"Fee sum mismatch: line_items={fee_sum:.2f}, subtotal={subtotal:.2f}")
            
            # Check tax sum
            tax_sum = sum(
                (item.total_tax_amount or 0) if isinstance(item, LineItem) 
                else (item.get('total_tax_amount') or 0)
                for item in self.result.line_items
            )
            total_tax = self.result.total_tax or self.result.total_tax_amount
            if total_tax and abs(tax_sum - total_tax) > tolerance:
                result.tax_sum_matches = False
                result.issues.append(f"Tax sum mismatch: line_items={tax_sum:.2f}, total_tax={total_tax:.2f}")
        
        # Check subtotal + tax = total
        subtotal = self.result.subtotal or self.result.subtotal_fee_amount
        total_tax = self.result.total_tax or self.result.total_tax_amount
        grand_total = self.result.grand_total or self.result.total_invoice_amount
        
        if subtotal and total_tax and grand_total:
            expected_total = subtotal + total_tax
            if abs(expected_total - grand_total) > tolerance:
                result.total_matches = False
                result.issues.append(f"Total mismatch: subtotal+tax={expected_total:.2f}, total={grand_total:.2f}")
        
        # Set status
        if not result.line_items_validated:
            result.status = "warn"
        if not result.fee_sum_matches or not result.tax_sum_matches or not result.total_matches:
            if len(result.issues) > 2:
                result.status = "fail"
            else:
                result.status = "warn"
        
        return result

    # ==================== HELPER METHODS ====================

    @staticmethod
    def normalize_amount(amount_str: Any) -> Optional[float]:
        """Convert string amount to float, handling Indian formats and negatives"""
        if amount_str is None:
            return None
        if isinstance(amount_str, (int, float)):
            return round(float(amount_str), 2)
        
        try:
            cleaned = str(amount_str)
            
            # Check for negative indicators
            is_negative = False
            
            # Pattern: -INR, INR-, (123.00), -123.00
            if '-INR' in cleaned or 'INR-' in cleaned or '-Rs' in cleaned:
                is_negative = True
            if cleaned.strip().startswith('-'):
                is_negative = True
            if cleaned.strip().startswith('(') and cleaned.strip().endswith(')'):
                is_negative = True
            if '(' in cleaned and ')' in cleaned:
                # Check if it's accounting format (123.00)
                paren_match = re.search(r'\(([\d,\.]+)\)', cleaned)
                if paren_match:
                    is_negative = True
                    cleaned = paren_match.group(1)
            
            # Remove currency symbols and whitespace
            cleaned = re.sub(r'[₹$\s]', '', cleaned)
            cleaned = cleaned.replace('INR', '').replace('Rs.', '').replace('Rs', '')
            cleaned = cleaned.replace(',', '').strip()
            cleaned = cleaned.replace('-', '').replace('(', '').replace(')', '')
            
            if cleaned:
                value = round(float(cleaned), 2)
                return -value if is_negative else value
        except (ValueError, TypeError):
            pass
        return None

    @staticmethod
    def is_negative_amount(amount_str: Any) -> bool:
        """Check if amount string represents a negative value"""
        if amount_str is None:
            return False
        text = str(amount_str)
        return (
            '-INR' in text or 'INR-' in text or
            '-Rs' in text or text.strip().startswith('-') or
            (text.strip().startswith('(') and text.strip().endswith(')'))
        )

    @staticmethod
    def normalize_date(date_str: str, output_format: str = '%Y-%m-%d') -> Optional[str]:
        """Normalize date to YYYY-MM-DD format (ISO standard)"""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        formats = [
            '%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y', 
            '%Y-%m-%d', '%d-%m-%y', '%d/%m/%y',
            '%d %b %Y', '%d %B %Y', '%Y/%m/%d',
            '%d-%b-%Y', '%d-%B-%Y', '%b %d, %Y',
            '%B %d, %Y', '%Y%m%d'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime(output_format)
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
        if not text:
            return None
            
        # Look for IN-XX format
        match = re.search(r'IN-([A-Z]{2})', text, re.IGNORECASE)
        if match:
            state_abbr = match.group(1).upper()
            # Map abbreviations to codes
            abbr_to_code = {v: k for k, v in self.STATE_ABBR.items()}
            return abbr_to_code.get(state_abbr, state_abbr)
        
        # Look for XX- format (like 07-Delhi)
        match = re.search(r'(\d{2})\s*[-–]\s*[A-Za-z]', text)
        if match:
            return match.group(1)
        
        # Look for just 2-digit code
        match = re.search(r'\b(\d{2})\b', text)
        if match:
            code = match.group(1)
            if code in self.STATE_ABBR:
                return code
        
        # Look for state name
        text_lower = text.lower()
        for state, code in self.STATE_CODES.items():
            if state in text_lower:
                return code
        
        return None

    def get_sac_description(self, sac_code: str) -> str:
        """Get description for SAC code"""
        if not sac_code:
            return "Service"
        return self.SAC_DESCRIPTIONS.get(sac_code, f"Service ({sac_code})")

    def merge_tax_rows(self, rows: List[Dict]) -> List[LineItem]:
        """
        Merge separate SGST/CGST/IGST rows into main charge rows.
        
        Input format:
        [
            {'description': 'Service Fee', 'amount': 1000},
            {'description': 'SGST 9%', 'amount': 90},
            {'description': 'CGST 9%', 'amount': 90},
        ]
        
        Output: Single LineItem with taxes merged
        """
        merged_items = []
        current_item = None
        line_no = 0
        
        for row in rows:
            desc = str(row.get('description', '')).upper()
            amount = self.normalize_amount(row.get('amount'))
            is_neg = self.is_negative_amount(row.get('amount'))
            
            # Check if this is a tax row
            is_sgst = 'SGST' in desc or 'STATE GST' in desc
            is_cgst = 'CGST' in desc or 'CENTRAL GST' in desc
            is_igst = 'IGST' in desc or 'INTEGRATED GST' in desc
            is_tax_row = is_sgst or is_cgst or is_igst
            
            if is_tax_row and current_item:
                # Merge tax into current item
                if is_sgst:
                    current_item.sgst_amount = amount
                elif is_cgst:
                    current_item.cgst_amount = amount
                elif is_igst:
                    current_item.igst_amount = amount
                
                # Extract tax rate if present
                rate_match = re.search(r'(\d+(?:\.\d+)?)\s*%', desc)
                if rate_match:
                    current_item.tax_rate_percent = float(rate_match.group(1))
            else:
                # Save previous item
                if current_item:
                    self._finalize_line_item(current_item)
                    merged_items.append(current_item)
                
                # Start new item
                line_no += 1
                sac_match = re.search(r'(99\d{4}|\d{6})', row.get('sac', '') or row.get('hsn', '') or desc)
                
                current_item = LineItem(
                    line_no=line_no,
                    service_code_or_hsn=sac_match.group(1) if sac_match else None,
                    description=row.get('description', ''),
                    taxable_amount=amount,
                    is_negative=is_neg
                )
        
        # Don't forget the last item
        if current_item:
            self._finalize_line_item(current_item)
            merged_items.append(current_item)
        
        return merged_items

    def _finalize_line_item(self, item: LineItem):
        """Calculate totals for a line item"""
        taxable = item.taxable_amount or 0
        sgst = item.sgst_amount or 0
        cgst = item.cgst_amount or 0
        igst = item.igst_amount or 0
        
        # Calculate total tax
        item.total_tax_amount = sgst + cgst + igst
        
        # Calculate total line amount
        item.total_line_amount = taxable + item.total_tax_amount
        
        # Sync aliases
        item.fee_amount = item.taxable_amount
        item.total_amount = item.total_line_amount
        item.service_description = item.description
        item.category_code_or_hsn = item.service_code_or_hsn
        
        # Infer tax rate if not set
        if not item.tax_rate_percent and taxable > 0 and item.total_tax_amount > 0:
            item.tax_rate_percent = round((item.total_tax_amount / taxable) * 100, 1)

    def detect_document_type(self) -> str:
        """Detect if document is Invoice, CreditNote, or DebitNote"""
        text_lower = self.text.lower()
        
        if 'credit note' in text_lower or 'credit memo' in text_lower:
            return "CreditNote"
        elif 'debit note' in text_lower:
            return "DebitNote"
        elif 'commercial credit' in text_lower:
            return "CommercialCreditNote"
        else:
            return "Invoice"
