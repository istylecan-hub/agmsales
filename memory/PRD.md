# Multi-Module ERP Application (Salary + Invoice + OrderHub)

## Original Problem Statement
A comprehensive ERP application combining:
1. **Salary Calculator Module**: Employee management, attendance processing from Excel, salary calculation with configurable rules, monthly salary history
2. **Invoice Extractor Module**: Upload PDF invoices from multiple e-commerce platforms (Amazon, Flipkart, JioMart, etc.), extract key data with GST tax merging, export to Excel
3. **OrderHub Module**: E-commerce order consolidation system for multi-platform order management, SKU mapping, and reporting

## Current Status: Active Development

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

### OrderHub Module (Complete - Feb 28, 2026)
- [x] **Core Features**:
  - Dashboard with enterprise-level analytics
  - Multi-platform order upload (Flipkart, Amazon, etc.)
  - Order reports with filtering
  - Master SKU management
  - Unmapped SKU tracking and resolution
  
- [x] **Performance Optimizations**:
  - Chunked file processing (5000 rows/chunk)
  - Bulk database inserts (1000 batch)
  - 100MB file upload limit
  - No artificial row limits
  
- [x] **Admin Controls** (Completed Feb 28, 2026):
  - `/api/orderhub/admin/data-summary` - Data overview
  - `/api/orderhub/admin/reset-orders` - Reset order data (preserves master SKUs)
  - `/api/orderhub/admin/reset-master` - Reset master SKU mappings
  - `/api/orderhub/admin/delete-upload/{file_id}` - Delete specific upload
  - `/api/orderhub/admin/reset-all` - Complete nuclear reset
  - `/api/orderhub/admin/remap-unmapped` - Re-map SKUs
  - All destructive endpoints have `confirm=true` safety mechanism
  - Frontend admin page at `/orderhub/admin`

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
│   ├── server.py                  # FastAPI app, all routes integrated
│   ├── invoice_extractor.py       # Job management, export logic
│   ├── universal_extractor.py     # 4-stage hybrid pipeline
│   ├── parsers/                   # Invoice parsers
│   │   ├── base_parser.py         
│   │   ├── amazon_parser.py
│   │   ├── flipkart_parser.py
│   │   ├── jiomart_parser.py
│   │   └── ... (generic, meesho, vmart, etc.)
│   └── orderhub/                  # OrderHub module
│       ├── models.py
│       ├── services/
│       │   ├── file_processor.py  # Chunked processing
│       │   └── unmapped.py        # SKU mapping logic
│       └── routes/
│           ├── admin.py           # Admin/reset endpoints
│           ├── upload.py
│           ├── dashboard.py
│           └── ... (8 route files total)
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── InvoiceExtractor.jsx
│       │   ├── SalaryReport.jsx
│       │   └── orderhub/
│       │       ├── Dashboard.jsx
│       │       ├── Upload.jsx
│       │       ├── Reports.jsx
│       │       ├── MasterSKUs.jsx
│       │       ├── UnmappedSKUs.jsx
│       │       └── Admin.jsx      # NEW - Admin controls
│       └── components/
│           └── Layout.jsx         # Navigation with OrderHub links
```

---

## Prioritized Backlog

### P0 - Critical
- [x] ~~OrderHub Admin Controls~~ (Completed Feb 28, 2026)
- [ ] Verify Salary Module fix (future dates not counted as absent)

### P1 - High
- [ ] Retry deployment (MongoDB auth error is platform issue, not code)
- [ ] Full end-to-end testing before deployment

### P2 - Low  
- [ ] Fix navigation visibility UI glitch
- [ ] Add more platform templates as needed

---

## Known Issues
1. **Deployment MongoDB Auth Error**: Platform-level issue with Emergent deployment connecting to MongoDB Atlas (SCRAM-SHA-1 auth error). Not a code issue - retry deployment or contact Emergent support.
2. **Salary Module Fix Pending Verification**: Fix applied to prevent future dates from being counted as absent - awaiting user verification.

---

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn/UI
- **Backend**: FastAPI, Python
- **Database**: MongoDB (motor async driver)
- **PDF Processing**: pdfplumber, PyPDF2, pytesseract (OCR)
- **Excel**: openpyxl
