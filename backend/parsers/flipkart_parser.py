# Flipkart Invoice Parser
# Handles: Flipkart Tax Invoice, Credit Note, and Commercial Credit Note

import re
from .base_parser import BaseParser, NormalizedInvoice, LineItem


class FlipkartParser(BaseParser):
    """Parser for Flipkart invoices and credit notes"""
    
    TEMPLATE_ID = "FLIPKART_COMMISSION_TAX_INVOICE"
    PLATFORM_NAME = "Flipkart"
    
    # Flipkart's GSTIN pattern (contains AACCF0683K)
    FLIPKART_GSTIN_PATTERN = r'\d{2}AACCF0683K[A-Z\d]{2}'

    def parse(self) -> NormalizedInvoice:
        """Parse Flipkart invoice text"""
        self.result.source_platform = "Flipkart"
        self.result.service_provider_name = "Flipkart Internet Private Limited"
        
        # Detect document type
        text_lower = self.text.lower()
        if "commercial credit note" in text_lower:
            self.result.document_type = "CommercialCreditNote"
            self.result.template_id = "FLIPKART_COMMERCIAL_CREDIT_NOTE"
        elif "credit note" in text_lower:
            self.result.document_type = "CreditNote"
            self.result.template_id = "FLIPKART_CREDIT_NOTE"
        else:
            self.result.document_type = "Invoice"
            self.result.template_id = "FLIPKART_COMMISSION_TAX_INVOICE"
        
        self._extract_invoice_number()
        self._extract_date()
        self._extract_gstins()
        self._extract_place_of_supply()
        self._extract_receiver_name()
        self._extract_line_items()
        self._extract_totals()
        
        return self.result

    def _extract_invoice_number(self):
        """Extract Flipkart invoice/credit note number"""
        # Direct pattern matching for Flipkart-specific formats (most reliable)
        direct_patterns = [
            r'(FKCKA\d+)',  # Credit note format
            r'(FKRKA\d+)',  # Tax invoice format
            r'(ICNDL\d+)',  # Commercial credit note format
        ]
        
        for pattern in direct_patterns:
            match = re.search(pattern, self.text)
            if match:
                self.result.invoice_number = match.group(1).strip()
                return
        
        # Fallback to labeled patterns
        labeled_patterns = [
            r'Credit\s*Note\s*#:\s*\n?\s*([A-Z0-9]+)',
            r'Invoice\s*#:\s*\n?\s*([A-Z0-9]+)',
        ]
        
        for pattern in labeled_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                inv_num = match.group(1).strip()
                # Validate it's not a field name
                if inv_num.upper() not in ['BUSINESS', 'NAME', 'ADDRESS', 'DATE']:
                    self.result.invoice_number = inv_num
                    return

    def _extract_date(self):
        """Extract invoice date"""
        patterns = [
            r'Credit\s*Note\s*Date[:\s]*(\d{2}[-/]\d{2}[-/]\d{4})',
            r'Invoice\s*Date[:\s]*(\d{2}[-/]\d{2}[-/]\d{4})',
            r'Date[:\s]*(\d{2}[-/]\d{2}[-/]\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                self.result.invoice_date = self.normalize_date(match.group(1).replace('-', '/'))
                return

    def _extract_gstins(self):
        """Extract provider and receiver GSTINs"""
        gstins = self.extract_gstin(self.text)
        
        # Flipkart's GSTIN (contains AACCF0683K)
        for gstin in gstins:
            if 'AACCF0683K' in gstin:
                self.result.service_provider_gstin = gstin
                break
        
        # First non-Flipkart GSTIN is receiver
        for gstin in gstins:
            if 'AACCF0683K' not in gstin:
                self.result.service_receiver_gstin = gstin
                break

    def _extract_place_of_supply(self):
        """Extract place of supply state code"""
        match = re.search(r'Place\s*of\s*Supply/State\s*Code[:\s]*([^\n,]+)', self.text, re.IGNORECASE)
        if match:
            code = self.extract_state_code(match.group(1))
            if code:
                self.result.place_of_supply_state_code = code

    def _extract_receiver_name(self):
        """Extract receiver business name"""
        patterns = [
            r'Business\s*Name[:\s]*([^\n]+)',
            r'Display\s*Name[:\s]*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if len(name) > 2 and len(name) < 100:
                    self.result.service_receiver_name = name
                    return

    def _extract_line_items(self):
        """Extract line items from Flipkart invoice"""
        if self.result.document_type == "CommercialCreditNote":
            self._extract_commercial_credit_items()
        else:
            self._extract_tax_invoice_items()

    def _extract_tax_invoice_items(self):
        """Extract items from tax invoice/credit note with GST"""
        # Flipkart format: SAC Description Net_Value Rate IGST_Amount Total
        # Example: 998599 Collection Fee 34.46 18.0 6.20 40.66
        
        # Line-by-line parsing for better accuracy
        lines = self.text.split('\n')
        sac_items = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Look for lines starting with SAC code (6 digits)
            sac_match = re.match(r'^(\d{6})\s+(.+)', line)
            if sac_match:
                sac_code = sac_match.group(1)
                rest = sac_match.group(2).strip()
                
                # Parse rest of line: Description + numbers
                # May have description split across this line and next
                
                # Get all numbers from rest
                numbers = re.findall(r'([\d,]+\.?\d*)', rest)
                numbers = [self.normalize_amount(n) for n in numbers if self.normalize_amount(n)]
                
                # Text part (description)
                text_part = re.sub(r'[\d,\.]+', '', rest).strip()
                
                # If description seems incomplete, check next line
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # If next line is continuation (no SAC, no Total)
                    if not re.match(r'^(\d{6}|Total)\s', next_line):
                        next_text = re.sub(r'[\d,\.]+', '', next_line).strip()
                        next_numbers = re.findall(r'([\d,]+\.?\d*)', next_line)
                        next_numbers = [self.normalize_amount(n) for n in next_numbers if self.normalize_amount(n)]
                        
                        if next_text and not next_numbers:
                            text_part = f"{text_part} {next_text}".strip()
                        elif next_numbers:
                            numbers.extend(next_numbers)
                            if next_text:
                                text_part = f"{text_part} {next_text}".strip()
                
                # Expected format: fee, rate, tax, total (4 numbers)
                if len(numbers) >= 4:
                    fee = numbers[0]
                    rate = numbers[1]
                    tax = numbers[2]
                    total = numbers[3]
                elif len(numbers) == 3:
                    fee = numbers[0]
                    rate = 18.0
                    tax = numbers[1]
                    total = numbers[2]
                elif len(numbers) == 2:
                    fee = numbers[0]
                    total = numbers[1]
                    tax = total - fee if total > fee else round(fee * 0.18, 2)
                    rate = 18.0
                else:
                    continue
                
                sac_items.append({
                    'sac': sac_code,
                    'desc': text_part,
                    'fee': fee,
                    'rate': rate,
                    'tax': tax,
                    'total': total
                })
        
        # Add all found items
        for item in sac_items:
            self.result.line_items.append(LineItem(
                category_code_or_hsn=item['sac'],
                service_description=item['desc'] or self.get_sac_description(item['sac']),
                fee_amount=item['fee'],
                igst_amount=item['tax'],
                total_tax_amount=item['tax'],
                total_amount=item['total'],
                tax_rate_percent=item['rate']
            ))
        
        if self.result.line_items:
            return
        
        # Fallback: Try regex patterns
        single_line_pattern = r'(\d{6})\s+([A-Za-z\s\-]+(?:Fee|Recovery)?)\s+([\d,]+\.?\d*)\s+(\d+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)'
        matches = re.findall(single_line_pattern, self.text)
        if matches:
            for match in matches:
                sac_code = match[0]
                desc1 = match[1].strip()
                desc2 = match[2].strip() if match[2] else ""
                description = f"{desc1} {desc2}".strip()
                fee_amount = self.normalize_amount(match[3])
                tax_rate = self.normalize_amount(match[4])
                igst_amount = self.normalize_amount(match[5])
                total_amount = self.normalize_amount(match[6])
                
                if fee_amount and fee_amount > 0:
                    self.result.line_items.append(LineItem(
                        category_code_or_hsn=sac_code,
                        service_description=description or self.get_sac_description(sac_code),
                        fee_amount=fee_amount,
                        igst_amount=igst_amount,
                        total_tax_amount=igst_amount,
                        total_amount=total_amount,
                        tax_rate_percent=tax_rate
                    ))
            return
        
        # Fallback: extract SAC codes and try to find amounts
        sac_codes = list(set(re.findall(r'\b(99\d{4})\b', self.text)))
        for sac in sac_codes:
            # Find amount after SAC code
            amount_pattern = rf'{sac}\s+[A-Za-z\s]+\s+([\d,]+\.?\d*)'
            match = re.search(amount_pattern, self.text)
            if match:
                fee_amount = self.normalize_amount(match.group(1))
                if fee_amount:
                    igst = round(fee_amount * 0.18, 2)
                    self.result.line_items.append(LineItem(
                        category_code_or_hsn=sac,
                        service_description=self.get_sac_description(sac),
                        fee_amount=fee_amount,
                        igst_amount=igst,
                        total_tax_amount=igst,
                        total_amount=fee_amount + igst,
                        tax_rate_percent=18.0
                    ))

    def _extract_commercial_credit_items(self):
        """Extract items from commercial credit note (no GST)"""
        # Format: Sr. No. Description Net Amount
        lines = self.text.split('\n')
        
        for line in lines:
            # Look for numbered items with amounts
            match = re.match(r'(\d+)\s+([A-Za-z\s]+(?:Fee|Discount|Recovery|Amount)?)\s+([\d,]+\.?\d*)\s*$', line.strip())
            if match:
                description = match.group(2).strip()
                amount = self.normalize_amount(match.group(3))
                
                if amount and amount > 0:
                    self.result.line_items.append(LineItem(
                        category_code_or_hsn=None,
                        service_description=description,
                        fee_amount=amount,
                        total_amount=amount,
                        tax_rate_percent=None
                    ))

    def _extract_totals(self):
        """Extract Flipkart-specific totals"""
        # Flipkart format: "Total 224684.89 40443.27 265128.16"
        total_pattern = r'Total\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)'
        match = re.search(total_pattern, self.text, re.IGNORECASE)
        
        if match:
            self.result.subtotal_fee_amount = self.normalize_amount(match.group(1))
            self.result.igst_amount = self.normalize_amount(match.group(2))
            self.result.total_tax_amount = self.result.igst_amount
            self.result.total_invoice_amount = self.normalize_amount(match.group(3))
            return
        
        # Try alternate patterns
        # Subtotal
        subtotal_match = re.search(r'(?:Sub\s*Total|Net\s*Taxable)[:\s]*([\d,]+\.?\d*)', self.text, re.IGNORECASE)
        if subtotal_match:
            self.result.subtotal_fee_amount = self.normalize_amount(subtotal_match.group(1))
        
        # IGST
        igst_match = re.search(r'IGST[:\s@\d%]*([\d,]+\.?\d*)', self.text, re.IGNORECASE)
        if igst_match:
            self.result.igst_amount = self.normalize_amount(igst_match.group(1))
            self.result.total_tax_amount = self.result.igst_amount
        
        # Grand Total
        total_match = re.search(r'Total\s*(?:Amount)?[:\s]*([\d,]+\.?\d*)(?:\s|$)', self.text, re.IGNORECASE)
        if total_match:
            self.result.total_invoice_amount = self.normalize_amount(total_match.group(1))
        
        # Calculate from line items if not found
        if not self.result.total_invoice_amount and self.result.line_items:
            self.result.subtotal_fee_amount = sum(
                (item.fee_amount or 0) if isinstance(item, LineItem) else (item.get('fee_amount') or 0)
                for item in self.result.line_items
            )
            self.result.total_tax_amount = sum(
                (item.total_tax_amount or 0) if isinstance(item, LineItem) else (item.get('total_tax_amount') or 0)
                for item in self.result.line_items
            )
            self.result.igst_amount = self.result.total_tax_amount
            self.result.total_invoice_amount = sum(
                (item.total_amount or 0) if isinstance(item, LineItem) else (item.get('total_amount') or 0)
                for item in self.result.line_items
            )
