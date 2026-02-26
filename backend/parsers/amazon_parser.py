# Amazon Invoice Parser
# Handles: Amazon Tax Invoice and Credit Note formats

import re
from .base_parser import BaseParser, NormalizedInvoice, LineItem


class AmazonParser(BaseParser):
    """Parser for Amazon Seller Services invoices"""
    
    TEMPLATE_ID = "AMAZON_TAX_INVOICE"
    PLATFORM_NAME = "Amazon"
    
    # Amazon's GSTIN pattern (starts with state code, contains AAICA3918J)
    AMAZON_GSTIN_PATTERN = r'\d{2}AAICA3918J[A-Z\d]{2}'

    def parse(self) -> NormalizedInvoice:
        """Parse Amazon invoice text"""
        self.result.source_platform = "Amazon"
        self.result.platform_name = "Amazon"
        self.result.service_provider_name = "Amazon Seller Services Private Limited"
        self.result.supplier_name = "Amazon Seller Services Private Limited"
        
        # Detect document type
        self.result.document_type = self.detect_document_type()
        if self.result.document_type == "CreditNote":
            self.result.template_id = "AMAZON_CREDIT_NOTE"
        else:
            self.result.template_id = "AMAZON_TAX_INVOICE"
        
        self._extract_invoice_number()
        self._extract_date()
        self._extract_gstins()
        self._extract_place_of_supply()
        self._extract_receiver_name()
        self._extract_line_items()
        self._extract_totals()
        
        return self.result

    def _extract_invoice_number(self):
        """Extract Amazon invoice/credit note number"""
        patterns = [
            r'Credit\s*Note\s*Number[:\s]*([A-Z]{2}-[A-Z]?-?\d+-\d+)',
            r'Invoice\s*Number[:\s]*([A-Z]{2}-\d+-\d+)',
            r'([A-Z]{2}-C?-?\d+-\d+)',  # Generic Amazon format: KA-2526-3179016 or HR-C-26-57073
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                self.result.invoice_number = match.group(1).strip()
                return

    def _extract_date(self):
        """Extract invoice date"""
        patterns = [
            r'(?:Invoice|Credit\s*Note)\s*Date[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
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
        
        # Amazon's GSTIN (contains AAICA3918J)
        for gstin in gstins:
            if 'AAICA3918J' in gstin:
                self.result.service_provider_gstin = gstin
                break
        
        # First non-Amazon GSTIN is receiver
        for gstin in gstins:
            if 'AAICA3918J' not in gstin:
                self.result.service_receiver_gstin = gstin
                break
        
        # Fallback
        if not self.result.service_provider_gstin and gstins:
            self.result.service_provider_gstin = gstins[0]
        if not self.result.service_receiver_gstin and len(gstins) > 1:
            self.result.service_receiver_gstin = gstins[1]

    def _extract_place_of_supply(self):
        """Extract place of supply state code"""
        patterns = [
            r'Place\s*of\s*Supply[:\s]*([A-Za-z\s]+)',
            r'State/UT\s*Code[:\s]*(\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                text = match.group(1).strip()
                code = self.extract_state_code(text)
                if code:
                    self.result.place_of_supply_state_code = code
                    return
                # Try direct extraction
                if text.isdigit() and len(text) == 2:
                    self.result.place_of_supply_state_code = text
                    return

    def _extract_receiver_name(self):
        """Extract receiver business name"""
        patterns = [
            r'Bill\s*to\s*Name[:\s]*([A-Za-z\s]+?)(?:\n|Address)',
            r'Name[:\s]*([A-Z][A-Za-z\s]+?)(?:\n|Address)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                name = match.group(1).strip()
                if len(name) > 2 and len(name) < 100:
                    self.result.service_receiver_name = name
                    return

    def _extract_line_items(self):
        """Extract line items from Amazon invoice (handles negative for credit notes)"""
        is_credit_note = self.result.document_type == "CreditNote"
        
        # Pattern: SI No. SAC_CODE Description Tax Rate Amount
        # Example: 1. 998599 Fixed Closing Fee INR 78.00 or -INR 78.00
        
        # First, try to extract from the main invoice table
        # Pattern matches: SAC code, description, amount (positive or negative)
        line_pattern = r'(\d{6})\s+([A-Za-z\s&]+?(?:Fee|Charge|Service)?)\s+[-]?(?:INR|Rs\.?)\s*[-]?([\d,]+\.?\d*)'
        matches = re.findall(line_pattern, self.text)
        
        processed_sacs = set()
        
        for match in matches:
            sac_code = match[0]
            description = match[1].strip()
            fee_amount = self.normalize_amount(match[2])
            
            if sac_code in processed_sacs or not fee_amount:
                continue
            
            # For credit notes, make amounts negative
            if is_credit_note:
                fee_amount = -abs(fee_amount)
            
            # Look for tax amount for this item
            tax_pattern = rf'{sac_code}.*?(?:IGST|CGST|SGST)\s*(\d+\.?\d*)%.*?[-]?(?:INR|Rs\.?)\s*[-]?([\d,]+\.?\d*)'
            tax_match = re.search(tax_pattern, self.text, re.IGNORECASE | re.DOTALL)
            
            igst_amount = None
            cgst_amount = None
            sgst_amount = None
            tax_rate = 18.0
            
            if tax_match:
                tax_rate = float(tax_match.group(1))
                tax_amount = self.normalize_amount(tax_match.group(2))
                
                if is_credit_note and tax_amount:
                    tax_amount = -abs(tax_amount)
                
                if "IGST" in self.text[tax_match.start():tax_match.end()].upper():
                    igst_amount = tax_amount
                else:
                    # CGST/SGST split
                    cgst_amount = tax_amount
                    sgst_amount = tax_amount
            else:
                # Calculate tax if not found
                tax_calc = round(abs(fee_amount) * 0.18, 2)
                if is_credit_note:
                    igst_amount = -tax_calc
                else:
                    igst_amount = tax_calc
            
            total_tax = igst_amount or ((cgst_amount or 0) + (sgst_amount or 0))
            total_amount = fee_amount + (total_tax or 0)
            
            self.result.line_items.append(LineItem(
                category_code_or_hsn=sac_code,
                service_code_or_hsn=sac_code,
                description=description or self.get_sac_description(sac_code),
                service_description=description or self.get_sac_description(sac_code),
                taxable_amount=fee_amount,
                fee_amount=fee_amount,
                cgst_amount=cgst_amount,
                sgst_amount=sgst_amount,
                igst_amount=igst_amount,
                total_tax_amount=total_tax,
                total_line_amount=total_amount,
                total_amount=total_amount,
                tax_rate_percent=tax_rate,
                is_negative=is_credit_note
            ))
            processed_sacs.add(sac_code)
        
        # If no line items found, try alternative extraction from Details section
        if not self.result.line_items:
            self._extract_line_items_from_details()

    def _extract_line_items_from_details(self):
        """Extract from 'Details of Fees' section (handles credit notes)"""
        is_credit_note = self.result.document_type == "CreditNote"
        
        # Look for date-based entries
        detail_pattern = r'(\d{2}/\d{2}/\d{4})\s+(\d{6})\s+([A-Za-z\s]+)\s+[-]?(?:INR|Rs\.?)?\s*[-]?([\d,]+\.?\d*)'
        matches = re.findall(detail_pattern, self.text)
        
        # Aggregate by SAC code
        sac_totals = {}
        
        for match in matches:
            sac_code = match[1]
            description = match[2].strip()
            amount = self.normalize_amount(match[3])
            
            if sac_code not in sac_totals:
                sac_totals[sac_code] = {'description': description, 'fee': 0}
            sac_totals[sac_code]['fee'] += amount or 0
        
        for sac_code, data in sac_totals.items():
            fee_amount = data['fee']
            
            # For credit notes, make negative
            if is_credit_note:
                fee_amount = -abs(fee_amount)
            
            igst_amount = round(abs(fee_amount) * 0.18, 2)
            if is_credit_note:
                igst_amount = -igst_amount
            
            self.result.line_items.append(LineItem(
                category_code_or_hsn=sac_code,
                service_code_or_hsn=sac_code,
                description=data['description'] or self.get_sac_description(sac_code),
                service_description=data['description'] or self.get_sac_description(sac_code),
                taxable_amount=fee_amount,
                fee_amount=fee_amount,
                igst_amount=igst_amount,
                total_tax_amount=igst_amount,
                total_line_amount=fee_amount + igst_amount,
                total_amount=fee_amount + igst_amount,
                tax_rate_percent=18.0,
                is_negative=is_credit_note
            ))

    def _extract_totals(self):
        """Extract Amazon-specific totals (handles both Invoice and Credit Note)"""
        is_credit_note = self.result.document_type == "CreditNote"
        
        # Amazon format: "Subtotal of fees amount INR 78.00" or "-INR 78.00" for credit notes
        patterns = {
            'subtotal': [
                r'Subtotal\s+of\s+fees\s+amount\s*[-]?(?:INR|Rs\.?)?\s*[-]?([\d,]+\.?\d*)',
                r'Subtotal\s+of\s+fees\s*[-]?(?:INR|Rs\.?)?\s*[-]?([\d,]+\.?\d*)',
            ],
            'igst': [
                r'Subtotal\s+for\s+IGST\s*[-]?(?:INR|Rs\.?)?\s*[-]?([\d,]+\.?\d*)',
            ],
            'cgst': [
                r'Subtotal\s+for\s+CGST\s*[-]?(?:INR|Rs\.?)?\s*[-]?([\d,]+\.?\d*)',
            ],
            'sgst': [
                r'Subtotal\s+for\s+SGST\s*[-]?(?:INR|Rs\.?)?\s*[-]?([\d,]+\.?\d*)',
            ],
            'total_tax': [
                r'Subtotal\s+of\s+GST\s+amount\s*[-]?(?:INR|Rs\.?)?\s*[-]?([\d,]+\.?\d*)',
            ],
            'total': [
                r'Total\s+Invoice\s+amount\s*[-]?(?:INR|Rs\.?)?\s*[-]?([\d,]+\.?\d*)',
                r'Total\s+(?:Credit\s+Note\s+)?amount\s*[-]?(?:INR|Rs\.?)?\s*[-]?([\d,]+\.?\d*)',
                r'Total[:\s]*[-]?(?:INR|Rs\.?)?\s*[-]?([\d,]+\.?\d*)',
            ]
        }
        
        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, self.text, re.IGNORECASE)
                if match:
                    value = self.normalize_amount(match.group(1))
                    if value:
                        # Apply negative for credit notes
                        if is_credit_note:
                            value = -abs(value)
                        
                        if field == 'subtotal':
                            self.result.subtotal_fee_amount = value
                            self.result.subtotal = value
                        elif field == 'igst':
                            self.result.igst_amount = value
                        elif field == 'cgst':
                            self.result.cgst_amount = value
                        elif field == 'sgst':
                            self.result.sgst_amount = value
                        elif field == 'total_tax':
                            self.result.total_tax_amount = value
                            self.result.total_tax = value
                        elif field == 'total':
                            self.result.total_invoice_amount = value
                            self.result.grand_total = value
                        break
        
        # Calculate total tax if not found
        if not self.result.total_tax_amount:
            if self.result.igst_amount:
                self.result.total_tax_amount = self.result.igst_amount
                self.result.total_tax = self.result.igst_amount
            elif self.result.cgst_amount and self.result.sgst_amount:
                self.result.total_tax_amount = self.result.cgst_amount + self.result.sgst_amount
                self.result.total_tax = self.result.total_tax_amount
        
        # Calculate from line items if totals not found
        if not self.result.total_invoice_amount and self.result.line_items:
            self.result.subtotal_fee_amount = sum(
                (item.fee_amount or item.taxable_amount or 0) if isinstance(item, LineItem) else (item.get('fee_amount') or item.get('taxable_amount') or 0)
                for item in self.result.line_items
            )
            self.result.subtotal = self.result.subtotal_fee_amount
            self.result.total_tax_amount = sum(
                (item.total_tax_amount or 0) if isinstance(item, LineItem) else (item.get('total_tax_amount') or 0)
                for item in self.result.line_items
            )
            self.result.total_tax = self.result.total_tax_amount
            self.result.total_invoice_amount = self.result.subtotal_fee_amount + (self.result.total_tax_amount or 0)
            self.result.grand_total = self.result.total_invoice_amount
