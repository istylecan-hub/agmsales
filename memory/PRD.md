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
3. Salary Configuration (10+ rules: OT, half-day, sandwich, etc.)
4. Salary Report with drill-down
5. Excel/PDF export
6. English/Hindi language toggle
7. Dark/Light mode

## What's Been Implemented (Feb 16, 2026)

### Section 1: Employee Master ✅
- Add/Edit/Delete employees
- Import from Excel (.xlsx/.xls)
- Export to Excel
- Search and filter by name, code, department
- Status management (Active/Inactive)
- Data persists in localStorage

### Section 2: Attendance Upload ✅
- Drag-and-drop Excel file upload
- Parses 10-row-per-employee biometric format
- Detects days in month, employees
- Shows preview with IN days count
- Warns about unmatched employees (in attendance but not in master)
- Info about missing employees (in master but not in attendance)

### Section 3: Salary Configuration ✅
- 3A. Attendance Detection (IN/OUT time based)
- 3B. Working Hours Standard (weekday/Sunday)
- 3C. Overtime Rules (grace period, conversion)
- 3D. Half Day Rule (thresholds)
- 3E. Sunday Working (extra day, missing punch handling)
- 3F. Holiday Rules (paid HL, HL worked)
- 3H. Sandwich Rule (extended, for WO and HL)
- 3I. Zero Attendance Rule
- 3K. Missing Punch Handling
- Reset to defaults button

### Section 4: Salary Report ✅
- Summary dashboard (total employees, salary, OT, zero salary count)
- Detailed sortable/filterable table
- Employee drill-down modal with daily breakdown
- Download Excel (formatted with headers, colors, totals)
- Download PDF (formatted report)
- Download individual employee breakdown

### UI/UX ✅
- Collapsible sidebar navigation
- Dark/Light mode toggle
- English/Hindi language toggle
- Professional business aesthetic
- Responsive design (desktop-optimized)
- Status color coding (green=paid, red=absent, blue=holiday, orange=OT)
- Toast notifications
- Progress tracking wizard

## Prioritized Backlog

### P0 (Must Have) - COMPLETED ✅
- All core features implemented and tested

### P1 (Should Have) - Future
- [ ] Support CSV import/export
- [ ] Print-friendly report view
- [ ] Data backup/restore functionality

### P2 (Nice to Have) - Future
- [ ] Charts/graphs in dashboard
- [ ] Attendance trend analysis
- [ ] Employee-wise salary history
- [ ] Multi-month comparison

## Next Tasks
1. Test with real attendance Excel files from biometric machines
2. Add data validation for edge cases
3. Add print CSS for reports
4. Consider adding charts to dashboard
