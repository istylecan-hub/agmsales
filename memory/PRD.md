# AGM SALES - Multi-Module Business Application

## Original Problem Statement
Build a complete business application for AGM Sales garment manufacturing company with two core modules:
1. **Salary Calculator**: Process monthly attendance data and calculate salaries
2. **Invoice Extractor**: Extract structured data from PDF invoices (Amazon, Meesho, Fashnear)

## Architecture
```
/app/
├── backend/
│   ├── server.py              # Main FastAPI server
│   ├── invoice_extractor.py   # Invoice extraction module
│   ├── uploads/               # PDF storage
│   └── exports/               # Generated CSV/Excel files
│
└── frontend/
    └── src/
        ├── pages/
        │   ├── Dashboard.jsx
        │   ├── EmployeeMaster.jsx
        │   ├── AttendanceUpload.jsx
        │   ├── SalaryConfiguration.jsx
        │   ├── SalaryReport.jsx
        │   └── InvoiceExtractor.jsx  # NEW
        ├── components/
        │   └── Layout.jsx
        ├── context/
        │   └── AppContext.js
        └── utils/
            ├── salaryCalculator.js
            ├── excelParser.js
            └── exportUtils.js
```

## Tech Stack
| Layer | Technology |
|-------|------------|
| Frontend | React 19 + Tailwind CSS + Shadcn/UI |
| Backend | FastAPI (Python) |
| Database | MongoDB (Atlas for production) |
| AI | OpenAI GPT-5.2 (via Emergent LLM Key) |
| PDF Processing | PyPDF2 + pytesseract (OCR) |
| Excel | SheetJS (frontend), openpyxl (backend) |

---

## MODULE 1: Salary Calculator

### Salary Calculation Formula
```
Present Days = Days in Month - Absent Days - Sandwich Days
Total Payable Days = Present Days + Sunday Working Days + OT Days
Total Salary = (Monthly Salary / Days in Month) × Total Payable Days
```

### Features
- ✅ Employee Master (CRUD + Excel Import/Export)
- ✅ Attendance Upload (10-row format)
- ✅ Month/Year Selection
- ✅ Holiday Management
- ✅ Configurable Salary Rules (10+ options)
- ✅ OT Calculation (9 hrs weekday, 8 hrs Sunday)
- ✅ 15 min tolerance rule
- ✅ Sandwich rule for WO/HL
- ✅ "Only Sunday, No OT" per employee option
- ✅ Net OT = OT Hours - Short Hours
- ✅ Excel/PDF Reports
- ✅ Individual Salary Slips

---

## MODULE 2: Invoice Extractor (NEW)

### Features
- ✅ PDF Upload (Drag & Drop, Bulk)
- ✅ AI Extraction (GPT-5.2 via Emergent LLM Key)
- ✅ Regex Fallback (No credits mode)
- ✅ OCR for Scanned PDFs
- ✅ Supports: Amazon, Meesho, Fashnear invoices
- ✅ Extracts: Invoice #, Date, GSTIN, Line Items, HSN Codes, Tax
- ✅ View by Service Provider
- ✅ CSV & Excel Export (5 sheets)

### API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/invoice/upload` | Upload PDF files |
| POST | `/api/invoice/extract/{job_id}` | Start extraction |
| GET | `/api/invoice/job/{job_id}` | Get job status |
| GET | `/api/invoice/export/csv/{job_id}` | Download CSV |
| GET | `/api/invoice/export/excel/{job_id}` | Download Excel |
| DELETE | `/api/invoice/job/{job_id}` | Delete job |

---

## Deployment
- **Live URL**: https://salary.agmsales.live
- **Cost**: 50 credits/month
- **Database**: MongoDB Atlas

---

## Completed Work (Feb 19, 2026)

### Session 1: Salary Calculator MVP
- Employee Management with Excel import/export
- Attendance processing (10-row format)
- Salary configuration (10+ rules)
- Reports with Excel/PDF download

### Session 2: Salary Logic Refinement
- Sunday working as separate count
- Short hours deduction
- Manual attendance edit
- Holiday management

### Session 3: Integration & Deployment
- Simplified salary formula (Present Days = Month - Absent - Sandwich)
- "Only Sunday, No OT" option per employee
- 15 min tolerance rule
- Month/Year selector for attendance
- localStorage persistence fix
- **Invoice Extractor module integrated**
- Deployed to production

---

## Backlog

### P1 (Should Have)
- [ ] Test Invoice Extractor with real invoices
- [ ] Test Salary Calculator with real attendance data
- [ ] Print-friendly report view

### P2 (Nice to Have)
- [ ] Dashboard charts/graphs
- [ ] Multi-month salary comparison
- [ ] Invoice history management
- [ ] Batch salary slip download

---

## Key Files
- `/app/backend/server.py` - Main backend
- `/app/backend/invoice_extractor.py` - Invoice extraction module
- `/app/frontend/src/pages/InvoiceExtractor.jsx` - Invoice UI
- `/app/frontend/src/utils/salaryCalculator.js` - Salary logic
- `/app/frontend/src/pages/SalaryConfiguration.jsx` - Config UI

## Test Reports
- `/app/test_reports/iteration_3.json` (Latest)
