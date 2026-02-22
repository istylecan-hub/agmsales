# AceVector (Snapdeal) Invoice Parser
# Handles: AceVector Limited Tax Invoice format

import re
from typing import Optional, List
from .base_parser import BaseParser, NormalizedInvoice, LineItem


class AceVectorParser(BaseParser):
    """Parser for AceVector Limited (Snapdeal) invoices"""
    
    TEMPLATE_ID = "ACEVECTOR_TAX_INVOICE"
    PLATFORM_NAME = "AceVector"
    
    # AceVector's GSTIN pattern (Haryana 06, contains AABCJ8820B)
    ACEVECTOR_GSTIN_PATTERN = r'06AABCJ8820B[A-Z\d]{2}'

    def parse(self) -> NormalizedInvoice:
        """Parse AceVector invoice text"""
        self.result.source_platform = "AceVector"
        self.result.service_provider_name = "AceVector Limited"
        
        # Detect document type
        if "credit note" in self.text.lower():
            self.result.document_type = "CreditNote"
            self.result.template_id = "ACEVECTOR_CREDIT_NOTE"
        else:
            self.result.document_type = "Invoice"
            self.result.template_id = "ACEVECTOR_TAX_INVOICE"
        
        self._extract_invoice_number()
        self._extract_date()
        self._extract_gstins()
        self._extract_place_of_supply()
        self._extract_receiver_name()
        self._extract_line_items()
        self._extract_totals()
        
        return self.result

    def _extract_invoice_number(self):
        """Extract AceVector invoice number"""
        patterns = [
            r'Document\s*No[:\s]*([A-Z0-9/]+)',
            r'(\d+[A-Z]+/IN/\d+)',  # AceVector format: 2526HR/IN/138081
            r'Invoice\s*(?:No|Number)[:\s]*([A-Z0-9/]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                self.result.invoice_number = match.group(1).strip()
                return

    def _extract_date(self):
        """Extract invoice date"""
        patterns = [
            r'Date[:\s]*(\d{2}[-/]\d{2}[-/]\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                self.result.invoice_date = self.normalize_date(match.group(1))
                return

    def _extract_gstins(self):
        """Extract provider and receiver GSTINs"""
        # AceVector format has clear Supplier Details and Buyer Details sections
        # Supplier Details: GSTIN: 06AABCJ8820B1ZY
        # Buyer Details: GSTIN: 07DPSPK6851R1ZP
        
        # More precise pattern matching for labeled sections
        supplier_section = re.search(r'Supplier\s*Details[:\s]*(.*?)(?:Buyer|Address|$)', 
                                     self.text, re.IGNORECASE | re.DOTALL)
        buyer_section = re.search(r'Buyer\s*Details[:\s]*(.*?)(?:Place|Address|Amount|$)', 
                                  self.text, re.IGNORECASE | re.DOTALL)
        
        gstin_pattern = r'GSTIN[:\s]*(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1})'
        
        if supplier_section:
            match = re.search(gstin_pattern, supplier_section.group(1), re.IGNORECASE)
            if match:
                self.result.service_provider_gstin = match.group(1).upper()
        
        if buyer_section:
            match = re.search(gstin_pattern, buyer_section.group(1), re.IGNORECASE)
            if match:
                self.result.service_receiver_gstin = match.group(1).upper()
        
        # Fallback: find all GSTINs and differentiate by PAN
        if not self.result.service_provider_gstin or not self.result.service_receiver_gstin:
            gstins = self.extract_gstin(self.text)
            unique_gstins = list(dict.fromkeys(gstins))  # Remove duplicates preserving order
            
            for gstin in unique_gstins:
                if 'AABCJ8820B' in gstin:  # AceVector's PAN
                    if not self.result.service_provider_gstin:
                        self.result.service_provider_gstin = gstin
                elif not self.result.service_receiver_gstin:
                    self.result.service_receiver_gstin = gstin

    def _extract_place_of_supply(self):
        """Extract place of supply state code"""
        match = re.search(r'Place\s*of\s*Supply[:\s]*(\d{2})', self.text, re.IGNORECASE)
        if match:
            self.result.place_of_supply_state_code = match.group(1)
            return
        
        match = re.search(r'Place\s*of\s*Supply[:\s]*([A-Za-z\-]+)', self.text, re.IGNORECASE)
        if match:
            code = self.extract_state_code(match.group(1))
            if code:
                self.result.place_of_supply_state_code = code

    def _extract_receiver_name(self):
        """Extract receiver business name"""
        match = re.search(r'Buyer\s*Details.*?Name[:\s]*([A-Za-z][A-Za-z\s\-]+)', 
                         self.text, re.IGNORECASE | re.DOTALL)
        if match:
            name = match.group(1).strip().split('\n')[0].strip()
            # Remove trailing identifiers like "- S78b05"
            name = re.sub(r'\s*-\s*[A-Z0-9]+$', '', name)
            if len(name) > 2 and len(name) < 100:
                self.result.service_receiver_name = name

    def _extract_line_items(self):
        """Extract line items from AceVector invoice"""
        # AceVector format in Supply Details table:
        # Sl No | Description | HSN | QTY | Unit | Unit Price | Discount | Taxable | GST(%) | Other | Total
        # 1 | Brand Monetization Fees | 998365 | OTH | 1 | 14273.70 | 0.00 | 14273.70 | 18 | 0.00 | 14273.70
        
        # Pattern for table row
        row_pattern = r'(\d+)\s+([A-Za-z\s]+(?:Fee|Fees|Service|Charge)?)\s+(\d{6})\s+\w+\s+\d+\s+([\d,]+\.?\d*)\s+[\d,]+\.?\d*\s+([\d,]+\.?\d*)\s+(\d+)\s+[\d,]+\.?\d*\s+([\d,]+\.?\d*)'
        
        matches = re.findall(row_pattern, self.text)
        
        for match in matches:
            description = match[1].strip()
            hsn_code = match[2]
            unit_price = self.normalize_amount(match[3])
            taxable = self.normalize_amount(match[4])
            gst_rate = float(match[5])
            total = self.normalize_amount(match[6])
            
            fee_amount = taxable or unit_price
            
            # Calculate IGST
            igst_amount = round(fee_amount * gst_rate / 100, 2) if fee_amount and gst_rate else None
            
            self.result.line_items.append(LineItem(
                category_code_or_hsn=hsn_code,
                service_description=description,
                fee_amount=fee_amount,
                igst_amount=igst_amount,
                total_tax_amount=igst_amount,
                total_amount=total or (fee_amount + igst_amount if fee_amount and igst_amount else None),
                tax_rate_percent=gst_rate
            ))
        
        # If table parsing failed, try simpler extraction
        if not self.result.line_items:
            self._extract_simple()

    def _extract_simple(self):
        """Simple extraction fallback"""
        # Look for Monetization Fee / Commission line
        fee_match = re.search(r'(?:Monetization|Commission)\s*(?:Fee|Fees)?\s*[:\s]*([\d,]+\.?\d*)', 
                             self.text, re.IGNORECASE)
        hsn_match = re.search(r'(\d{6})', self.text)
        
        if fee_match:
            fee_amount = self.normalize_amount(fee_match.group(1))
            hsn_code = hsn_match.group(1) if hsn_match else "998365"
            
            igst_amount = round(fee_amount * 0.18, 2) if fee_amount else None
            
            self.result.line_items.append(LineItem(
                category_code_or_hsn=hsn_code,
                service_description="Brand Monetization Fees",
                fee_amount=fee_amount,
                igst_amount=igst_amount,
                total_tax_amount=igst_amount,
                total_amount=fee_amount + igst_amount if fee_amount and igst_amount else None,
                tax_rate_percent=18.0
            ))

    def _extract_totals(self):
        """Extract AceVector-specific totals"""
        # AceVector format has a clear totals row:
        # Taxable | CGST | SGST | IGST | Cess | State Cess | Round Off | Total Invoice
        # Example: 14273.70 0.00 0.00 2569.27 0.00 0.00 0.00 16842.97
        
        # Look for totals row with all values
        totals_pattern = r'(\d{1,3}(?:,\d{3})*\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d{1,3}(?:,\d{3})*\.?\d*)\s+\d+\.?\d*\s+\d+\.?\d*\s+[\d\.\-]+\s+(\d{1,3}(?:,\d{3})*\.?\d*)'
        match = re.search(totals_pattern, self.text)
        
        if match:
            self.result.subtotal_fee_amount = self.normalize_amount(match.group(1))
            self.result.cgst_amount = self.normalize_amount(match.group(2))
            self.result.sgst_amount = self.normalize_amount(match.group(3))
            self.result.igst_amount = self.normalize_amount(match.group(4))
            self.result.total_invoice_amount = self.normalize_amount(match.group(5))
            self.result.total_tax_amount = self.result.igst_amount or ((self.result.cgst_amount or 0) + (self.result.sgst_amount or 0))
            return
        
        # Try pattern: Total Invoice followed by amount
        total_match = re.search(r'Total\s*Invoice\s*[\s:]*([\d,]+\.?\d*)', self.text, re.IGNORECASE)
        if total_match:
            self.result.total_invoice_amount = self.normalize_amount(total_match.group(1))
        
        # Look for IGST amount
        igst_match = re.search(r'IGST[:\s]*([\d,]+\.?\d*)', self.text, re.IGNORECASE)
        if igst_match:
            self.result.igst_amount = self.normalize_amount(igst_match.group(1))
            self.result.total_tax_amount = self.result.igst_amount
        
        # Try "Amount In Words" pattern - look for total before it
        words_match = re.search(r'Amount\s*In\s*Words', self.text, re.IGNORECASE)
        if words_match and not self.result.total_invoice_amount:
            # Look for number pattern before "Amount In Words"
            before_text = self.text[:words_match.start()]
            amounts = re.findall(r'(\d{1,3}(?:,\d{3})*\.\d{2})', before_text)
            if amounts:
                self.result.total_invoice_amount = self.normalize_amount(amounts[-1])
            amounts = re.findall(r'([\d,]+\.?\d{2})', before_text)
            if amounts:
                self.result.total_invoice_amount = self.normalize_amount(amounts[-1])
        
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
