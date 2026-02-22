# Salary Calculator + Invoice Data Extractor Application

## Original Problem Statement
A combined application for:
1. **Salary Calculator Module**: Employee management, attendance processing from Excel, salary calculation with configurable rules, monthly salary history
2. **Invoice Extractor Module**: Upload PDF invoices from multiple e-commerce platforms, extract key data, export to Excel

## Current Status: In Progress

---

## What's Been Implemented

### Salary Calculator (Complete)
- [x] Employee management (CRUD operations)
- [x] Attendance processing from Excel
- [x] Salary calculation with configurable rules
- [x] Monthly salary history (save/view/compare)
- [x] Report generation

### Invoice Extractor (Complete - Backend)
- [x] **4-Stage Hybrid Pipeline** implemented:
  - Stage A: PDF text extraction (pdfplumber + OCR fallback)
  - Stage B: Template detection
  - Stage C: Template-specific parsing
  - Stage D: LLM fallback (optional)

- [x] **Template-Specific Parsers** for:
  - Amazon (Tax Invoice, Credit Note)
  - Flipkart (Tax Invoice, Credit Note, Commercial Credit Note)
  - Meesho (Tax Invoice)
  - V-Mart (Tax Invoice)
  - AceVector/Snapdeal (Tax Invoice)
  - Myntra (Tax Invoice)
  - Fashnear (Tax Invoice, Credit Note)
  - Generic GST (fallback)

- [x] **Normalized Output Schema**:
  - Header fields (invoice#, date, GSTINs, provider, receiver, place of supply)
  - Totals (subtotal, CGST, SGST, IGST, total tax, total amount)
  - Line items (SAC/HSN, description, fee, taxes, total)
  - Validation status

- [x] **Excel Export** with 3 sheets:
  - Invoice_Details (header-level)
  - Line_Items (long format)
  - Errors_Logs (validation issues)

### Testing Results (Feb 2026)
| Platform | Invoice # | Total | Items | Status |
|----------|-----------|-------|-------|--------|
| Amazon | KA-2526-3179016 | 92.04 | 1 | ✅ |
| Flipkart | FKCKA26001044544 | 650.46 | 3 | ✅ |
| Meesho | TI/01/26/1599650 | 378,809.84 | 3 | ✅ |
| V-Mart | COM/2526/IN10961 | 2,926.29 | 1 | ✅ |
| AceVector | 2526HR/IN/138081 | 16,842.97 | 1 | ✅ |

---

## API Endpoints

### Invoice Extractor
- `POST /api/invoice/upload` - Upload PDF files
- `POST /api/invoice/extract/{job_id}` - Start extraction
- `GET /api/invoice/job/{job_id}` - Get job status
- `GET /api/invoice/export/excel/{job_id}` - Download Excel
- `GET /api/invoice/export/csv/{job_id}` - Download CSV
- `DELETE /api/invoice/job/{job_id}` - Delete job

### Salary Calculator
- `GET/POST /api/employees` - Employee management
- `POST /api/attendance` - Upload attendance
- `GET/POST /api/salary-history` - Salary history management

---

## Architecture

```
/app/
├── backend/
│   ├── server.py                  # FastAPI app, routes
│   ├── invoice_extractor.py       # Job management, export logic
│   ├── universal_extractor.py     # 4-stage hybrid pipeline
│   └── parsers/
│       ├── __init__.py
│       ├── base_parser.py         # BaseParser, NormalizedInvoice
│       ├── amazon_parser.py
│       ├── flipkart_parser.py
│       ├── meesho_parser.py
│       ├── vmart_parser.py
│       ├── acevector_parser.py
│       ├── myntra_parser.py
│       ├── fashnear_parser.py
│       └── generic_parser.py
├── frontend/
│   └── src/
│       └── pages/
│           ├── InvoiceExtractor.jsx
│           └── SalaryReport.jsx
```

---

## Prioritized Backlog

### P0 - Critical
- [ ] Fix CORS error for production deployment
- [ ] Test with user's actual invoice samples

### P1 - High
- [ ] Deploy updated invoice extractor
- [ ] Add confidence score indicator in UI

### P2 - Low
- [ ] Fix navigation visibility UI glitch
- [ ] Add more platform templates as needed

---

## Known Issues
1. **CORS Error**: Production deployment blocked by CORS - middleware fix applied but needs verification
2. **MongoDB**: Currently using local MongoDB; ensure MONGO_URL is configured for production

---

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn/UI
- **Backend**: FastAPI, Python
- **Database**: MongoDB (motor async driver)
- **PDF Processing**: pdfplumber, PyPDF2, pytesseract (OCR)
- **Excel**: openpyxl
