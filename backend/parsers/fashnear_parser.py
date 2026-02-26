# Fashnear Invoice Parser
# Handles: Fashnear Technologies Tax Invoice and Credit Note formats

import re
from .base_parser import BaseParser, NormalizedInvoice, LineItem


class FashnearParser(BaseParser):
    """Parser for Fashnear Technologies invoices (Meesho group)"""
    
    TEMPLATE_ID = "FASHNEAR_TAX_INVOICE"
    PLATFORM_NAME = "Fashnear"
    
    # Fashnear's PAN/GSTIN patterns
    FASHNEAR_PAN = "AADCF8221E"

    def parse(self) -> NormalizedInvoice:
        """Parse Fashnear invoice text"""
        self.result.source_platform = "Fashnear"
        self.result.platform_name = "Fashnear"
        self.result.service_provider_name = "Fashnear Technologies Private Limited"
        self.result.supplier_name = "Fashnear Technologies Private Limited"
        
        # Detect document type
        self.result.document_type = self.detect_document_type()
        if self.result.document_type == "CreditNote":
            self.result.template_id = "FASHNEAR_CREDIT_NOTE"
        else:
            self.result.template_id = "FASHNEAR_TAX_INVOICE"
        
        self._extract_invoice_number()
        self._extract_date()
        self._extract_gstins()
        self._extract_place_of_supply()
        self._extract_receiver_name()
        self._extract_line_items()
        self._extract_totals()
        
        return self.result

    def _extract_invoice_number(self):
        """Extract Fashnear invoice number"""
        patterns = [
            r'Invoice\s*(?:No\.?|Number)[:\s]*([A-Z0-9/\-]+)',
            r'Credit\s*Note\s*(?:No\.?|Number)[:\s]*([A-Z0-9/\-]+)',
            r'(CN/\d+/\d+/\d+)',  # Credit note format
            r'(TI/\d+/\d+/\d+)',  # Tax invoice format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                self.result.invoice_number = match.group(1).strip()
                return

    def _extract_date(self):
        """Extract invoice date"""
        patterns = [
            r'(?:Invoice|Credit\s*Note)\s*Date[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
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
        
        # Fashnear's GSTIN (contains AADCF8221E)
        for gstin in gstins:
            if self.FASHNEAR_PAN in gstin:
                self.result.service_provider_gstin = gstin
                break
        
        # First non-Fashnear GSTIN is receiver
        for gstin in gstins:
            if self.FASHNEAR_PAN not in gstin:
                self.result.service_receiver_gstin = gstin
                break
        
        # Fallback
        if not self.result.service_provider_gstin and gstins:
            self.result.service_provider_gstin = gstins[0]
        if not self.result.service_receiver_gstin and len(gstins) > 1:
            self.result.service_receiver_gstin = gstins[1]

    def _extract_place_of_supply(self):
        """Extract place of supply state code"""
        match = re.search(r'Place\s*of\s*Supply\s*[-–]?\s*(\d{2})', self.text, re.IGNORECASE)
        if match:
            self.result.place_of_supply_state_code = match.group(1)
            return
        
        match = re.search(r'Place\s*of\s*Supply[:\s]*([A-Za-z\s]+)', self.text, re.IGNORECASE)
        if match:
            code = self.extract_state_code(match.group(1))
            if code:
                self.result.place_of_supply_state_code = code

    def _extract_receiver_name(self):
        """Extract receiver business name"""
        patterns = [
            r'Bill\s*To[:\s]*\n?([A-Za-z][A-Za-z\s]+)',
            r'Buyer[:\s]*\n?([A-Za-z][A-Za-z\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                name = match.group(1).strip().split('\n')[0].strip()
                if len(name) > 2 and len(name) < 100:
                    self.result.service_receiver_name = name
                    return

    def _extract_line_items(self):
        """Extract line items from Fashnear invoice"""
        # Similar to Meesho format
        lines = self.text.split('\n')
        processed = set()
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # Look for SAC code
            sac_match = re.search(r'(99\d{4}|996\d{3})', line_clean)
            if not sac_match:
                continue
            
            sac_code = sac_match.group(1)
            if sac_code in processed:
                continue
            
            # Extract description (text before SAC)
            desc_part = line_clean[:sac_match.start()].strip()
            desc_part = re.sub(r'^\d+\s*', '', desc_part).strip()
            
            # Extract amounts after SAC
            amount_part = line_clean[sac_match.end():]
            amounts = re.findall(r'([\d,]+\.?\d*)', amount_part)
            amounts = [self.normalize_amount(a) for a in amounts if self.normalize_amount(a) is not None]
            
            if not amounts:
                continue
            
            fee_amount = amounts[0] if amounts else None
            igst_amount = None
            total_amount = None
            
            # Look for IGST with @ pattern
            igst_match = re.search(r'([\d,]+\.?\d*)\s*@\s*18%', amount_part)
            if igst_match:
                igst_amount = self.normalize_amount(igst_match.group(1))
            
            # Get total (largest amount)
            if amounts:
                non_zero = [a for a in amounts if a and a > 0]
                if non_zero:
                    total_amount = max(non_zero)
                    if fee_amount and not igst_amount:
                        expected_igst = round(fee_amount * 0.18, 2)
                        for a in non_zero:
                            if abs(a - expected_igst) < 1:
                                igst_amount = a
                                break
            
            description = desc_part if desc_part else self.get_sac_description(sac_code)
            
            self.result.line_items.append(LineItem(
                category_code_or_hsn=sac_code,
                service_description=description,
                fee_amount=fee_amount,
                igst_amount=igst_amount,
                total_tax_amount=igst_amount,
                total_amount=total_amount,
                tax_rate_percent=18.0
            ))
            processed.add(sac_code)

    def _extract_totals(self):
        """Extract Fashnear-specific totals"""
        # Look for Total row
        total_pattern = r'Total\s*\(?Rs\.?\)?\s*([\d,]+\.?\d*)'
        match = re.search(total_pattern, self.text, re.IGNORECASE)
        
        if match:
            self.result.total_invoice_amount = self.normalize_amount(match.group(1))
        
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
                self.result.total_invoice_amount = sum(
                    (item.total_amount or 0) if isinstance(item, LineItem) else (item.get('total_amount') or 0)
                    for item in self.result.line_items
                )
