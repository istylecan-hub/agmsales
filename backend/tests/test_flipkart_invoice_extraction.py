"""
Flipkart Invoice Extraction Tests
Tests the Flipkart invoice extraction API endpoints and regex-based extraction logic.

Test Coverage:
- Invoice extraction API endpoint /api/invoice/extract/{job_id}
- Invoice Number extraction for 3 document types
- Document type detection: CreditNote, Invoice, CommercialCreditNote
- GSTIN extraction for provider and receiver
- Total amount extraction
- Line items extraction with SAC codes
- Excel export /api/invoice/export/excel/{job_id}
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestFlipkartInvoiceExtraction:
    """Test Flipkart invoice extraction using existing processed job."""
    
    # Job ID with pre-processed Flipkart invoices
    JOB_ID = "4cff7aa3-2d11-46f0-af7d-77fa2b985901"
    
    @pytest.fixture(scope="class")
    def job_data(self):
        """Fetch job data once for all tests in this class."""
        response = requests.get(f"{BASE_URL}/api/invoice/job/{self.JOB_ID}")
        assert response.status_code == 200, f"Failed to fetch job: {response.text}"
        return response.json()
    
    def test_job_exists_and_completed(self, job_data):
        """Test that the job exists and is completed."""
        assert job_data["job_id"] == self.JOB_ID
        assert job_data["status"] == "completed"
        assert job_data["total_files"] == 4
        assert job_data["processed_files"] == 4
        assert job_data["failed_files"] == 0
        print(f"✓ Job {self.JOB_ID} exists with status: {job_data['status']}")
    
    def test_all_files_processed_successfully(self, job_data):
        """Test that all 4 files were processed successfully."""
        files = job_data["files"]
        assert len(files) == 4
        
        for file in files:
            assert file["status"] == "done", f"File {file['filename']} has status {file['status']}"
            assert file["error_message"] is None
            assert file["extraction_data"] is not None
            print(f"✓ {file['filename']} processed successfully")
    
    def test_flipkart1_credit_note_extraction(self, job_data):
        """Test flipkart1.pdf Credit Note extraction (FKCKA prefix)."""
        file_data = next((f for f in job_data["files"] if f["filename"] == "flipkart1.pdf"), None)
        assert file_data is not None, "flipkart1.pdf not found"
        
        data = file_data["extraction_data"]
        
        # Document type and number
        assert data["document_type"] == "CreditNote", f"Expected CreditNote, got {data['document_type']}"
        assert data["invoice_number"] == "FKCKA26000190312", f"Expected FKCKA26000190312, got {data['invoice_number']}"
        
        # Platform detection
        assert data["source_platform"] == "Flipkart"
        
        # GSTIN extraction
        assert data["service_provider_gstin"] == "29AACCF0683K1ZD", f"Provider GSTIN: {data['service_provider_gstin']}"
        assert data["service_receiver_gstin"] == "07AGCPY2367E1Z9", f"Receiver GSTIN: {data['service_receiver_gstin']}"
        
        # Total amounts (expected: 3626.88)
        assert data["total_invoice_amount"] == 3626.88, f"Expected 3626.88, got {data['total_invoice_amount']}"
        assert data["igst_amount"] == 553.25, f"Expected IGST 553.25, got {data['igst_amount']}"
        
        # Line items with SAC codes
        assert len(data["line_items"]) >= 3, f"Expected at least 3 line items, got {len(data['line_items'])}"
        
        sac_codes = [item["category_code_or_hsn"] for item in data["line_items"]]
        assert "998599" in sac_codes, "Missing SAC code 998599"
        assert "996812" in sac_codes, "Missing SAC code 996812"
        
        print("✓ flipkart1.pdf Credit Note extraction verified")
        print(f"  - Invoice Number: {data['invoice_number']}")
        print(f"  - Total Amount: {data['total_invoice_amount']}")
        print(f"  - Line Items: {len(data['line_items'])}")
    
    def test_flipkart2_tax_invoice_extraction(self, job_data):
        """Test flipkart2.pdf Tax Invoice extraction (FKRKA prefix)."""
        file_data = next((f for f in job_data["files"] if f["filename"] == "flipkart2.pdf"), None)
        assert file_data is not None, "flipkart2.pdf not found"
        
        data = file_data["extraction_data"]
        
        # Document type and number
        assert data["document_type"] == "Invoice", f"Expected Invoice, got {data['document_type']}"
        assert data["invoice_number"] == "FKRKA26000290632", f"Expected FKRKA26000290632, got {data['invoice_number']}"
        
        # GSTIN extraction
        assert data["service_provider_gstin"] == "29AACCF0683K1ZD"
        assert data["service_receiver_gstin"] == "07AGCPY2367E1Z9"
        
        # Total amounts (expected: 265128.16)
        assert data["total_invoice_amount"] == 265128.16, f"Expected 265128.16, got {data['total_invoice_amount']}"
        assert data["igst_amount"] == 40443.27, f"Expected IGST 40443.27, got {data['igst_amount']}"
        
        # Line items with SAC codes (including Ad Services)
        assert len(data["line_items"]) >= 4, f"Expected at least 4 line items, got {len(data['line_items'])}"
        
        sac_codes = [item["category_code_or_hsn"] for item in data["line_items"]]
        assert "998599" in sac_codes, "Missing SAC code 998599"
        assert "996812" in sac_codes, "Missing SAC code 996812"
        assert "998365" in sac_codes, "Missing SAC code 998365 (Ad Services)"
        
        print("✓ flipkart2.pdf Tax Invoice extraction verified")
        print(f"  - Invoice Number: {data['invoice_number']}")
        print(f"  - Total Amount: {data['total_invoice_amount']}")
        print(f"  - Line Items: {len(data['line_items'])}")
    
    def test_flipkart3_commercial_credit_note_extraction(self, job_data):
        """Test flipkart3.pdf Commercial Credit Note extraction (ICNDL prefix, no GSTIN/tax)."""
        file_data = next((f for f in job_data["files"] if f["filename"] == "flipkart3.pdf"), None)
        assert file_data is not None, "flipkart3.pdf not found"
        
        data = file_data["extraction_data"]
        
        # Document type and number
        assert data["document_type"] == "CommercialCreditNote", f"Expected CommercialCreditNote, got {data['document_type']}"
        assert data["invoice_number"] == "ICNDL26000031306", f"Expected ICNDL26000031306, got {data['invoice_number']}"
        
        # Commercial Credit Notes should NOT have GSTIN
        assert data["service_provider_gstin"] is None, f"Commercial CN should not have provider GSTIN: {data['service_provider_gstin']}"
        assert data["service_receiver_gstin"] is None, f"Commercial CN should not have receiver GSTIN: {data['service_receiver_gstin']}"
        
        # Total amounts (expected: 428.4, no tax)
        assert data["total_invoice_amount"] == 428.4, f"Expected 428.4, got {data['total_invoice_amount']}"
        assert data["igst_amount"] is None, f"Commercial CN should not have IGST: {data['igst_amount']}"
        
        print("✓ flipkart3.pdf Commercial Credit Note extraction verified")
        print(f"  - Invoice Number: {data['invoice_number']}")
        print(f"  - Total Amount: {data['total_invoice_amount']}")
        print(f"  - GSTIN (should be None): Provider={data['service_provider_gstin']}, Receiver={data['service_receiver_gstin']}")
    
    def test_flipkart4_commercial_credit_note_extraction(self, job_data):
        """Test flipkart4.pdf Commercial Credit Note extraction (ICNDL prefix)."""
        file_data = next((f for f in job_data["files"] if f["filename"] == "flipkart4.pdf"), None)
        assert file_data is not None, "flipkart4.pdf not found"
        
        data = file_data["extraction_data"]
        
        # Document type
        assert data["document_type"] == "CommercialCreditNote", f"Expected CommercialCreditNote, got {data['document_type']}"
        
        # Should have ICNDL prefix
        assert data["invoice_number"].startswith("ICNDL"), f"Expected ICNDL prefix, got {data['invoice_number']}"
        
        # Total amounts (expected: 14.4)
        assert data["total_invoice_amount"] == 14.4, f"Expected 14.4, got {data['total_invoice_amount']}"
        
        # No GSTIN or tax for commercial credit notes
        assert data["service_provider_gstin"] is None
        assert data["service_receiver_gstin"] is None
        assert data["igst_amount"] is None
        
        print("✓ flipkart4.pdf Commercial Credit Note extraction verified")
        print(f"  - Invoice Number: {data['invoice_number']}")
        print(f"  - Total Amount: {data['total_invoice_amount']}")


class TestExcelExport:
    """Test Excel export functionality."""
    
    JOB_ID = "4cff7aa3-2d11-46f0-af7d-77fa2b985901"
    
    def test_excel_export_success(self):
        """Test that Excel export endpoint works for completed job."""
        response = requests.get(f"{BASE_URL}/api/invoice/export/excel/{self.JOB_ID}")
        
        assert response.status_code == 200, f"Excel export failed: {response.status_code} - {response.text}"
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers.get("Content-Type", "")
        
        # Check Content-Disposition header
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp
        assert ".xlsx" in content_disp
        
        # Check file size is reasonable (should have data)
        content_length = len(response.content)
        assert content_length > 1000, f"Excel file too small: {content_length} bytes"
        
        print(f"✓ Excel export successful, file size: {content_length} bytes")


class TestCSVExport:
    """Test CSV export functionality."""
    
    JOB_ID = "4cff7aa3-2d11-46f0-af7d-77fa2b985901"
    
    def test_csv_export_success(self):
        """Test that CSV export endpoint works for completed job."""
        response = requests.get(f"{BASE_URL}/api/invoice/export/csv/{self.JOB_ID}")
        
        assert response.status_code == 200, f"CSV export failed: {response.status_code} - {response.text}"
        assert "text/csv" in response.headers.get("Content-Type", "")
        
        # Check Content-Disposition header
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp
        assert ".csv" in content_disp
        
        # Check file content
        content = response.text
        assert "Invoice Number" in content, "CSV should contain header row"
        assert "FKCKA26000190312" in content or "FKRKA26000290632" in content, "CSV should contain invoice numbers"
        
        print(f"✓ CSV export successful, length: {len(content)} characters")


class TestInvoiceAPIEndpoints:
    """Test Invoice API endpoint responses."""
    
    def test_invoice_root_endpoint(self):
        """Test /api/invoice/ root endpoint."""
        response = requests.get(f"{BASE_URL}/api/invoice/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        print("✓ Invoice API root endpoint is ready")
    
    def test_job_not_found(self):
        """Test 404 response for non-existent job."""
        response = requests.get(f"{BASE_URL}/api/invoice/job/nonexistent-job-id")
        
        assert response.status_code == 404
        print("✓ 404 returned for non-existent job")
    
    def test_export_on_incomplete_job(self):
        """Test export fails for non-completed job (if any exists)."""
        # Just verify the error handling works
        response = requests.get(f"{BASE_URL}/api/invoice/export/excel/nonexistent-job")
        assert response.status_code == 404
        print("✓ Export correctly returns 404 for non-existent job")


class TestDataIntegrity:
    """Test data integrity across all extracted invoices."""
    
    JOB_ID = "4cff7aa3-2d11-46f0-af7d-77fa2b985901"
    
    @pytest.fixture(scope="class")
    def job_data(self):
        """Fetch job data once for all tests."""
        response = requests.get(f"{BASE_URL}/api/invoice/job/{self.JOB_ID}")
        return response.json()
    
    def test_all_amounts_are_valid_numbers(self, job_data):
        """Verify all extracted amounts are valid numbers (not strings or None for required fields)."""
        for file in job_data["files"]:
            data = file["extraction_data"]
            
            # Total invoice amount should always be present
            assert data["total_invoice_amount"] is not None, f"Missing total for {file['filename']}"
            assert isinstance(data["total_invoice_amount"], (int, float)), f"Total should be numeric for {file['filename']}"
            
            # Line item amounts should be numeric when present
            for item in data.get("line_items", []):
                if item.get("fee_amount") is not None:
                    assert isinstance(item["fee_amount"], (int, float)), f"Fee amount should be numeric"
        
        print("✓ All amounts are valid numbers")
    
    def test_sac_codes_format(self, job_data):
        """Verify SAC codes are 6-digit strings starting with 99."""
        for file in job_data["files"]:
            data = file["extraction_data"]
            
            # Only tax invoices and credit notes have SAC codes
            if data["document_type"] in ["Invoice", "CreditNote"]:
                for item in data.get("line_items", []):
                    sac = item.get("category_code_or_hsn")
                    if sac:
                        assert len(sac) == 6, f"SAC code should be 6 digits: {sac}"
                        assert sac.startswith("99"), f"SAC code should start with 99: {sac}"
        
        print("✓ SAC codes are in valid format")
    
    def test_gstin_format(self, job_data):
        """Verify GSTIN format is valid (15 characters)."""
        gstin_pattern = r'^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}$'
        import re
        
        for file in job_data["files"]:
            data = file["extraction_data"]
            
            # Provider GSTIN
            if data.get("service_provider_gstin"):
                gstin = data["service_provider_gstin"]
                assert len(gstin) == 15, f"GSTIN should be 15 chars: {gstin}"
                assert re.match(gstin_pattern, gstin), f"Invalid GSTIN format: {gstin}"
            
            # Receiver GSTIN
            if data.get("service_receiver_gstin"):
                gstin = data["service_receiver_gstin"]
                assert len(gstin) == 15, f"GSTIN should be 15 chars: {gstin}"
                assert re.match(gstin_pattern, gstin), f"Invalid GSTIN format: {gstin}"
        
        print("✓ GSTIN format is valid")
    
    def test_extraction_method_recorded(self, job_data):
        """Verify extraction method is recorded for audit trail."""
        for file in job_data["files"]:
            data = file["extraction_data"]
            assert "_extraction_method" in data, f"Missing _extraction_method for {file['filename']}"
            assert data["_extraction_method"] == "flipkart_regex", f"Expected flipkart_regex, got {data['_extraction_method']}"
        
        print("✓ Extraction method recorded as flipkart_regex")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
