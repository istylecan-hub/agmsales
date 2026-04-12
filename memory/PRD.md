# AGM Salary Calculator - Product Requirements

## Original Problem Statement
A Salary Calculator application with:
1. **Salary Calculator Module**: Employee management, attendance processing from Excel, salary calculation with configurable rules, monthly salary history
2. **Advance Payment Management**: Upload advance data via CSV/Excel, filter by Type="Salary", match on Employee Name + Code, use UID for upserts
3. **JWT Authentication**: Username/password login, protected routes, Bearer token on all API calls
4. **Security Hardening**: PostHog disabled, CORS restricted, security headers on all responses

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
- [x] February 28-day fix (was incorrectly using 31 days)

### Advance Payment Management (Complete - UI + Backend)
- [x] CSV/Excel upload with flexible column matching
- [x] Type="Salary" filter
- [x] Employee name + code dual matching
- [x] UID-based upsert for duplicate handling
- [x] Frontend-to-backend employee sync for matching
- [ ] Advance deduction from salary calculation (NOT YET IMPLEMENTED)

### JWT Authentication (Complete - Apr 12, 2026)
- [x] Backend: `/api/auth/login` with JWT token generation (python-jose)
- [x] Backend: `Depends(get_current_user)` on ALL protected routes
- [x] Backend: Token verification endpoint `/api/auth/verify`
- [x] Frontend: Login page with form
- [x] Frontend: AuthContext with token management (sessionStorage)
- [x] Frontend: PrivateRoute wrapper for protected pages
- [x] Frontend: Auth headers on ALL fetch calls (storage.js, SalaryReport.jsx, AdvanceManagement.jsx)
- [x] Frontend: 401 handling with auto-redirect to login
- [x] Frontend: Logout with session cleanup

### Security Hardening (Complete - Apr 12, 2026)
- [x] PostHog session recording disabled (`disable_session_recording: true`, `posthog.opt_out_capturing()`)
- [x] CORS restricted to `accounts.agmsale.com` and `agmone.agmsale.com`
- [x] Security headers middleware: X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, Content-Security-Policy

---

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login, returns JWT
- `GET /api/auth/verify` - Verify token validity
- `POST /api/auth/logout` - Logout (client-side token discard)

### Employees (Protected)
- `GET /api/employees` - List all employees
- `POST /api/employees` - Bulk save/replace employees
- `POST /api/employees/add` - Add single employee
- `PUT /api/employees/{code}` - Update employee
- `DELETE /api/employees/{code}` - Delete employee

### Salary (Protected)
- `POST /api/salary/save` - Save monthly salary (upsert)
- `GET /api/salary/history` - List saved months
- `GET /api/salary/history/{year}/{month}` - Get specific month data
- `PUT /api/salary/history/{year}/{month}/{emp_code}` - Update employee salary
- `DELETE /api/salary/history/{year}/{month}` - Delete month record
- `GET /api/salary/compare/{y1}/{m1}/{y2}/{m2}` - Compare two months
- `GET /api/salary/employee/{code}/growth` - Employee growth history

### Advance (Protected)
- `POST /api/advance/upload` - Upload CSV/Excel
- `GET /api/advance/list` - List all advances
- `GET /api/advance/employee/{code}` - Employee-specific advances
- `DELETE /api/advance/clear` - Clear all advances
- `DELETE /api/advance/{uid}` - Delete specific advance

---

## Architecture

```
/app/
├── backend/
│   ├── server.py          # FastAPI app, CORS, security headers, routes
│   ├── auth.py            # JWT auth module
│   ├── advance_api.py     # Advance CSV upload module
│   └── .env               # APP_USERNAME, APP_PASSWORD, JWT_SECRET_KEY, MONGO_URL, DB_NAME
└── frontend/
    └── src/
        ├── App.js             # Routes with PrivateRoute wrappers
        ├── context/
        │   ├── AuthContext.jsx # Auth state, login/logout, authFetch
        │   └── AppContext.js   # App state (employees, config, attendance)
        ├── utils/
        │   ├── storage.js      # API calls with auth headers
        │   └── salaryCalculator.js
        ├── components/
        │   ├── Layout.jsx      # Navigation + Logout
        │   └── PrivateRoute.jsx
        └── pages/
            ├── Login.jsx
            ├── Dashboard.jsx
            ├── EmployeeMaster.jsx
            ├── AttendanceUpload.jsx
            ├── SalaryConfiguration.jsx
            ├── SalaryReport.jsx
            └── AdvanceManagement.jsx
```

---

## Prioritized Backlog

### P1 - High
- [ ] Advance deduction in salary calculation (`salaryCalculator.js`)
- [ ] Monthly salary save overwrite verification

### P2 - Medium
- [ ] Clean up old unused files (invoice_extractor.py, orderhub/, parsers/, etc.)
- [ ] Full E2E regression test

### P3 - Low
- [ ] Dashboard analytics improvements
- [ ] Better error messages for auth failures

---

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn/UI, sonner (toasts)
- **Backend**: FastAPI, Python, python-jose (JWT)
- **Database**: MongoDB (motor async driver)
- **Auth**: JWT Bearer tokens, sessionStorage
