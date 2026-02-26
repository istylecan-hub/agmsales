# Enhanced Generic Invoice Parser
# Handles unknown/generic GST invoice formats with intelligent tax merging

import re
from typing import List, Dict, Optional, Tuple
from .base_parser import BaseParser, NormalizedInvoice, LineItem


class GenericParser(BaseParser):
    """Enhanced fallback parser for unknown/generic GST invoice formats"""
    
    TEMPLATE_ID = "UNKNOWN_GENERIC_GST"
    PLATFORM_NAME = "Unknown"

    def parse(self) -> NormalizedInvoice:
        """Parse generic invoice text with enhanced extraction"""
        self.result.source_platform = "Unknown"
        self.result.platform_name = "Unknown"
        
        # Detect document type
        self.result.document_type = self.detect_document_type()
        
        # Extract metadata
        self._extract_invoice_number()
        self._extract_dates()
        self._extract_gstins()
        self._extract_place_of_supply()
        self._extract_parties()
        
        # Extract line items with tax merging
        self._extract_line_items_enhanced()
        
        # Extract totals
        self._extract_totals()
        
        # Reconcile if needed
        self._reconcile_from_line_items()
        
        return self.result

    def _extract_invoice_number(self):
        """Extract invoice/credit note/debit note number"""
        patterns = [
            r'Credit\s*Note\s*(?:No\.?|Number|#)[:\s]*([A-Z0-9/\-]+)',
            r'Debit\s*Note\s*(?:No\.?|Number|#)[:\s]*([A-Z0-9/\-]+)',
            r'Invoice\s*(?:No\.?|Number|#)[:\s]*([A-Z0-9/\-]+)',
            r'Document\s*(?:No\.?|Number)[:\s]*([A-Z0-9/\-]+)',
            r'Tax\s*Invoice\s*No\.?[:\s]*([A-Z0-9/\-]+)',
            r'CN\s*No\.?[:\s]*([A-Z0-9/\-]+)',
            r'DN\s*No\.?[:\s]*([A-Z0-9/\-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                inv = match.group(1).strip()
                # Validate it's not a keyword
                if inv.lower() not in ['date', 'details', 'tax', 'value', 'amount', 'the']:
                    self.result.invoice_number = inv
                    return

    def _extract_dates(self):
        """Extract invoice date and original invoice date (for credit notes)"""
        # Invoice date patterns
        date_patterns = [
            r'(?:Invoice|Credit\s*Note|Debit\s*Note|Document)\s*Date[:\s]*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
            r'Date\s*of\s*(?:Invoice|Issue)[:\s]*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
            r'Dated?[:\s]*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{4})',
            r'Date[:\s]*(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                self.result.invoice_date = self.normalize_date(match.group(1))
                break
        
        # Original invoice date (for credit notes)
        if self.result.document_type in ['CreditNote', 'DebitNote']:
            orig_patterns = [
                r'Original\s*Invoice\s*(?:No\.?|Number)[:\s]*([A-Z0-9/\-]+)',
                r'Against\s*Invoice\s*(?:No\.?|Number)?[:\s]*([A-Z0-9/\-]+)',
                r'Ref\.?\s*Invoice[:\s]*([A-Z0-9/\-]+)',
            ]
            
            for pattern in orig_patterns:
                match = re.search(pattern, self.text, re.IGNORECASE)
                if match:
                    self.result.original_invoice_number = match.group(1).strip()
                    break
            
            orig_date_patterns = [
                r'Original\s*Invoice\s*Date[:\s]*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
            ]
            
            for pattern in orig_date_patterns:
                match = re.search(pattern, self.text, re.IGNORECASE)
                if match:
                    self.result.original_invoice_date = self.normalize_date(match.group(1))
                    break

    def _extract_gstins(self):
        """Extract supplier and buyer GSTINs"""
        gstins = self.extract_gstin(self.text)
        
        if gstins:
            self.result.supplier_gstin = gstins[0]
            self.result.service_provider_gstin = gstins[0]
        if len(gstins) > 1:
            self.result.buyer_gstin = gstins[1]
            self.result.service_receiver_gstin = gstins[1]

    def _extract_place_of_supply(self):
        """Extract place of supply and state code"""
        patterns = [
            r'Place\s*of\s*Supply[:\s]*([A-Za-z\s\-]+?)(?:\(|$|\n)',
            r'Place\s*of\s*Supply[:\s]*(\d{2})\s*[-–]?\s*([A-Za-z]+)',
            r'State\s*(?:Code)?[:\s]*(\d{2})',
            r'Supply\s*State[:\s]*([A-Za-z\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                if match.lastindex == 2:
                    # Pattern with code and name
                    self.result.state_code = match.group(1)
                    self.result.place_of_supply = f"{match.group(1)}-{match.group(2)}"
                else:
                    text = match.group(1).strip()
                    code = self.extract_state_code(text)
                    if code:
                        self.result.state_code = code
                        self.result.place_of_supply = code
                        self.result.place_of_supply_state_code = code
                        return
                    if text.isdigit() and len(text) == 2:
                        self.result.state_code = text
                        self.result.place_of_supply_state_code = text
                        return
        
        # Try to extract from GSTIN (first 2 digits)
        if self.result.buyer_gstin:
            self.result.state_code = self.result.buyer_gstin[:2]
            self.result.place_of_supply_state_code = self.result.state_code

    def _extract_parties(self):
        """Extract supplier and buyer names"""
        # Supplier patterns
        supplier_patterns = [
            r'(?:From|Seller|Supplier|Vendor|Billed?\s*By)[:\s]*\n?([A-Z][A-Za-z\s]+(?:Limited|Ltd|Pvt|Private|LLP)?)',
            r'([A-Z][A-Za-z\s]+(?:Private\s*Limited|Pvt\.?\s*Ltd\.?|Limited|LLP))',
        ]
        
        for pattern in supplier_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                name = match.group(1).strip().split('\n')[0].strip()
                if len(name) > 5 and len(name) < 100:
                    self.result.supplier_name = name
                    self.result.service_provider_name = name
                    break
        
        # Buyer patterns
        buyer_patterns = [
            r'(?:Bill\s*(?:To|ed\s*To)|Buyer|Customer|Sold\s*To|Ship\s*To)[:\s]*\n?(?:Name[:\s]*)?([A-Za-z][A-Za-z\s]+)',
            r'Recipient[:\s]*\n?([A-Za-z][A-Za-z\s]+)',
        ]
        
        for pattern in buyer_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                name = match.group(1).strip().split('\n')[0].strip()
                if len(name) > 2 and len(name) < 100:
                    self.result.buyer_name = name
                    self.result.service_receiver_name = name
                    break

    def _extract_line_items_enhanced(self):
        """Extract line items with intelligent tax merging"""
        # Try multiple strategies
        
        # Strategy 1: Extract from "Details of Fees" table (preferred for detailed breakdown)
        items = self._extract_from_details_table()
        if items:
            self.result.line_items = items
            return
        
        # Strategy 2: Extract SAC-based rows with tax merging
        items = self._extract_sac_based_items()
        if items:
            self.result.line_items = items
            return
        
        # Strategy 3: Extract by service keywords
        items = self._extract_by_keywords()
        if items:
            self.result.line_items = items
            return
        
        # Strategy 4: Generic table extraction
        items = self._extract_generic_table()
        if items:
            self.result.line_items = items

    def _extract_from_details_table(self) -> List[LineItem]:
        """Extract from 'Details of Fees' style tables - avoids summary duplication"""
        # Look for detailed breakdown section
        details_section = None
        
        markers = ['details of fees', 'fee details', 'particulars', 'description of services']
        text_lower = self.text.lower()
        
        for marker in markers:
            idx = text_lower.find(marker)
            if idx != -1:
                details_section = self.text[idx:idx+3000]
                break
        
        if not details_section:
            return []
        
        # Parse detailed rows
        raw_rows = []
        lines = details_section.split('\n')
        
        for line in lines:
            if len(line.strip()) < 5:
                continue
            
            # Look for rows with SAC codes and amounts
            sac_match = re.search(r'(99\d{4}|\d{6})', line)
            amounts = re.findall(r'(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)', line)
            amounts = [self.normalize_amount(a) for a in amounts if self.normalize_amount(a)]
            
            if sac_match and amounts:
                desc = line[:sac_match.start()].strip()
                desc = re.sub(r'^\d+\.?\s*', '', desc).strip()  # Remove line numbers
                
                raw_rows.append({
                    'sac': sac_match.group(1),
                    'description': desc,
                    'amount': amounts[0] if amounts else 0
                })
            elif amounts and len(amounts) >= 1:
                # Check if it's a tax row
                line_upper = line.upper()
                if 'SGST' in line_upper or 'CGST' in line_upper or 'IGST' in line_upper:
                    raw_rows.append({
                        'description': line.strip(),
                        'amount': amounts[0]
                    })
        
        # Use tax merge logic
        if raw_rows:
            return self.merge_tax_rows(raw_rows)
        
        return []

    def _extract_sac_based_items(self) -> List[LineItem]:
        """Extract items by SAC code with tax row merging"""
        raw_rows = []
        lines = self.text.split('\n')
        
        for line in lines:
            if len(line.strip()) < 5:
                continue
            
            line_upper = line.upper()
            
            # Check for SAC code row
            sac_match = re.search(r'(99\d{4}|\d{6})', line)
            amounts = re.findall(r'([\d,]+\.?\d*)', line)
            amounts = [self.normalize_amount(a) for a in amounts if self.normalize_amount(a) and self.normalize_amount(a) > 0]
            
            if sac_match and amounts:
                desc = line[:sac_match.start()].strip()
                desc = re.sub(r'^\d+\.?\s*', '', desc).strip()
                
                raw_rows.append({
                    'sac': sac_match.group(1),
                    'description': desc or self.get_sac_description(sac_match.group(1)),
                    'amount': amounts[0]
                })
            elif 'SGST' in line_upper or 'CGST' in line_upper or 'IGST' in line_upper:
                if amounts:
                    raw_rows.append({
                        'description': line.strip(),
                        'amount': amounts[0]
                    })
        
        if raw_rows:
            return self.merge_tax_rows(raw_rows)
        
        return []

    def _extract_by_keywords(self) -> List[LineItem]:
        """Extract items by service keywords"""
        keywords = [
            'commission', 'fee', 'shipping', 'delivery', 'handling',
            'service', 'charges', 'monetization', 'advertising',
            'fulfillment', 'collection', 'platform', 'marketplace',
            'logistics', 'storage', 'picking', 'packing'
        ]
        
        raw_rows = []
        lines = self.text.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            
            for kw in keywords:
                if kw in line_lower:
                    amounts = re.findall(r'([\d,]+\.?\d*)', line)
                    amounts = [self.normalize_amount(a) for a in amounts if self.normalize_amount(a) and self.normalize_amount(a) > 0]
                    
                    if amounts:
                        desc_match = re.match(r'^([A-Za-z\s\-&/()]+)', line.strip())
                        desc = desc_match.group(1).strip() if desc_match else kw.title()
                        
                        # Check if this is a tax row
                        if 'sgst' in line_lower or 'cgst' in line_lower or 'igst' in line_lower:
                            raw_rows.append({
                                'description': line.strip(),
                                'amount': amounts[0]
                            })
                        else:
                            raw_rows.append({
                                'description': desc,
                                'amount': amounts[0]
                            })
                    break
        
        if raw_rows:
            return self.merge_tax_rows(raw_rows)
        
        return []

    def _extract_generic_table(self) -> List[LineItem]:
        """Extract from generic table format"""
        items = []
        lines = self.text.split('\n')
        line_no = 0
        
        for line in lines:
            if len(line.strip()) < 10:
                continue
            
            # Skip tax rows
            line_upper = line.upper()
            if 'SGST' in line_upper or 'CGST' in line_upper or 'IGST' in line_upper:
                continue
            
            amounts = re.findall(r'([\d,]+\.?\d*)', line)
            amounts = [self.normalize_amount(a) for a in amounts if self.normalize_amount(a) and self.normalize_amount(a) > 0.01]
            
            if len(amounts) >= 2:
                # Text part
                text_part = re.sub(r'[\d,\.]+', '', line).strip()
                text_part = re.sub(r'\s+', ' ', text_part).strip()
                
                if len(text_part) > 3:
                    line_no += 1
                    fee = min(amounts)
                    total = max(amounts)
                    tax = total - fee if total > fee else 0
                    
                    is_neg = self.is_negative_amount(line)
                    
                    items.append(LineItem(
                        line_no=line_no,
                        description=text_part[:60],
                        service_description=text_part[:60],
                        taxable_amount=fee,
                        fee_amount=fee,
                        igst_amount=tax if tax > 0 else None,
                        total_tax_amount=tax if tax > 0 else None,
                        total_line_amount=total,
                        total_amount=total,
                        tax_rate_percent=round((tax/fee)*100, 1) if tax > 0 and fee > 0 else None,
                        is_negative=is_neg
                    ))
        
        return items

    def _extract_totals(self):
        """Extract totals with enhanced patterns"""
        # Grand Total
        total_patterns = [
            r'(?:Grand\s*)?Total\s*(?:Amount|Invoice|Payable)?[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Net\s*(?:Amount|Payable)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Total\s*Invoice\s*(?:Value|Amount)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Amount\s*Payable[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                val = self.normalize_amount(match.group(1))
                if val and val > 0:
                    self.result.grand_total = val
                    self.result.total_invoice_amount = val
                    break
        
        # Subtotal / Taxable Value
        subtotal_patterns = [
            r'Sub\s*[-\s]?Total[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Taxable\s*(?:Value|Amount)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Total\s*(?:Taxable|Fee)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Assessment\s*Value[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ]
        
        for pattern in subtotal_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                val = self.normalize_amount(match.group(1))
                if val and val > 0:
                    self.result.subtotal = val
                    self.result.subtotal_fee_amount = val
                    break
        
        # Tax amounts
        # IGST
        igst_patterns = [
            r'IGST[:\s@]*(?:\d+(?:\.\d+)?\s*%)?[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Integrated\s*(?:GST|Tax)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ]
        for pattern in igst_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                val = self.normalize_amount(match.group(1))
                if val and val > 0:
                    self.result.igst_amount = val
                    break
        
        # CGST
        cgst_patterns = [
            r'CGST[:\s@]*(?:\d+(?:\.\d+)?\s*%)?[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'Central\s*(?:GST|Tax)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ]
        for pattern in cgst_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                val = self.normalize_amount(match.group(1))
                if val and val > 0:
                    self.result.cgst_amount = val
                    break
        
        # SGST
        sgst_patterns = [
            r'SGST[:\s@]*(?:\d+(?:\.\d+)?\s*%)?[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
            r'State\s*(?:GST|Tax)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)',
        ]
        for pattern in sgst_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                val = self.normalize_amount(match.group(1))
                if val and val > 0:
                    self.result.sgst_amount = val
                    break
        
        # Calculate total tax
        if self.result.igst_amount:
            self.result.total_tax = self.result.igst_amount
            self.result.total_tax_amount = self.result.igst_amount
            # If IGST is present, CGST/SGST should be 0
            self.result.cgst_amount = 0
            self.result.sgst_amount = 0
        elif self.result.cgst_amount or self.result.sgst_amount:
            self.result.total_tax = (self.result.cgst_amount or 0) + (self.result.sgst_amount or 0)
            self.result.total_tax_amount = self.result.total_tax

    def _reconcile_from_line_items(self):
        """Calculate totals from line items if header totals missing"""
        if not self.result.line_items:
            # If no line items and we have total, calculate backwards
            if self.result.grand_total and not self.result.subtotal:
                total = self.result.grand_total
                # Assume 18% tax
                self.result.subtotal = round(total / 1.18, 2)
                self.result.subtotal_fee_amount = self.result.subtotal
                self.result.total_tax = round(total - self.result.subtotal, 2)
                self.result.total_tax_amount = self.result.total_tax
                if not self.result.igst_amount and not self.result.cgst_amount:
                    self.result.igst_amount = self.result.total_tax
            return
        
        # Calculate from line items
        fee_sum = 0
        tax_sum = 0
        total_sum = 0
        
        for item in self.result.line_items:
            if isinstance(item, LineItem):
                fee_sum += item.taxable_amount or item.fee_amount or 0
                tax_sum += item.total_tax_amount or 0
                total_sum += item.total_line_amount or item.total_amount or 0
            else:
                fee_sum += item.get('taxable_amount') or item.get('fee_amount') or 0
                tax_sum += item.get('total_tax_amount') or 0
                total_sum += item.get('total_line_amount') or item.get('total_amount') or 0
        
        if not self.result.subtotal and fee_sum > 0:
            self.result.subtotal = fee_sum
            self.result.subtotal_fee_amount = fee_sum
        
        if not self.result.total_tax and tax_sum > 0:
            self.result.total_tax = tax_sum
            self.result.total_tax_amount = tax_sum
        
        if not self.result.grand_total and total_sum > 0:
            self.result.grand_total = total_sum
            self.result.total_invoice_amount = total_sum
