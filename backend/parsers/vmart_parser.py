# V-Mart Invoice Parser
# Handles: V-Mart Retail Tax Invoice format

import re
from typing import Optional, List
from .base_parser import BaseParser, NormalizedInvoice, LineItem


class VMartParser(BaseParser):
    """Parser for V-Mart Retail Limited invoices"""
    
    TEMPLATE_ID = "VMART_TAX_INVOICE"
    PLATFORM_NAME = "V-Mart"
    
    # V-Mart's GSTIN pattern (Haryana 06, contains AABCV7206K)
    VMART_GSTIN_PATTERN = r'06AABCV7206K[A-Z\d]{2}'

    def parse(self) -> NormalizedInvoice:
        """Parse V-Mart invoice text"""
        self.result.source_platform = "V-Mart"
        self.result.service_provider_name = "V-Mart Retail Limited"
        
        # Detect document type
        if "credit note" in self.text.lower():
            self.result.document_type = "CreditNote"
            self.result.template_id = "VMART_CREDIT_NOTE"
        else:
            self.result.document_type = "Invoice"
            self.result.template_id = "VMART_TAX_INVOICE"
        
        self._extract_invoice_number()
        self._extract_date()
        self._extract_gstins()
        self._extract_place_of_supply()
        self._extract_receiver_name()
        self._extract_line_items()
        self._extract_totals()
        
        return self.result

    def _extract_invoice_number(self):
        """Extract V-Mart invoice number"""
        patterns = [
            r'Invoice\s*No[:\s]*([A-Z0-9/]+)',
            r'(COM/\d+/IN\d+)',  # V-Mart format: COM/2526/IN10961
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                self.result.invoice_number = match.group(1).strip()
                return

    def _extract_date(self):
        """Extract invoice date"""
        patterns = [
            r'Dated[:\s]*(\d{4}[-/]\d{2}[-/]\d{2})',  # YYYY-MM-DD format
            r'Date[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                self.result.invoice_date = self.normalize_date(match.group(1))
                return

    def _extract_gstins(self):
        """Extract provider and receiver GSTINs"""
        gstins = self.extract_gstin(self.text)
        
        # V-Mart's GSTIN (contains AABCV7206K)
        for gstin in gstins:
            if 'AABCV7206K' in gstin:
                self.result.service_provider_gstin = gstin
                break
        
        # First non-V-Mart GSTIN is receiver
        for gstin in gstins:
            if 'AABCV7206K' not in gstin:
                self.result.service_receiver_gstin = gstin
                break

    def _extract_place_of_supply(self):
        """Extract place of supply state code"""
        # V-Mart shows state code in "State Code: XX" format
        match = re.search(r'State\s*Code\s*:\s*(\d{2})', self.text, re.IGNORECASE)
        if match:
            self.result.place_of_supply_state_code = match.group(1)
            return
        
        match = re.search(r'State\s*Name\s*:\s*([A-Za-z\s]+)', self.text, re.IGNORECASE)
        if match:
            code = self.extract_state_code(match.group(1))
            if code:
                self.result.place_of_supply_state_code = code

    def _extract_receiver_name(self):
        """Extract receiver business name"""
        match = re.search(r'Bill\s*To\s*/\s*Ship\s*To\s*address[:\s]*\n?([A-Za-z][A-Za-z\s]+)', self.text, re.IGNORECASE)
        if match:
            name = match.group(1).strip().split('\n')[0].strip()
            if len(name) > 2 and len(name) < 100:
                self.result.service_receiver_name = name

    def _extract_line_items(self):
        """Extract line items from V-Mart invoice"""
        # V-Mart format:
        # Sl No. Particulars Qty Rate per Amount
        # Commission 2479.91
        # Description of service : Business And Production Services
        # SAC : 996211
        # IGST 18.0 % 446.38
        
        # Look for Commission/Service line with amount
        lines = self.text.split('\n')
        
        current_item = {}
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # Look for "Commission" or similar with amount
            commission_match = re.search(r'(Commission|Service\s*Charge|Fee)[:\s]*([\d,]+\.?\d*)?', line_clean, re.IGNORECASE)
            if commission_match:
                desc = commission_match.group(1)
                amount = self.normalize_amount(commission_match.group(2)) if commission_match.group(2) else None
                
                # Look for amount on same line or next line
                if not amount:
                    amounts = re.findall(r'([\d,]+\.?\d*)', line_clean)
                    amounts = [self.normalize_amount(a) for a in amounts if self.normalize_amount(a)]
                    if amounts:
                        amount = amounts[0]
                
                current_item['description'] = desc
                current_item['fee_amount'] = amount
            
            # Look for SAC code
            sac_match = re.search(r'SAC\s*:\s*(\d{6})', line_clean, re.IGNORECASE)
            if sac_match:
                current_item['sac_code'] = sac_match.group(1)
            
            # Look for IGST
            igst_match = re.search(r'IGST\s+(\d+\.?\d*)\s*%\s*([\d,]+\.?\d*)', line_clean, re.IGNORECASE)
            if igst_match:
                current_item['tax_rate'] = float(igst_match.group(1))
                current_item['igst_amount'] = self.normalize_amount(igst_match.group(2))
        
        # Create line item if we found data
        if current_item.get('fee_amount'):
            fee = current_item.get('fee_amount', 0)
            igst = current_item.get('igst_amount', 0)
            
            # If IGST not found, calculate it
            if not igst and fee:
                igst = round(fee * 0.18, 2)
            
            self.result.line_items.append(LineItem(
                category_code_or_hsn=current_item.get('sac_code'),
                service_description=current_item.get('description', 'Commission'),
                fee_amount=fee,
                igst_amount=igst,
                total_tax_amount=igst,
                total_amount=fee + igst if fee and igst else None,
                tax_rate_percent=current_item.get('tax_rate', 18.0)
            ))
        
        # Alternative: Look for structured table data
        if not self.result.line_items:
            self._extract_from_table()

    def _extract_from_table(self):
        """Extract from table format"""
        # Pattern: Amount on one line, SAC on another, IGST on another
        fee_match = re.search(r'(?:Commission|Fee|Charge)\s*([\d,]+\.?\d*)', self.text, re.IGNORECASE)
        sac_match = re.search(r'SAC\s*:\s*(\d{6})', self.text, re.IGNORECASE)
        igst_match = re.search(r'IGST\s+\d+\.?\d*\s*%\s*([\d,]+\.?\d*)', self.text, re.IGNORECASE)
        
        fee = self.normalize_amount(fee_match.group(1)) if fee_match else None
        sac = sac_match.group(1) if sac_match else None
        igst = self.normalize_amount(igst_match.group(1)) if igst_match else None
        
        if fee:
            if not igst:
                igst = round(fee * 0.18, 2)
            
            self.result.line_items.append(LineItem(
                category_code_or_hsn=sac,
                service_description="Commission",
                fee_amount=fee,
                igst_amount=igst,
                total_tax_amount=igst,
                total_amount=fee + igst,
                tax_rate_percent=18.0
            ))

    def _extract_totals(self):
        """Extract V-Mart-specific totals"""
        # Look for "Total Rs. X,XXX.XX"
        total_match = re.search(r'Total\s*(?:Rs\.?)?\s*([\d,]+\.?\d*)', self.text, re.IGNORECASE)
        if total_match:
            self.result.total_invoice_amount = self.normalize_amount(total_match.group(1))
        
        # Calculate from line items
        if self.result.line_items:
            if not self.result.subtotal_fee_amount:
                self.result.subtotal_fee_amount = sum(
                    (item.fee_amount or 0) if isinstance(item, LineItem) else (item.get('fee_amount') or 0)
                    for item in self.result.line_items
                )
            if not self.result.total_tax_amount:
                self.result.total_tax_amount = sum(
                    (item.total_tax_amount or 0) if isinstance(item, LineItem) else (item.get('total_tax_amount') or 0)
                    for item in self.result.line_items
                )
                self.result.igst_amount = self.result.total_tax_amount
            if not self.result.total_invoice_amount:
                self.result.total_invoice_amount = self.result.subtotal_fee_amount + (self.result.total_tax_amount or 0)
