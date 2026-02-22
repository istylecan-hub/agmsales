# Meesho Invoice Parser
# Handles: Meesho Tax Invoice format

import re
from typing import Optional, List
from .base_parser import BaseParser, NormalizedInvoice, LineItem


class MeeshoParser(BaseParser):
    """Parser for Meesho Technologies invoices"""
    
    TEMPLATE_ID = "MEESHO_TAX_INVOICE"
    PLATFORM_NAME = "Meesho"
    
    # Meesho's GSTIN pattern (Karnataka 29, contains AARCM9332R)
    MEESHO_GSTIN_PATTERN = r'29AARCM9332R[A-Z\d]{2}'

    def parse(self) -> NormalizedInvoice:
        """Parse Meesho invoice text"""
        self.result.source_platform = "Meesho"
        self.result.service_provider_name = "Meesho Technologies Private Limited"
        
        # Detect document type
        if "credit note" in self.text.lower():
            self.result.document_type = "CreditNote"
            self.result.template_id = "MEESHO_CREDIT_NOTE"
        else:
            self.result.document_type = "Invoice"
            self.result.template_id = "MEESHO_TAX_INVOICE"
        
        self._extract_invoice_number()
        self._extract_date()
        self._extract_gstins()
        self._extract_place_of_supply()
        self._extract_receiver_name()
        self._extract_line_items()
        self._extract_totals()
        
        return self.result

    def _extract_invoice_number(self):
        """Extract Meesho invoice number"""
        patterns = [
            r'Invoice\s*Number[:\s]*([A-Z0-9/]+)',
            r'(TI/\d+/\d+/\d+)',  # Meesho format: TI/01/26/1599650
            r'Invoice\s*No\.?[:\s]*([A-Z0-9/]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                self.result.invoice_number = match.group(1).strip()
                return

    def _extract_date(self):
        """Extract invoice date"""
        patterns = [
            r'Invoice\s*Date[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
            r'Date[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                self.result.invoice_date = self.normalize_date(match.group(1))
                return

    def _extract_gstins(self):
        """Extract provider and receiver GSTINs"""
        gstins = self.extract_gstin(self.text)
        
        # Meesho's GSTIN (contains AARCM9332R)
        for gstin in gstins:
            if 'AARCM9332R' in gstin:
                self.result.service_provider_gstin = gstin
                break
        
        # First non-Meesho GSTIN is receiver
        for gstin in gstins:
            if 'AARCM9332R' not in gstin:
                self.result.service_receiver_gstin = gstin
                break

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
        match = re.search(r'Bill\s*To[:\s]*\n?([A-Za-z][A-Za-z\s]+)', self.text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Take first line only
            name = name.split('\n')[0].strip()
            if len(name) > 2 and len(name) < 100:
                self.result.service_receiver_name = name

    def _extract_line_items(self):
        """Extract line items from Meesho invoice"""
        # Meesho format is table with columns:
        # S.No | Item | HSN | Taxable Value | SGST (Rs.) | CGST (Rs.) | IGST (Rs.) | Total (Rs.)
        # Example row: 1 Advertisement Fees... 998365 32301.28 0 @ 0% 0 @ 0% 5814.23 @ 18% 38115.51
        
        lines = self.text.split('\n')
        processed = set()
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # Look for SAC code (6 digits starting with 99 or 996)
            sac_match = re.search(r'(99\d{4}|996\d{3})', line_clean)
            if not sac_match:
                continue
            
            sac_code = sac_match.group(1)
            if sac_code in processed:
                continue
            
            # Extract description (text before SAC)
            desc_part = line_clean[:sac_match.start()].strip()
            desc_part = re.sub(r'^\d+\s*', '', desc_part).strip()  # Remove leading number
            
            # Extract all numbers from line (including after SAC)
            amount_part = line_clean[sac_match.end():]
            
            # Parse amounts with their @ rate markers
            # Pattern: amount @ rate% or just amount
            all_amounts = []
            
            # Find patterns like "5814.23 @ 18%" or just "32301.28"
            amount_pattern = r'([\d,]+\.?\d*)\s*(?:@\s*\d+%)?'
            for m in re.finditer(amount_pattern, amount_part):
                val = self.normalize_amount(m.group(1))
                if val is not None and val >= 0:
                    all_amounts.append(val)
            
            if not all_amounts:
                continue
            
            # Meesho table format: Taxable | SGST | CGST | IGST | Total
            # Typical values: [32301.28, 0, 0, 5814.23, 38115.51]
            # The IGST is usually calculated as Taxable * 18%
            
            fee_amount = all_amounts[0] if all_amounts else None
            total_amount = all_amounts[-1] if len(all_amounts) > 1 else None
            
            # For inter-state (IGST): typically values are fee, 0, 0, igst, total
            # IGST should be ~18% of fee
            igst_amount = None
            cgst_amount = None
            sgst_amount = None
            
            if fee_amount and total_amount and len(all_amounts) >= 3:
                expected_igst = round(fee_amount * 0.18, 2)
                
                # Find the IGST value (should be close to 18% of fee)
                for amt in all_amounts[1:-1]:  # Skip first (fee) and last (total)
                    if amt > 0 and abs(amt - expected_igst) < expected_igst * 0.05:  # Within 5%
                        igst_amount = amt
                        break
                
                # If not found by matching, check if we have the pattern fee, 0, 0, igst, total
                if not igst_amount and len(all_amounts) >= 5:
                    # [fee, sgst, cgst, igst, total]
                    if all_amounts[1] == 0 and all_amounts[2] == 0:
                        igst_amount = all_amounts[3]
                    elif all_amounts[1] > 0 and all_amounts[2] > 0:
                        # CGST/SGST case
                        cgst_amount = all_amounts[1]
                        sgst_amount = all_amounts[2]
            
            # Calculate tax if not found
            if not igst_amount and not cgst_amount and fee_amount and total_amount:
                if total_amount > fee_amount:
                    igst_amount = round(total_amount - fee_amount, 2)
                else:
                    igst_amount = round(fee_amount * 0.18, 2)
            
            total_tax = igst_amount if igst_amount else ((cgst_amount or 0) + (sgst_amount or 0))
            
            # Validate and recalculate total if needed
            if fee_amount and total_tax:
                calculated_total = fee_amount + total_tax
                if total_amount and abs(total_amount - calculated_total) > 1:
                    # Use calculated if significantly different
                    pass  # Keep extracted total
                elif not total_amount:
                    total_amount = calculated_total
            
            description = desc_part if desc_part else self.get_sac_description(sac_code)
            
            self.result.line_items.append(LineItem(
                category_code_or_hsn=sac_code,
                service_description=description,
                fee_amount=fee_amount,
                cgst_amount=cgst_amount,
                sgst_amount=sgst_amount,
                igst_amount=igst_amount,
                total_tax_amount=total_tax,
                total_amount=total_amount,
                tax_rate_percent=18.0
            ))
            processed.add(sac_code)
            igst_match = re.search(r'([\d,]+\.?\d*)\s*@\s*18%', amount_part)
            if igst_match:
                igst_amount = self.normalize_amount(igst_match.group(1))
            
            # Total is usually the largest amount (last one)
            if amounts:
                # Filter out zeros
                non_zero = [a for a in amounts if a and a > 0]
                if non_zero:
                    total_amount = max(non_zero)
                    # IGST is typically fee * 0.18
                    if fee_amount and not igst_amount:
                        expected_igst = round(fee_amount * 0.18, 2)
                        for a in non_zero:
                            if abs(a - expected_igst) < 1:  # Within 1 INR
                                igst_amount = a
                                break
            
            # Handle CGST/SGST if present (intra-state)
            if sgst_amount and sgst_amount > 0:
                total_tax = (sgst_amount or 0) + (cgst_amount or 0)
            else:
                total_tax = igst_amount
            
            description = desc_part if desc_part else self.get_sac_description(sac_code)
            
            self.result.line_items.append(LineItem(
                category_code_or_hsn=sac_code,
                service_description=description,
                fee_amount=fee_amount,
                cgst_amount=cgst_amount if cgst_amount and cgst_amount > 0 else None,
                sgst_amount=sgst_amount if sgst_amount and sgst_amount > 0 else None,
                igst_amount=igst_amount,
                total_tax_amount=total_tax,
                total_amount=total_amount,
                tax_rate_percent=18.0
            ))
            processed.add(sac_code)

    def _extract_totals(self):
        """Extract Meesho-specific totals"""
        # Look for Total row with multiple amounts
        # Format: Total (Rs.) 321025.26 0.00 0.00 57784.58 378809.84
        total_pattern = r'Total\s*\(?Rs\.?\)?\s*([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)'
        match = re.search(total_pattern, self.text, re.IGNORECASE)
        
        if match:
            self.result.subtotal_fee_amount = self.normalize_amount(match.group(1))
            self.result.sgst_amount = self.normalize_amount(match.group(2))
            self.result.cgst_amount = self.normalize_amount(match.group(3))
            self.result.igst_amount = self.normalize_amount(match.group(4))
            self.result.total_invoice_amount = self.normalize_amount(match.group(5))
            
            if self.result.igst_amount:
                self.result.total_tax_amount = self.result.igst_amount
            else:
                self.result.total_tax_amount = (self.result.cgst_amount or 0) + (self.result.sgst_amount or 0)
            return
        
        # Try simpler pattern
        total_match = re.search(r'Total\s*(?:Rs\.?)?\s*([\d,]+\.?\d*)', self.text, re.IGNORECASE)
        if total_match:
            self.result.total_invoice_amount = self.normalize_amount(total_match.group(1))
        
        # Calculate from line items if not found
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
