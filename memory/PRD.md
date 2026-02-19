# AGM SALES - Salary Calculator Application

## Original Problem Statement
Build a complete Salary Calculator web application for a garment manufacturing company (AGM Sales) that processes monthly attendance machine data, allows configurable salary rules, manages employee master data, and generates downloadable salary reports in Excel format.

## Architecture
- **Frontend**: React with shadcn/ui components, React Router, localStorage persistence
- **Data Storage**: Client-side localStorage (no backend needed)
- **Excel Processing**: SheetJS (xlsx) library for reading/writing Excel files
- **PDF Generation**: jsPDF with autoTable plugin
- **UI**: Tailwind CSS with custom dark/light themes

## User Personas
1. **HR/Payroll Staff**: Process monthly salaries, configure rules, download reports
2. **Office Administrators**: Manage employee master data, import/export Excel files

## Core Requirements
### Static Features
1. Employee Master Management (CRUD)
2. Attendance Upload from biometric machine (10-row-per-employee format)
3. Salary Configuration (10+ rules: OT, half-day, sandwich, short hours, etc.)
4. Salary Report with drill-down
5. Excel/PDF export
6. English/Hindi language toggle
7. Dark/Light mode

## Salary Calculation Formula (UPDATED Feb 19, 2026)

### Key Formula:
```
Total Salary = (Monthly Salary / Days in Month) × Total Payable Days

Total Payable Days = Present Days + Sunday Working Days + OT Days
```

### Calculation Rules:
1. **Present Days**: Count of weekdays employee came to work
2. **Sunday Working Days**: Count of Sundays employee came and worked 8+ hours (or within 15 min tolerance)
3. **OT Hours**: Hours worked beyond standard (9 hrs weekday, 8 hrs Sunday)
4. **Short Hours**: Hours short of standard (only if > 15 min short)
5. **Net OT Hours**: OT Hours - Short Hours
6. **OT Days**: Net OT Hours ÷ 9 (configurable)

### Tolerance Rule:
- If employee is 15-20 minutes short, still count as 1 full day
- Only deduct short hours if > 15 minutes short

### "Only Sunday, No OT" Option:
- Per-employee setting
- When enabled: Employee gets Sunday working pay but no OT pay

## What's Been Implemented

### Feb 16, 2026 - Initial MVP
- Employee Master CRUD with Excel import/export
- Attendance Upload with 10-row format parsing
- Salary Configuration with all rules
- Salary Reports with Excel/PDF download

### Feb 16, 2026 - Feature Update
**1. Sunday Working** ✅
- Sunday worked shown separately in dedicated column
- Counts as extra working day with separate pay

**2. Short Hours Deduction (Section 3L)** ✅
- Tracks hours worked below 9hr standard
- Daily short hours summed up
- Conversion: 9 short hours = 1 day deduction (configurable)

**3. Manual Attendance Edit** ✅
- Search employees in attendance preview
- Edit button on each employee row
- Modal to edit IN/OUT times and work hours for any day

### Feb 19, 2026 - Salary Formula Simplification ✅
**1. Simplified Calculation Logic**
- All calculations now derived ONLY from IN/OUT times
- Removed dependency on attendance sheet's OT, Work Hours, Status columns
- Formula: `Salary = (Monthly Salary / Days in Month) × Total Payable Days`
- Where: `Total Payable Days = Present Days + Sunday Working Days + OT Days`

**2. "Only Sunday Pay, No OT" Option** ✅
- Added per-employee setting in Employee Master
- Toggle in Add/Edit Employee modal
- "No OT" badge displayed for applicable employees
- When enabled: Employee gets Sunday working pay but no overtime

**3. Short Hours Tolerance** ✅
- New configurable tolerance (default: 15 minutes)
- If employee is within tolerance of standard hours, count as full day
- Only track short hours if > tolerance minutes short

**4. Updated Configuration UI**
- Removed obsolete "Use OT from Attendance Sheet" toggle
- Added Short Hours Tolerance (mins) input
- Updated formula explanations in Hindi

**5. Updated Salary Report**
- New columns: Net OT, OT Days, Total Payable Days
- Employee detail modal shows complete formula breakdown
- Calculation transparency for HR verification

**6. localStorage Persistence Fix** ✅
- Fixed race condition causing data loss on navigation
- Used lazy initialization from localStorage
- Added isInitialLoadComplete ref to prevent overwrites

## Updated UI Elements
- Summary Dashboard: 5 cards (Employees, Salary, OT, Short Ded., Zero Salary)
- Salary Table: OT Hrs, Short Hrs, Net OT, OT Days, Payable Days, Total columns
- Employee Detail Modal: Complete formula breakdown with values
- Excel/PDF exports include all salary components

## Key Files Reference
- `/app/frontend/src/utils/salaryCalculator.js` - Core calculation engine
- `/app/frontend/src/pages/EmployeeMaster.jsx` - Employee CRUD with onlySundayNoOT
- `/app/frontend/src/pages/SalaryConfiguration.jsx` - Config UI
- `/app/frontend/src/pages/SalaryReport.jsx` - Report with new columns
- `/app/frontend/src/context/AppContext.js` - State management & persistence
- `/app/frontend/src/utils/constants.js` - Default config & translations

## Prioritized Backlog

### P0 (Must Have) - COMPLETED ✅
- All core features implemented and tested
- Salary formula simplified as per user requirement
- "Only Sunday, No OT" option added
- localStorage persistence fixed

### P1 (Should Have) - Future
- [ ] Support CSV import/export
- [ ] Print-friendly report view
- [ ] Data backup/restore functionality
- [ ] Individual salary slip PDF download (implemented but untested)

### P2 (Nice to Have) - Future
- [ ] Charts/graphs in dashboard
- [ ] Attendance trend analysis
- [ ] Employee-wise salary history
- [ ] Multi-month comparison

## Testing Reports
- `/app/test_reports/iteration_1.json`
- `/app/test_reports/iteration_2.json`
- `/app/test_reports/iteration_3.json` (Latest - Feb 19, 2026)

## Next Tasks
1. Test with real biometric attendance Excel files
2. Validate salary calculations against actual payroll
3. User acceptance testing
