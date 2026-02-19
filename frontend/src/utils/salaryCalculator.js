// Salary calculation engine
// Only uses IN/OUT times from attendance sheet
// All calculations (Present, Absent, OT, Short Hours) derived from IN-OUT

import { parseTimeToMinutes, calculateWorkMinutes, hasInTime, normalizeEmpCode } from './excelParser';
import { DAY_CLASSIFICATIONS } from './constants';

/**
 * Calculate salary for all employees based on attendance data and configuration
 */
export const calculateSalaries = (attendanceData, employees, config, daysInMonth) => {
  const results = [];
  const employeeMap = new Map();
  
  // Create a map of employees by normalized code
  employees.forEach(emp => {
    const normalizedCode = normalizeEmpCode(emp.code);
    employeeMap.set(normalizedCode, emp);
  });
  
  // Track unmatched employees
  const unmatchedFromAttendance = [];
  const notInAttendance = new Set(employees.map(e => normalizeEmpCode(e.code)));
  
  attendanceData.employees.forEach((attEmp) => {
    const normalizedCode = normalizeEmpCode(attEmp.code);
    const masterEmployee = employeeMap.get(normalizedCode);
    
    if (!masterEmployee) {
      unmatchedFromAttendance.push({
        code: attEmp.code,
        name: attEmp.name,
      });
      return;
    }
    
    notInAttendance.delete(normalizedCode);
    
    const result = calculateEmployeeSalary(
      attEmp,
      masterEmployee,
      config,
      daysInMonth,
      attendanceData.manualHolidays || []
    );
    
    results.push(result);
  });
  
  return {
    results,
    unmatchedFromAttendance,
    notInAttendance: Array.from(notInAttendance).map(code => {
      const emp = employeeMap.get(code);
      return { code, name: emp?.name || 'Unknown' };
    }),
    summary: calculateSummary(results),
  };
};

/**
 * Calculate salary for a single employee
 * 
 * LOGIC:
 * - Only look at IN and OUT times
 * - Work Hours = OUT - IN (calculate ourselves)
 * - Present = IN time exists
 * - Absent = No IN time (and not Sunday/Holiday)
 * - Weekday OT = Work Hours - 9 hours (when positive)
 * - Sunday: 7.5+ hours = 1 full day, >8 hours extra = OT
 * - Short Hours = 9 - Work Hours (when worked but less than 9)
 */
