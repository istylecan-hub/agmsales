# Myntra Invoice Parser
# Handles: Myntra Designs Tax Invoice format

import re
from .base_parser import BaseParser, NormalizedInvoice, LineItem


class MyntraParser(BaseParser):
    """Parser for Myntra Designs invoices"""
    
    TEMPLATE_ID = "MYNTRA_TAX_INVOICE"
    PLATFORM_NAME = "Myntra"
    
    # Myntra GSTIN patterns (various states, company PAN AABCM1518R)
    MYNTRA_PAN = "AABCM1518R"

    def parse(self) -> NormalizedInvoice:
        """Parse Myntra invoice text"""
        self.result.source_platform = "Myntra"
        self.result.platform_name = "Myntra"
        self.result.service_provider_name = "Myntra Designs Private Limited"
        self.result.supplier_name = "Myntra Designs Private Limited"
        
        # Detect document type
        self.result.document_type = self.detect_document_type()
        if self.result.document_type == "CreditNote":
            self.result.template_id = "MYNTRA_CREDIT_NOTE"
        else:
            self.result.template_id = "MYNTRA_TAX_INVOICE"
        
        self._extract_invoice_number()
        self._extract_date()
        self._extract_gstins()
        self._extract_place_of_supply()
        self._extract_receiver_name()
        self._extract_line_items()
        self._extract_totals()
        
        return self.result

    def _extract_invoice_number(self):
        """Extract Myntra invoice number"""
        patterns = [
            r'Invoice\s*No\.?[:\s]*([A-Z0-9\-]+)',
            r'(M\d+[A-Z]+[-]?\d+)',  # Myntra format: M26KAIN-436411
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                self.result.invoice_number = match.group(1).strip()
                return

    def _extract_date(self):
        """Extract invoice date"""
        patterns = [
            r'Invoice\s*Date[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
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
        
        # Myntra's GSTIN (contains AABCM1518R)
        for gstin in gstins:
            if self.MYNTRA_PAN in gstin:
                self.result.service_provider_gstin = gstin
                break
        
        # First non-Myntra GSTIN is receiver
        for gstin in gstins:
            if self.MYNTRA_PAN not in gstin:
                self.result.service_receiver_gstin = gstin
                break

    def _extract_place_of_supply(self):
        """Extract place of supply state code"""
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
        """Extract line items from Myntra invoice"""
        # Myntra format with HSN/SAC table:
        # HSN/SAC | Description | Taxable | IGST/CGST/SGST Rate | Tax Amount | Total
        
        # Pattern for SAC code followed by amounts
        lines = self.text.split('\n')
        processed = set()
        
        for line in lines:
            line_clean = line.strip()
            
            # Look for HSN/SAC code
            sac_match = re.search(r'(99\d{4}|\d{6})', line_clean)
            if not sac_match:
                continue
            
            sac_code = sac_match.group(1)
            if sac_code in processed:
                continue
            
            # Extract amounts
            amounts = re.findall(r'([\d,]+\.?\d*)', line_clean.replace(sac_code, ''))
            amounts = [self.normalize_amount(a) for a in amounts if self.normalize_amount(a)]
            
            if not amounts:
                continue
            
            # Get description
            desc_part = line_clean[:sac_match.start()].strip()
            desc_part = re.sub(r'^\d+\s*', '', desc_part).strip()
            
            # Typical order: taxable, rate, tax, total
            fee_amount = amounts[0] if amounts else None
            tax_amount = None
            total_amount = None
            tax_rate = 18.0
            
            # Look for percentage
            rate_match = re.search(r'(\d+)\s*%', line_clean)
            if rate_match:
                tax_rate = float(rate_match.group(1))
            
            # Determine IGST vs CGST/SGST
            has_igst = 'IGST' in line_clean.upper() or 'igst' in self.text.lower()
            has_cgst = 'CGST' in line_clean.upper() or 'cgst' in self.text.lower()
            
            if len(amounts) >= 3:
                fee_amount = amounts[0]
                tax_amount = amounts[1]
                total_amount = amounts[2]
            elif len(amounts) == 2:
                fee_amount = amounts[0]
                total_amount = amounts[1]
                tax_amount = total_amount - fee_amount if total_amount and fee_amount else None
            
            cgst = sgst = igst = None
            if has_igst:
                igst = tax_amount
            elif has_cgst and tax_amount:
                cgst = tax_amount / 2
                sgst = tax_amount / 2
            else:
                igst = tax_amount
            
            self.result.line_items.append(LineItem(
                category_code_or_hsn=sac_code,
                service_description=desc_part if desc_part else self.get_sac_description(sac_code),
                fee_amount=fee_amount,
                cgst_amount=cgst,
                sgst_amount=sgst,
                igst_amount=igst,
                total_tax_amount=tax_amount,
                total_amount=total_amount,
                tax_rate_percent=tax_rate
            ))
            processed.add(sac_code)

    def _extract_totals(self):
        """Extract Myntra-specific totals"""
        # Look for Total row
        total_pattern = r'Total\s*([\d,]+\.?\d*)\s*([\d,]+\.?\d*)?\s*([\d,]+\.?\d*)?'
        match = re.search(total_pattern, self.text, re.IGNORECASE)
        
        if match:
            amounts = [self.normalize_amount(g) for g in match.groups() if g]
            amounts = [a for a in amounts if a]
            
            if len(amounts) >= 3:
                self.result.subtotal_fee_amount = amounts[0]
                self.result.total_tax_amount = amounts[1]
                self.result.total_invoice_amount = amounts[2]
            elif len(amounts) >= 1:
                self.result.total_invoice_amount = amounts[-1]
        
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
            if not self.result.total_invoice_amount:
                self.result.total_invoice_amount = self.result.subtotal_fee_amount + (self.result.total_tax_amount or 0)
        
        # Set IGST/CGST/SGST based on line items
        if self.result.line_items:
            igst = sum(
                (item.igst_amount or 0) if isinstance(item, LineItem) else (item.get('igst_amount') or 0)
                for item in self.result.line_items
            )
            cgst = sum(
                (item.cgst_amount or 0) if isinstance(item, LineItem) else (item.get('cgst_amount') or 0)
                for item in self.result.line_items
            )
            sgst = sum(
                (item.sgst_amount or 0) if isinstance(item, LineItem) else (item.get('sgst_amount') or 0)
                for item in self.result.line_items
            )
            
            if igst > 0:
                self.result.igst_amount = igst
            if cgst > 0:
                self.result.cgst_amount = cgst
            if sgst > 0:
                self.result.sgst_amount = sgst
