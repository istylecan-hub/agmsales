// Constants and default configuration for Salary Calculator

export const DEFAULT_CONFIG = {
  // 3A. Attendance Detection
  useInOutForAttendance: true,
  
  // 3B. Working Hours Standard
  weekdayStandardHours: 9,
  sundayStandardHours: 8,
  
  // 3C. Overtime Rules
  enableOvertime: true,
  otConversionBase: 9, // Net OT hours divided by this gives OT days
  
  // 3D. Half Day Rule
  enableHalfDay: true,
  weekdayHalfDayThreshold: 4.5, // hours - below this = 0.5 day
  sundayHalfDayThreshold: 4, // hours
  
  // 3E. Sunday Working
  countSundayAsExtraDay: true,
  sundayMissingOutPunch: 'full', // 'full', 'half', 'none'
  
  // 3F. Holiday Rules
  holidayNotWorkedIsPaid: true,
  holidayWorkedIsExtraDay: true,
  
  // 3G. Week Off
  weekOffIsPaid: true,
  
  // 3H. Sandwich Rule
  enableSandwich: true,
  applySandwichToWO: true,
  applySandwichToHL: true,
  
  // 3I. Zero Attendance Rule
  zeroAttendanceZeroSalary: true,
  
  // 3K. Missing Punch Handling
  weekdayMissingOutPunch: 'full', // 'full', 'half', 'absent'
  
  // 3L. Short Hours Deduction
  enableShortHoursDeduction: true,
  shortHoursConversionBase: 9, // short hours divided by this gives deduction days
  shortHoursTolerance: 15, // 15 minutes tolerance - within this = 1 full day
};

export const STORAGE_KEYS = {
  EMPLOYEES: 'agm_employees',
  CONFIG: 'agm_salary_config',
  ATTENDANCE_DATA: 'agm_attendance_data',
  LAST_CALCULATION: 'agm_last_calculation',
};

export const DAY_CLASSIFICATIONS = {
  PRESENT: 'PRESENT',
  ABSENT: 'ABSENT',
  SUNDAY_WORKED: 'SUNDAY_WORKED',
  HOLIDAY_WORKED: 'HOLIDAY_WORKED',
  WEEK_OFF: 'WO',
  HOLIDAY_OFF: 'HL_OFF',
  HALF_DAY: 'HALF_DAY',
};

export const STATUS_COLORS = {
  paid: '#22C55E',
  absent: '#EF4444',
  holiday: '#3B82F6',
  overtime: '#F97316',
  neutral: '#64748B',
};

// Hindi translations
export const TRANSLATIONS = {
  en: {
    appName: 'AGM SALES',
    subtitle: 'Salary Calculator',
    dashboard: 'Dashboard',
    employees: 'Employees',
    attendance: 'Attendance',
    configuration: 'Configuration',
    reports: 'Reports',
    invoiceExtractor: 'Invoice Extractor',
    addEmployee: 'Add Employee',
    importExcel: 'Import Excel',
    exportExcel: 'Export Excel',
    calculate: 'Calculate Salary',
    download: 'Download',
    search: 'Search...',
    employeeCode: 'Employee Code',
    employeeName: 'Employee Name',
    department: 'Department',
    monthlySalary: 'Monthly Salary',
    dateOfJoining: 'Date of Joining',
    status: 'Status',
    active: 'Active',
    inactive: 'Inactive',
    actions: 'Actions',
    edit: 'Edit',
    delete: 'Delete',
    save: 'Save',
    cancel: 'Cancel',
    confirm: 'Confirm',
    uploadFile: 'Upload File',
    dragDrop: 'Drag and drop your file here, or click to select',
    proceed: 'Proceed',
    totalEmployees: 'Total Employees',
    totalSalary: 'Total Salary',
    totalOT: 'Total OT',
    zeroSalary: 'Zero Salary',
    presentDays: 'Present Days',
    absentDays: 'Absent Days',
    paidDays: 'Paid Days',
    overtimeHours: 'OT Hours',
    overtimeDays: 'OT Days',
    grossSalary: 'Gross Salary',
    otAmount: 'OT Amount',
    totalSalaryPayable: 'Total Salary',
    perDaySalary: 'Per Day',
    daysInMonth: 'Days in Month',
    sundayWorked: 'Sunday Worked',
    holidayWorked: 'Holiday Worked',
    effectiveWO: 'Effective WO',
    effectiveHL: 'Effective HL',
    sandwichDays: 'Sandwich Days',
    downloadExcel: 'Download Excel',
    downloadPDF: 'Download PDF',
  },
  hi: {
    appName: 'AGM SALES',
    subtitle: 'वेतन कैलकुलेटर',
    dashboard: 'डैशबोर्ड',
    employees: 'कर्मचारी',
    attendance: 'उपस्थिति',
    configuration: 'कॉन्फ़िगरेशन',
    reports: 'रिपोर्ट',
    invoiceExtractor: 'इनवॉइस एक्सट्रैक्टर',
    addEmployee: 'कर्मचारी जोड़ें',
    importExcel: 'Excel आयात करें',
    exportExcel: 'Excel निर्यात करें',
    calculate: 'वेतन गणना करें',
    download: 'डाउनलोड',
    search: 'खोजें...',
    employeeCode: 'कर्मचारी कोड',
    employeeName: 'कर्मचारी नाम',
    department: 'विभाग',
    monthlySalary: 'मासिक वेतन',
    dateOfJoining: 'शामिल होने की तारीख',
    status: 'स्थिति',
    active: 'सक्रिय',
    inactive: 'निष्क्रिय',
    actions: 'क्रियाएं',
    edit: 'संपादित करें',
    delete: 'हटाएं',
    save: 'सेव करें',
    cancel: 'रद्द करें',
    confirm: 'पुष्टि करें',
    uploadFile: 'फाइल अपलोड करें',
    dragDrop: 'फाइल यहां ड्रैग करें या क्लिक करके चुनें',
    proceed: 'आगे बढ़ें',
    totalEmployees: 'कुल कर्मचारी',
    totalSalary: 'कुल वेतन',
    totalOT: 'कुल OT',
    zeroSalary: 'शून्य वेतन',
    presentDays: 'उपस्थित दिन',
    absentDays: 'अनुपस्थित दिन',
    paidDays: 'भुगतान दिन',
    overtimeHours: 'OT घंटे',
    overtimeDays: 'OT दिन',
    grossSalary: 'सकल वेतन',
    otAmount: 'OT राशि',
    totalSalaryPayable: 'कुल वेतन',
    perDaySalary: 'प्रति दिन',
    daysInMonth: 'महीने में दिन',
    sundayWorked: 'रविवार काम',
    holidayWorked: 'छुट्टी काम',
    effectiveWO: 'प्रभावी WO',
    effectiveHL: 'प्रभावी HL',
    sandwichDays: 'सैंडविच दिन',
    downloadExcel: 'Excel डाउनलोड',
    downloadPDF: 'PDF डाउनलोड',
  },
};