const calculateEmployeeSalary = (attEmp, masterEmp, config, daysInMonth, manualHolidays = []) => {
  const dailyBreakdown = [];
  let presentDays = 0;
  let sundayWorkedDays = 0;
  let holidayWorkedDays = 0;
  let rawWODays = 0;
  let rawHLDays = 0;
  let absentDays = 0;
  let totalOTMinutes = 0;
  let totalCameDays = 0;
  let halfDayCount = 0;
  let totalShortMinutes = 0;
  
  const classifications = [];
  
  // Config values
  const weekdayStandardMins = (config.weekdayStandardHours || 9) * 60; // 9 hours = 540 mins
  const sundayStandardMins = (config.sundayStandardHours || 8) * 60; // 8 hours = 480 mins
  const sundayMinThreshold = 7.5 * 60; // 7.5 hours = 450 mins for full day
  const weekdayHalfDayMins = (config.weekdayHalfDayThreshold || 4.5) * 60;
  
  // Process each day
  attEmp.dailyData.forEach((day) => {
    const {
      day: dayNum,
      dayName,
      inTime,
      outTime,
      isSunday,
    } = day;
    
    // Check if this day is a manual holiday
    const isManualHoliday = manualHolidays.includes(dayNum);
    const isHoliday = isManualHoliday || day.isHoliday;
    
    // Determine if employee has IN time
    const hasIn = hasInTime(inTime);
    const hasOut = hasInTime(outTime);
    
    let classification = DAY_CLASSIFICATIONS.ABSENT;
    let dayValue = 0;
    let otMinutes = 0;
    let isHalfDay = false;
    let shortMinutes = 0;
    
    // CALCULATE WORK MINUTES FROM IN-OUT (not from sheet's work hours)
    let workMins = 0;
    if (hasIn && hasOut) {
      workMins = calculateWorkMinutes(inTime, outTime);
    }
    
    if (hasIn) {
      totalCameDays++;
      
      if (isSunday) {
        // SUNDAY WORKING
        classification = DAY_CLASSIFICATIONS.SUNDAY_WORKED;
        
        if (workMins >= sundayMinThreshold) {
          // 7.5+ hours = 1 full day
          dayValue = 1;
          
          // Extra hours beyond 8 hours = OT
          if (config.enableOvertime && workMins > sundayStandardMins) {
            otMinutes = workMins - sundayStandardMins;
          }
        } else if (workMins > 0) {
          // Less than 7.5 hours but came
          dayValue = 0.5;
          isHalfDay = true;
          halfDayCount++;
        } else if (!hasOut) {
          // IN but no OUT - use config setting
          if (config.sundayMissingOutPunch === 'full') {
            dayValue = 1;
          } else if (config.sundayMissingOutPunch === 'half') {
            dayValue = 0.5;
            isHalfDay = true;
            halfDayCount++;
          }
        }
        
        sundayWorkedDays += dayValue;
        
      } else if (isHoliday) {
        // HOLIDAY WORKING (treat like Sunday)
        classification = DAY_CLASSIFICATIONS.HOLIDAY_WORKED;
        
        if (workMins >= sundayMinThreshold) {
          dayValue = 1;
          if (config.enableOvertime && workMins > sundayStandardMins) {
            otMinutes = workMins - sundayStandardMins;
          }
        } else if (workMins > 0) {
          dayValue = 0.5;
          isHalfDay = true;
          halfDayCount++;
        } else if (!hasOut) {
          dayValue = 1;
        }
        
        holidayWorkedDays += dayValue;
        
      } else {
        // REGULAR WEEKDAY
        classification = DAY_CLASSIFICATIONS.PRESENT;
        
        if (workMins > 0) {
          // Half day check
          if (config.enableHalfDay && workMins < weekdayHalfDayMins) {
            dayValue = 0.5;
            isHalfDay = true;
            halfDayCount++;
          } else {
            dayValue = 1;
          }
          
          // Short hours deduction (worked but less than 9 hours)
          if (config.enableShortHoursDeduction && workMins < weekdayStandardMins && workMins >= weekdayHalfDayMins) {
            shortMinutes = weekdayStandardMins - workMins;
          }
          
          // WEEKDAY OT: (OUT - IN) - 9 hours (when positive)
          if (config.enableOvertime && workMins > weekdayStandardMins) {
            const graceMins = config.otGraceMinutes || 0;
            const overtimeMins = workMins - weekdayStandardMins;
            if (overtimeMins > graceMins) {
              otMinutes = overtimeMins;
            }
          }
        } else if (!hasOut) {
          // IN exists but no OUT - use config setting
          if (config.weekdayMissingOutPunch === 'full') {
            dayValue = 1;
          } else if (config.weekdayMissingOutPunch === 'half') {
            dayValue = 0.5;
            isHalfDay = true;
            halfDayCount++;
          } else {
            dayValue = 0;
            classification = DAY_CLASSIFICATIONS.ABSENT;
            absentDays++;
          }
        }
        
        if (classification === DAY_CLASSIFICATIONS.PRESENT) {
          presentDays += dayValue;
        }
      }
      
      totalOTMinutes += otMinutes;
      totalShortMinutes += shortMinutes;
      
    } else {
      // No IN time - absent or week off or holiday
      if (isSunday) {
        classification = DAY_CLASSIFICATIONS.WEEK_OFF;
        rawWODays++;
      } else if (isHoliday) {
        classification = DAY_CLASSIFICATIONS.HOLIDAY_OFF;
        rawHLDays++;
      } else {
        classification = DAY_CLASSIFICATIONS.ABSENT;
        absentDays++;
      }
    }
    
    classifications.push({
      day: dayNum,
      classification,
      isAbsent: classification === DAY_CLASSIFICATIONS.ABSENT,
    });
    
    // Convert work minutes to HH:MM format for display
    const workHoursDisplay = workMins > 0 
      ? `${Math.floor(workMins / 60).toString().padStart(2, '0')}:${(workMins % 60).toString().padStart(2, '0')}`
      : '00:00';
    
    dailyBreakdown.push({
      day: dayNum,
      dayName,
      inTime: inTime || '--:--',
      outTime: outTime || '--:--',
      workHours: workHoursDisplay,
      workMins: workMins,
      classification,
      dayValue,
      isHalfDay,
      otMinutes,
      shortMinutes,
      isHoliday: isHoliday,
    });
  });
  
  // Zero attendance rule
  if (config.zeroAttendanceZeroSalary && totalCameDays === 0) {
    return {
      code: masterEmp.code,
      name: masterEmp.name,
      department: masterEmp.department || attEmp.department,
      monthlySalary: masterEmp.salary,
      daysInMonth,
      perDaySalary: 0,
      presentDays: 0,
      sundayWorked: 0,
      holidayWorked: 0,
      rawWO: rawWODays,
      rawHL: rawHLDays,
      effectiveWO: 0,
      effectiveHL: 0,
      sandwichDays: 0,
      paidDays: 0,
      absentDays: daysInMonth,
      otMinutes: 0,
      otHours: 0,
      otDays: 0,
      shortMinutes: 0,
      shortHours: 0,
      shortDays: 0,
      shortDeduction: 0,
      totalPayableDays: 0,
      grossSalary: 0,
      otAmount: 0,
      totalSalary: 0,
      halfDayCount: 0,
      dailyBreakdown,
      isZeroAttendance: true,
    };
  }
  
  // Apply sandwich rule
  let sandwichWO = 0;
  let sandwichHL = 0;
  
  if (config.enableSandwich) {
    const sandwichResult = applySandwichRule(classifications, config);
    sandwichWO = sandwichResult.sandwichWO;
    sandwichHL = sandwichResult.sandwichHL;
  }
  
  const effectiveWO = Math.max(0, rawWODays - sandwichWO);
  const effectiveHL = Math.max(0, rawHLDays - sandwichHL);
  const sandwichDays = sandwichWO + sandwichHL;
  
  // Calculate OT
  const otHours = totalOTMinutes / 60;
  const otDays = otHours / (config.otConversionBase || 9);
  
  // Calculate short hours deduction
  const shortHours = totalShortMinutes / 60;
  const shortDays = config.enableShortHoursDeduction 
    ? shortHours / (config.shortHoursConversionBase || 9) 
    : 0;
  
  // SALARY CALCULATION
  const perDaySalary = masterEmp.salary / daysInMonth;
  const paidDays = presentDays + effectiveWO + effectiveHL;
  
  // Total Payable = Present + Sunday Worked + Holiday Worked + OT Days - Short Days
  const totalPayableDays = presentDays + sundayWorkedDays + holidayWorkedDays + otDays - shortDays;
  
  // Gross salary based on present + effective WO/HL + Sunday/Holiday worked
  const grossSalary = perDaySalary * (paidDays + sundayWorkedDays + holidayWorkedDays);
  
  // OT amount
  const otAmount = perDaySalary * otDays;
  
  // Short deduction
  const shortDeduction = perDaySalary * shortDays;
  
  // TOTAL SALARY = Gross + OT - Short Deduction
  const totalSalary = grossSalary + otAmount - shortDeduction;
  
  return {
    code: masterEmp.code,
    name: masterEmp.name,
    department: masterEmp.department || attEmp.department,
    monthlySalary: masterEmp.salary,
    daysInMonth,
    perDaySalary: Math.round(perDaySalary * 100) / 100,
    presentDays: Math.round(presentDays * 100) / 100,
    sundayWorked: Math.round(sundayWorkedDays * 100) / 100,
    holidayWorked: Math.round(holidayWorkedDays * 100) / 100,
    rawWO: rawWODays,
    rawHL: rawHLDays,
    effectiveWO,
    effectiveHL,
    sandwichDays,
    paidDays: Math.round(paidDays * 100) / 100,
    absentDays,
    otMinutes: totalOTMinutes,
    otHours: Math.round(otHours * 100) / 100,
    otDays: Math.round(otDays * 100) / 100,
    shortMinutes: totalShortMinutes,
    shortHours: Math.round(shortHours * 100) / 100,
    shortDays: Math.round(shortDays * 100) / 100,
    shortDeduction: Math.round(shortDeduction),
    totalPayableDays: Math.round(totalPayableDays * 100) / 100,
    grossSalary: Math.round(grossSalary),
    otAmount: Math.round(otAmount),
    totalSalary: Math.round(totalSalary),
    halfDayCount,
    dailyBreakdown,
    isZeroAttendance: false,
  };
};

