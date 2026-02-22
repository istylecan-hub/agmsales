# AceVector (Snapdeal) Invoice Parser
# Handles: AceVector Limited Tax Invoice format

import re
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
        # AceVector format: Both GSTINs often on same line
        # "GSTIN: 06AABCJ8820B1ZY GSTIN: 07DPSPK6851R1ZP"
        
        gstin_pattern = r'(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1})'
        
        # Look for pattern "Supplier Details:...GSTIN: XXX...Buyer Details:...GSTIN: YYY"
        # In AceVector, they appear as: "GSTIN: supplier_gstin GSTIN: buyer_gstin" on one line
        
        # Find all GSTINs in order of appearance
        all_gstins = re.findall(gstin_pattern, self.text, re.IGNORECASE)
        unique_gstins = []
        for g in all_gstins:
            g_upper = g.upper()
            if g_upper not in unique_gstins:
                unique_gstins.append(g_upper)
        
        # AceVector's PAN is AABCJ8820B
        for gstin in unique_gstins:
            if 'AABCJ8820B' in gstin:
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
        # AceVector format:
        # "1 Brand 998365 OTH 1 14273.70 0.00 14273.70 18 0.00 14273.70"
        # Sl No | Description | HSN | QTY-type | QTY | Unit Price | Discount | Taxable | GST(%) | Other | Total
        
        lines = self.text.split('\n')
        
        for i, line in enumerate(lines):
            # Skip headers and totals rows
            if 'Sl No' in line or 'Description' in line:
                continue
            if 'Taxable' in line.split()[0:1] or 'Total Invoice' in line:
                continue
                
            # Look for 6-digit HSN/SAC code
            hsn_match = re.search(r'(998\d{3})', line)
            if not hsn_match:
                continue
            
            hsn_code = hsn_match.group(1)
            
            # For AceVector, extract just the decimal numbers (amounts)
            decimal_amounts = re.findall(r'(\d+\.\d{2})', line)
            decimal_amounts = [float(a) for a in decimal_amounts]
            
            # Filter out zeros and keep meaningful amounts
            non_zero_amounts = [a for a in decimal_amounts if a > 0]
            
            if not non_zero_amounts:
                continue
            
            # Get description (text before HSN)
            desc = line[:hsn_match.start()].strip()
            desc = re.sub(r'^\d+\s*', '', desc).strip()  # Remove leading serial number
            
            # Check next line for continuation of description
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # "Monetization Fees" continuation
                if next_line and not re.search(r'^\d|Taxable|Total|Amount|Sl No', next_line):
                    if not re.search(r'\d+\.\d{2}', next_line):  # No amounts
                        desc = f"{desc} {next_line}".strip()
            
            # The first meaningful amount is the fee (taxable amount)
            fee_amount = non_zero_amounts[0] if non_zero_amounts else None
            
            # Look for GST rate - it's a 2-digit integer (like 18) between decimal amounts
            # Pattern: look for integers in [5, 9, 12, 18, 28] 
            gst_rate = 18.0  # Default
            parts = line.split()
            for part in parts:
                if part in ['5', '9', '12', '18', '28']:
                    gst_rate = float(part)
                    break
            
            if fee_amount:
                igst_amount = round(fee_amount * gst_rate / 100, 2)
                total_amount = fee_amount + igst_amount
                
                self.result.line_items.append(LineItem(
                    category_code_or_hsn=hsn_code,
                    service_description=desc or "Monetization Fees",
                    fee_amount=fee_amount,
                    igst_amount=igst_amount,
                    total_tax_amount=igst_amount,
                    total_amount=total_amount,
                    tax_rate_percent=gst_rate
                ))
                return  # Only one line item typically
        
        # If table parsing failed, try simple extraction from totals
        if not self.result.line_items:
            self._extract_simple()

    def _extract_simple(self):
        """Simple extraction fallback"""
        # Look for taxable amount in totals row
        taxable_match = re.search(r'Taxable\s+([\d,]+\.?\d*)', self.text, re.IGNORECASE)
        igst_match = re.search(r'IGST\s+([\d,]+\.?\d*)', self.text, re.IGNORECASE)
        hsn_match = re.search(r'(998\d{3})', self.text)
        
        fee_amount = None
        igst_amount = None
        
        if taxable_match:
            fee_amount = self.normalize_amount(taxable_match.group(1))
        
        if igst_match:
            igst_amount = self.normalize_amount(igst_match.group(1))
        elif fee_amount:
            igst_amount = round(fee_amount * 0.18, 2)
        
        hsn_code = hsn_match.group(1) if hsn_match else "998365"
        
        if fee_amount:
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
        # AceVector format has totals data on a line by itself:
        # "14273.70 0.00 0.00 2569.27 0.00 0.00 0.00 16842.97"
        # Format: Taxable | CGST | SGST | IGST | Cess | State Cess | Round Off | Total Invoice
        
        # Look for line with exactly 8 decimal numbers (the totals row)
        lines = self.text.split('\n')
        
        for line in lines:
            # Skip header row
            if 'Taxable' in line and 'CGST' in line:
                continue
            
            # Find lines with multiple decimal amounts
            amounts = re.findall(r'(\d+\.\d{2})', line)
            if len(amounts) >= 7:  # Should have at least 7-8 values
                amounts = [float(a) for a in amounts]
                
                # Format: [Taxable, CGST, SGST, IGST, Cess, StateCess, RoundOff, Total]
                if len(amounts) >= 8:
                    self.result.subtotal_fee_amount = amounts[0]
                    self.result.cgst_amount = amounts[1]
                    self.result.sgst_amount = amounts[2]
                    self.result.igst_amount = amounts[3]
                    self.result.total_invoice_amount = amounts[7]
                    self.result.total_tax_amount = self.result.igst_amount or ((self.result.cgst_amount or 0) + (self.result.sgst_amount or 0))
                    return
        
        # Fallback: Try "Total Invoice" pattern
        total_match = re.search(r'Total\s*Invoice\s*[\s:]*([\d,]+\.?\d*)', self.text, re.IGNORECASE)
        if total_match:
            self.result.total_invoice_amount = self.normalize_amount(total_match.group(1))
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
