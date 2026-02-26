# JioMart Invoice Parser
# Handles: JioMart/Reliance Retail Tax Invoices and Credit Notes

import re
from .base_parser import BaseParser, NormalizedInvoice, LineItem


class JioMartParser(BaseParser):
    """Parser for JioMart/Reliance Retail invoices"""
    
    TEMPLATE_ID = "JIOMART_TAX_INVOICE"
    PLATFORM_NAME = "JioMart"
    
    # Reliance Retail GSTINs pattern
    RELIANCE_GSTIN_KEYWORDS = ['reliance', 'jiomart', 'AAACR']

    def parse(self) -> NormalizedInvoice:
        """Parse JioMart invoice text"""
        self.result.source_platform = "JioMart"
        self.result.platform_name = "JioMart"
        
        # Detect document type
        self.result.document_type = self.detect_document_type()
        if self.result.document_type == "CreditNote":
            self.result.template_id = "JIOMART_CREDIT_NOTE"
        
        self._extract_invoice_number()
        self._extract_date()
        self._extract_gstins()
        self._extract_place_of_supply()
        self._extract_parties()
        self._extract_line_items()
        self._extract_totals()
        
        return self.result

    def _extract_invoice_number(self):
        """Extract JioMart invoice number"""
        patterns = [
            r'(?:Tax\s*)?Invoice\s*(?:No\.?|Number)[:\s]*([A-Z0-9/\-]+)',
            r'Credit\s*Note\s*(?:No\.?|Number)[:\s]*([A-Z0-9/\-]+)',
            r'Document\s*(?:No\.?|Number)[:\s]*([A-Z0-9/\-]+)',
            r'Bill\s*(?:No\.?|Number)[:\s]*([A-Z0-9/\-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                self.result.invoice_number = match.group(1).strip()
                return

    def _extract_date(self):
        """Extract invoice date"""
        patterns = [
            r'(?:Invoice|Bill|Document)\s*Date[:\s]*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
            r'Date[:\s]*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                self.result.invoice_date = self.normalize_date(match.group(1))
                return

    def _extract_gstins(self):
        """Extract GSTINs"""
        gstins = self.extract_gstin(self.text)
        
        # Find Reliance/JioMart GSTIN
        for gstin in gstins:
            if 'AAACR' in gstin:
                self.result.supplier_gstin = gstin
                self.result.service_provider_gstin = gstin
                self.result.supplier_name = "Reliance Retail Limited"
                self.result.service_provider_name = "Reliance Retail Limited"
                break
        
        # First non-Reliance GSTIN is buyer
        for gstin in gstins:
            if gstin != self.result.supplier_gstin:
                self.result.buyer_gstin = gstin
                self.result.service_receiver_gstin = gstin
                break
        
        # Fallback
        if not self.result.supplier_gstin and gstins:
            self.result.supplier_gstin = gstins[0]
            self.result.service_provider_gstin = gstins[0]
        if not self.result.buyer_gstin and len(gstins) > 1:
            self.result.buyer_gstin = gstins[1]
            self.result.service_receiver_gstin = gstins[1]

    def _extract_place_of_supply(self):
        """Extract place of supply"""
        patterns = [
            r'Place\s*of\s*Supply[:\s]*([A-Za-z\s]+)',
            r'State[:\s]*(\d{2})\s*[-–]?\s*([A-Za-z]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                code = self.extract_state_code(match.group(1))
                if code:
                    self.result.state_code = code
                    self.result.place_of_supply_state_code = code
                    return

    def _extract_parties(self):
        """Extract buyer name"""
        patterns = [
            r'(?:Bill\s*To|Buyer|Customer|Sold\s*To)[:\s]*\n?([A-Za-z][A-Za-z\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                name = match.group(1).strip().split('\n')[0].strip()
                if len(name) > 2 and len(name) < 100:
                    self.result.buyer_name = name
                    self.result.service_receiver_name = name
                    return

    def _extract_line_items(self):
        """Extract line items with tax merging"""
        raw_rows = []
        lines = self.text.split('\n')
        
        for line in lines:
            if len(line.strip()) < 5:
                continue
            
            # Look for SAC/HSN codes
            sac_match = re.search(r'(99\d{4}|\d{8}|\d{4})', line)
            amounts = re.findall(r'(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)', line)
            amounts = [self.normalize_amount(a) for a in amounts if self.normalize_amount(a) and self.normalize_amount(a) > 0]
            
            line_upper = line.upper()
            is_tax_row = 'SGST' in line_upper or 'CGST' in line_upper or 'IGST' in line_upper
            
            if is_tax_row and amounts:
                raw_rows.append({
                    'description': line.strip(),
                    'amount': amounts[0]
                })
            elif sac_match and amounts:
                desc = line[:sac_match.start()].strip()
                desc = re.sub(r'^\d+\.?\s*', '', desc).strip()
                
                raw_rows.append({
                    'sac': sac_match.group(1),
                    'description': desc or self.get_sac_description(sac_match.group(1)),
                    'amount': amounts[0]
                })
        
        if raw_rows:
            self.result.line_items = self.merge_tax_rows(raw_rows)

    def _extract_totals(self):
        """Extract totals"""
        # Subtotal
        subtotal_match = re.search(r'(?:Sub\s*Total|Taxable\s*Value)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)', self.text, re.IGNORECASE)
        if subtotal_match:
            self.result.subtotal = self.normalize_amount(subtotal_match.group(1))
            self.result.subtotal_fee_amount = self.result.subtotal
        
        # Tax amounts
        igst_match = re.search(r'IGST[:\s@\d%]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)', self.text, re.IGNORECASE)
        if igst_match:
            self.result.igst_amount = self.normalize_amount(igst_match.group(1))
        
        cgst_match = re.search(r'CGST[:\s@\d%]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)', self.text, re.IGNORECASE)
        sgst_match = re.search(r'SGST[:\s@\d%]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)', self.text, re.IGNORECASE)
        
        if cgst_match:
            self.result.cgst_amount = self.normalize_amount(cgst_match.group(1))
        if sgst_match:
            self.result.sgst_amount = self.normalize_amount(sgst_match.group(1))
        
        # Calculate total tax
        if self.result.igst_amount:
            self.result.total_tax = self.result.igst_amount
            self.result.total_tax_amount = self.result.igst_amount
        elif self.result.cgst_amount or self.result.sgst_amount:
            self.result.total_tax = (self.result.cgst_amount or 0) + (self.result.sgst_amount or 0)
            self.result.total_tax_amount = self.result.total_tax
        
        # Grand total
        total_patterns = [
            r'(?:Grand\s*)?Total[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Net\s*(?:Amount|Payable)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                val = self.normalize_amount(match.group(1))
                if val and val > 0:
                    self.result.grand_total = val
                    self.result.total_invoice_amount = val
                    break
        
        # Calculate from line items if missing
        if self.result.line_items and not self.result.grand_total:
            self.result.subtotal = sum(
                (item.taxable_amount or item.fee_amount or 0) if isinstance(item, LineItem) else (item.get('taxable_amount') or item.get('fee_amount') or 0)
                for item in self.result.line_items
            )
            self.result.subtotal_fee_amount = self.result.subtotal
            self.result.total_tax = sum(
                (item.total_tax_amount or 0) if isinstance(item, LineItem) else (item.get('total_tax_amount') or 0)
                for item in self.result.line_items
            )
            self.result.total_tax_amount = self.result.total_tax
            self.result.grand_total = self.result.subtotal + (self.result.total_tax or 0)
            self.result.total_invoice_amount = self.result.grand_total