/**
 * Apply extended sandwich rule
 */
const applySandwichRule = (classifications, config) => {
  let sandwichWO = 0;
  let sandwichHL = 0;
  
  const isWOorHL = (c) => 
    c.classification === DAY_CLASSIFICATIONS.WEEK_OFF || 
    c.classification === DAY_CLASSIFICATIONS.HOLIDAY_OFF;
  
  const isWorking = (c) => 
    c.classification === DAY_CLASSIFICATIONS.PRESENT ||
    c.classification === DAY_CLASSIFICATIONS.SUNDAY_WORKED ||
    c.classification === DAY_CLASSIFICATIONS.HOLIDAY_WORKED;
  
  const isAbsent = (c) => c.classification === DAY_CLASSIFICATIONS.ABSENT;
  
  for (let i = 0; i < classifications.length; i++) {
    const current = classifications[i];
    
    if (!isWOorHL(current)) continue;
    
    if (current.classification === DAY_CLASSIFICATIONS.WEEK_OFF && !config.applySandwichToWO) continue;
    if (current.classification === DAY_CLASSIFICATIONS.HOLIDAY_OFF && !config.applySandwichToHL) continue;
    
    let leftFound = null;
    for (let j = i - 1; j >= 0; j--) {
      if (isWOorHL(classifications[j])) continue;
      if (isWorking(classifications[j])) {
        leftFound = 'working';
        break;
      }
      if (isAbsent(classifications[j])) {
        leftFound = 'absent';
        break;
      }
    }
    
    let rightFound = null;
    for (let j = i + 1; j < classifications.length; j++) {
      if (isWOorHL(classifications[j])) continue;
      if (isWorking(classifications[j])) {
        rightFound = 'working';
        break;
      }
      if (isAbsent(classifications[j])) {
        rightFound = 'absent';
        break;
      }
    }
    
    if (leftFound === 'absent' && rightFound === 'absent') {
      if (current.classification === DAY_CLASSIFICATIONS.WEEK_OFF) {
        sandwichWO++;
      } else {
        sandwichHL++;
      }
    }
    
    if (leftFound === null && rightFound === 'absent') {
      if (current.classification === DAY_CLASSIFICATIONS.WEEK_OFF) {
        sandwichWO++;
      } else {
        sandwichHL++;
      }
    }
    
    if (rightFound === null && leftFound === 'absent') {
      if (current.classification === DAY_CLASSIFICATIONS.WEEK_OFF) {
        sandwichWO++;
      } else {
        sandwichHL++;
      }
    }
  }
  
  return { sandwichWO, sandwichHL };
};

/**
 * Calculate summary statistics
 */
const calculateSummary = (results) => {
  const totalEmployees = results.length;
  const totalSalary = results.reduce((sum, r) => sum + r.totalSalary, 0);
  const totalOT = results.reduce((sum, r) => sum + r.otAmount, 0);
  const totalShortDeduction = results.reduce((sum, r) => sum + (r.shortDeduction || 0), 0);
  const zeroSalaryCount = results.filter(r => r.totalSalary === 0).length;
  const halfDayCount = results.reduce((sum, r) => sum + r.halfDayCount, 0);
  
  return {
    totalEmployees,
    totalSalary,
    totalOT,
    totalShortDeduction,
    zeroSalaryCount,
    halfDayCount,
  };
};
