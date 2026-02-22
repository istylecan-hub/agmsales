# Generic Invoice Parser
# Fallback parser for unknown invoice formats

import re
from .base_parser import BaseParser, NormalizedInvoice, LineItem


class GenericParser(BaseParser):
    """Fallback parser for unknown/generic GST invoice formats"""
    
    TEMPLATE_ID = "UNKNOWN_GENERIC_GST"
    PLATFORM_NAME = "Unknown"

    def parse(self) -> NormalizedInvoice:
        """Parse generic invoice text"""
        self.result.source_platform = "Unknown"
        
        # Detect document type
        if "credit note" in self.text.lower():
            self.result.document_type = "CreditNote"
        else:
            self.result.document_type = "Invoice"
        
        self._extract_invoice_number()
        self._extract_date()
        self._extract_gstins()
        self._extract_place_of_supply()
        self._extract_receiver_name()
        self._extract_provider_name()
        self._extract_line_items()
        self._extract_totals()
        
        return self.result

    def _extract_invoice_number(self):
        """Extract invoice number from any format"""
        patterns = [
            r'Invoice\s*(?:No\.?|Number|#)[:\s]*([A-Z0-9/\-]+)',
            r'Credit\s*Note\s*(?:No\.?|Number|#)[:\s]*([A-Z0-9/\-]+)',
            r'Document\s*(?:No\.?|Number)[:\s]*([A-Z0-9/\-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                inv = match.group(1).strip()
                # Validate it's not a keyword
                if inv.lower() not in ['date', 'details', 'tax', 'value', 'amount']:
                    self.result.invoice_number = inv
                    return

    def _extract_date(self):
        """Extract date from any format"""
        patterns = [
            r'(?:Invoice|Credit\s*Note|Document)\s*Date[:\s]*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
            r'Date[:\s]*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{4})',
            r'Dated[:\s]*(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                self.result.invoice_date = self.normalize_date(match.group(1))
                return

    def _extract_gstins(self):
        """Extract all GSTINs"""
        gstins = self.extract_gstin(self.text)
        
        if gstins:
            self.result.service_provider_gstin = gstins[0]
        if len(gstins) > 1:
            self.result.service_receiver_gstin = gstins[1]

    def _extract_place_of_supply(self):
        """Extract place of supply"""
        patterns = [
            r'Place\s*of\s*Supply[:\s]*([A-Za-z\s\-]+)',
            r'State\s*Code[:\s]*(\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                code = self.extract_state_code(match.group(1))
                if code:
                    self.result.place_of_supply_state_code = code
                    return
                # Direct code
                if match.group(1).isdigit():
                    self.result.place_of_supply_state_code = match.group(1)
                    return

    def _extract_receiver_name(self):
        """Extract receiver name"""
        patterns = [
            r'Bill\s*(?:To|ed\s*To)[:\s]*\n?(?:Name[:\s]*)?([A-Za-z][A-Za-z\s]+)',
            r'Buyer[:\s]*\n?(?:Name[:\s]*)?([A-Za-z][A-Za-z\s]+)',
            r'Customer[:\s]*\n?([A-Za-z][A-Za-z\s]+)',
            r'Business\s*Name[:\s]*([A-Za-z][A-Za-z\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                name = match.group(1).strip().split('\n')[0].strip()
                if len(name) > 2 and len(name) < 100:
                    self.result.service_receiver_name = name
                    return

    def _extract_provider_name(self):
        """Extract provider/seller name"""
        patterns = [
            r'Bill\s*(?:From|ed\s*From)[:\s]*\n?(?:Name[:\s]*)?([A-Za-z][A-Za-z\s]+(?:Limited|Ltd|Pvt|Private)?)',
            r'Seller[:\s]*\n?(?:Name[:\s]*)?([A-Za-z][A-Za-z\s]+(?:Limited|Ltd|Pvt|Private)?)',
            r'([A-Z][A-Za-z\s]+(?:Private\s*Limited|Pvt\.?\s*Ltd\.?))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                name = match.group(1).strip().split('\n')[0].strip()
                if len(name) > 5 and len(name) < 100:
                    self.result.service_provider_name = name
                    return

    def _extract_line_items(self):
        """Extract line items using multiple strategies"""
        # Strategy 1: Look for SAC codes with amounts
        self._extract_items_by_sac()
        
        # Strategy 2: Look for service keywords with amounts
        if not self.result.line_items:
            self._extract_items_by_keywords()
        
        # Strategy 3: Extract any table-like data
        if not self.result.line_items:
            self._extract_items_from_table()

    def _extract_items_by_sac(self):
        """Extract items by SAC code"""
        lines = self.text.split('\n')
        processed = set()
        
        for line in lines:
            sac_match = re.search(r'(99\d{4}|\d{6})', line)
            if not sac_match:
                continue
            
            sac_code = sac_match.group(1)
            if sac_code in processed:
                continue
            
            # Get amounts from line
            amounts = re.findall(r'([\d,]+\.?\d*)', line.replace(sac_code, ''))
            amounts = [self.normalize_amount(a) for a in amounts if self.normalize_amount(a)]
            amounts = [a for a in amounts if a and a > 0]
            
            if not amounts:
                continue
            
            # Description before SAC
            desc = line[:sac_match.start()].strip()
            desc = re.sub(r'^\d+\.?\s*', '', desc).strip()
            
            fee = amounts[0]
            total = amounts[-1] if len(amounts) > 1 else fee
            tax = total - fee if total > fee else round(fee * 0.18, 2)
            
            self.result.line_items.append(LineItem(
                category_code_or_hsn=sac_code,
                service_description=desc or self.get_sac_description(sac_code),
                fee_amount=fee,
                igst_amount=tax,
                total_tax_amount=tax,
                total_amount=total if total > fee else fee + tax,
                tax_rate_percent=18.0
            ))
            processed.add(sac_code)

    def _extract_items_by_keywords(self):
        """Extract items by service keywords"""
        keywords = [
            'commission', 'fee', 'shipping', 'delivery', 'handling',
            'service', 'charges', 'monetization', 'advertising',
            'fulfillment', 'collection', 'platform'
        ]
        
        lines = self.text.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            
            for kw in keywords:
                if kw in line_lower:
                    # Extract amounts
                    amounts = re.findall(r'([\d,]+\.?\d*)', line)
                    amounts = [self.normalize_amount(a) for a in amounts if self.normalize_amount(a)]
                    amounts = [a for a in amounts if a and a > 0]
                    
                    if not amounts:
                        continue
                    
                    # Get description
                    desc_match = re.match(r'^([A-Za-z\s\-&/()]+)', line.strip())
                    desc = desc_match.group(1).strip() if desc_match else kw.title()
                    
                    fee = amounts[0]
                    total = amounts[-1] if len(amounts) > 1 else None
                    tax = None
                    
                    if total and total > fee:
                        tax = total - fee
                    else:
                        tax = round(fee * 0.18, 2)
                        total = fee + tax
                    
                    self.result.line_items.append(LineItem(
                        service_description=desc,
                        fee_amount=fee,
                        igst_amount=tax,
                        total_tax_amount=tax,
                        total_amount=total,
                        tax_rate_percent=18.0
                    ))
                    break

    def _extract_items_from_table(self):
        """Extract from generic table format"""
        # Look for rows with multiple numbers
        number_pattern = r'([\d,]+\.?\d*)'
        lines = self.text.split('\n')
        
        for line in lines:
            if len(line.strip()) < 10:
                continue
            
            amounts = re.findall(number_pattern, line)
            amounts = [self.normalize_amount(a) for a in amounts if self.normalize_amount(a)]
            amounts = [a for a in amounts if a and a > 0.01]
            
            if len(amounts) >= 2:
                # Text part (non-numbers)
                text_part = re.sub(r'[\d,\.]+', '', line).strip()
                text_part = re.sub(r'\s+', ' ', text_part).strip()
                
                if len(text_part) > 3:
                    fee = min(amounts)
                    total = max(amounts)
                    tax = total - fee if total > fee else 0
                    
                    self.result.line_items.append(LineItem(
                        service_description=text_part[:60],
                        fee_amount=fee,
                        igst_amount=tax if tax > 0 else None,
                        total_tax_amount=tax if tax > 0 else None,
                        total_amount=total,
                        tax_rate_percent=18.0 if tax > 0 else None
                    ))

    def _extract_totals(self):
        """Extract totals from generic format"""
        # Grand Total
        total_patterns = [
            r'(?:Grand\s*)?Total\s*(?:Amount|Invoice|Payable)?[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Net\s*(?:Amount|Payable)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                self.result.total_invoice_amount = self.normalize_amount(match.group(1))
                break
        
        # Subtotal
        subtotal_patterns = [
            r'Sub\s*Total[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Taxable\s*(?:Value|Amount)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ]
        
        for pattern in subtotal_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                self.result.subtotal_fee_amount = self.normalize_amount(match.group(1))
                break
        
        # Tax amounts
        igst_match = re.search(r'IGST[:\s@\d%]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)', self.text, re.IGNORECASE)
        if igst_match:
            self.result.igst_amount = self.normalize_amount(igst_match.group(1))
            self.result.total_tax_amount = self.result.igst_amount
        
        cgst_match = re.search(r'CGST[:\s@\d%]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)', self.text, re.IGNORECASE)
        sgst_match = re.search(r'SGST[:\s@\d%]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)', self.text, re.IGNORECASE)
        
        if cgst_match:
            self.result.cgst_amount = self.normalize_amount(cgst_match.group(1))
        if sgst_match:
            self.result.sgst_amount = self.normalize_amount(sgst_match.group(1))
        
        if self.result.cgst_amount and self.result.sgst_amount:
            self.result.total_tax_amount = self.result.cgst_amount + self.result.sgst_amount
        
        # Calculate from line items if missing
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
                self.result.total_invoice_amount = sum(
                    (item.total_amount or 0) if isinstance(item, LineItem) else (item.get('total_amount') or 0)
                    for item in self.result.line_items
                )
        
        # If we only have total, calculate backwards
        if self.result.total_invoice_amount and not self.result.subtotal_fee_amount:
            total = self.result.total_invoice_amount
            self.result.subtotal_fee_amount = round(total / 1.18, 2)
            self.result.total_tax_amount = round(total - self.result.subtotal_fee_amount, 2)
            self.result.igst_amount = self.result.total_tax_amount
