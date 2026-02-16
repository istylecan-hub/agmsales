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
- Example shown in config: 5 days × 2 hours short = 10 hours = 1.11 day deduction

**3. Manual Attendance Edit** ✅
- Search employees in attendance preview
- Edit button on each employee row
- Modal to edit IN/OUT times and work hours for any day
- Changes saved to localStorage

### Updated UI Elements
- Summary Dashboard: 5 cards (Employees, Salary, OT, Short Ded., Zero Salary)
- Salary Table: Added Short Hrs and Short Ded. columns
- Employee Detail Modal: Short Hours shown in summary, Short (min) column in breakdown
- Excel/PDF exports include short hours data

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
1. Test with real biometric attendance Excel files
2. Add data validation for edge cases
3. Add print CSS for reports
