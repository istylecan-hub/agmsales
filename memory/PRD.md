# AGM Salary Calculator - Product Requirements

## Original Problem Statement
A Salary Calculator application with:
1. **Salary Calculator Module**: Employee management, attendance processing from Excel, salary calculation with configurable rules, monthly salary history
2. **Advance Payment Management**: Upload advance data via CSV/Excel, filter by Type="Salary", match on Employee Name + Code, use UID for upserts, **deduct from salary**
3. **JWT Authentication**: Username/password login, protected routes, Bearer token on all API calls
4. **Security Hardening**: PostHog disabled, CORS restricted, security headers, rate limiting, no sensitive data in localStorage

> Invoice Extractor and OrderHub modules have been REMOVED per user request.

## Current Status: Active Development

---

## What's Been Implemented

### Salary Calculator (Complete)
- [x] Employee management (CRUD operations)
- [x] Attendance processing from Excel
- [x] Salary calculation with configurable rules (OT, sandwich, short hours, etc.)
- [x] Monthly salary history (save/view/compare/delete) with upsert logic
- [x] Employee salary growth tracking
- [x] Report generation (Excel, PDF, Salary Slips)
- [x] February 28-day fix

### Advance Payment Management (Complete)
- [x] CSV/Excel upload with flexible column matching
- [x] Type="Salary" filter
- [x] Employee name + code dual matching
- [x] UID-based upsert for duplicate handling
- [x] Frontend-to-backend employee sync for matching
- [x] **Advance deduction from salary calculation** (Apr 12, 2026)
  - `salaryCalculator.js` accepts `advancesMap` parameter
  - Fetches advances for selected month/year before calculation
  - Shows `advanceAmount` and `netSalary` per employee
  - Summary shows `totalAdvance` and `totalNetSalary`
  - SalaryReport table has Advance and Net Pay columns

### JWT Authentication (Complete - Apr 12, 2026)
- [x] Backend: `/api/auth/login` with JWT token generation (python-jose)
- [x] Backend: `Depends(get_current_user)` on ALL protected routes
- [x] Frontend: Login page, AuthContext, PrivateRoute, auth headers on ALL fetch calls
- [x] Frontend: 401 handling with auto-redirect to login

### Security Hardening (Complete - Apr 12, 2026)
- [x] PostHog session recording disabled
- [x] CORS restricted to `accounts.agmsale.com` and `agmone.agmsale.com`
- [x] Security headers middleware (X-Frame-Options, CSP, etc.)
- [x] **Rate limiting** (slowapi): Login 5/min, Salary save 10/min, Employee save 10/min
- [x] **localStorage sensitive data removed**: Only `agm_theme` and `agm_salary_config` kept
  - Employees loaded from MongoDB server on every mount
  - Attendance and calculation data in React state only
  - Old keys (`agm_employees`, `agm_attendance_data`, `agm_last_calculation`) cleaned up on mount

---

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login (rate limited: 5/min)
- `GET /api/auth/verify` - Verify token
- `POST /api/auth/logout` - Logout

### Employees (Protected)
- `GET /api/employees` - List all
- `POST /api/employees` - Bulk save (rate limited: 10/min)
- `POST /api/employees/add` - Add single
- `PUT /api/employees/{code}` - Update
- `DELETE /api/employees/{code}` - Delete

### Salary (Protected)
- `POST /api/salary/save` - Save monthly (rate limited: 10/min, upsert)
- `GET /api/salary/history` - List saved months
- `GET /api/salary/history/{year}/{month}` - Month detail
- `PUT /api/salary/history/{year}/{month}/{emp_code}` - Update employee salary
- `DELETE /api/salary/history/{year}/{month}` - Delete month
- `GET /api/salary/compare/{y1}/{m1}/{y2}/{m2}` - Compare
- `GET /api/salary/employee/{code}/growth` - Growth history

### Advance (Protected)
- `POST /api/advance/upload` - Upload CSV/Excel
- `GET /api/advance/list` - List all (supports ?month=&year= filter)
- `GET /api/advance/employee/{code}` - Employee advances
- `DELETE /api/advance/clear` - Clear all
- `DELETE /api/advance/{uid}` - Delete specific

---

## Architecture

```
/app/
├── backend/
│   ├── server.py          # FastAPI app, CORS, security headers, rate limiting, routes
│   ├── auth.py            # JWT auth + rate-limited login
│   ├── advance_api.py     # Advance CSV upload
│   ├── rate_limit.py      # Shared slowapi Limiter instance
│   └── .env               # APP_USERNAME, APP_PASSWORD, JWT_SECRET_KEY, MONGO_URL, DB_NAME
└── frontend/
    └── src/
        ├── App.js
        ├── context/
        │   ├── AuthContext.jsx   # Auth state, login/logout
        │   └── AppContext.js     # App state, NO localStorage for sensitive data
        ├── utils/
        │   ├── storage.js        # Server-only sync, no localStorage for employees/attendance/calc
        │   └── salaryCalculator.js  # Advance deduction support
        ├── components/
        │   ├── Layout.jsx
        │   └── PrivateRoute.jsx
        └── pages/
            ├── Login.jsx
            ├── Dashboard.jsx
            ├── EmployeeMaster.jsx
            ├── AttendanceUpload.jsx
            ├── SalaryConfiguration.jsx  # Fetches advances before calculation
            ├── SalaryReport.jsx         # Shows Advance + Net Pay columns
            └── AdvanceManagement.jsx
```

---

## Prioritized Backlog

### P1 - High
- [x] ~~Clean up old unused backend files~~ (Apr 12, 2026)
- [ ] Monthly salary save overwrite verification

### P2 - Medium
- [ ] Full E2E regression test with real attendance data
- [ ] Dashboard analytics improvements

### P3 - Low
- [ ] Better error messages for auth failures

---

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn/UI, sonner
- **Backend**: FastAPI, Python, python-jose (JWT), slowapi (rate limiting)
- **Database**: MongoDB (motor async driver)
- **Auth**: JWT Bearer tokens, sessionStorage
