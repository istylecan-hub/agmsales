// Salary calculation engine for AGM Sales
// All calculations based ONLY on IN/OUT times from attendance sheet
// Formula: Salary = (Monthly Salary / Days in Month) × Total Payable Days
// Total Payable Days = Present Days + Sunday Working Days + OT Days

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
 * LOGIC (as per user's requirement):
 * 
 * 1. Monthly Salary Calculation:
 *    - Salary = (Monthly Salary / Days in Month) × Total Payable Days
 *    - Example: Feb has 28 days, salary 10000, worked 10 days = 10000/28*10
 * 
 * 2. Present Days:
 *    - Count all days employee came (excluding Sundays)
 *    - If employee works 8 hours (or 15-20 min short) = 1 day
 *    - If more than 15 min short = track in short hours
 * 
 * 3. Sunday Working:
 *    - Sunday is weekly off
 *    - If employee comes and works 8 hours = 1 Sunday Working Day
 *    - If 15-20 min short, still count as 1 day
 *    - Extra hours beyond 8 = OT (unless onlySundayNoOT is enabled)
 * 
 * 4. OT Hours:
 *    - Weekday: Hours worked beyond 9 hours
 *    - Sunday: Hours worked beyond 8 hours
 * 
 * 5. Short Hours:
 *    - Only if more than 15 minutes short
 *    - Net OT = OT Hours - Short Hours
 * 
 * 6. OT Days:
 *    - OT Days = Net OT Hours / 9 (conversion base)
 * 
 * 7. Total Payable Days = Present Days + Sunday Working Days + OT Days
 * 
 * 8. Total Salary = (Monthly Salary / Days in Month) × Total Payable Days
 */
const calculateEmployeeSalary = (attEmp, masterEmp, config, daysInMonth, manualHolidays = []) => {
  const dailyBreakdown = [];
  let presentDays = 0;
  let sundayWorkedDays = 0;
  let holidayWorkedDays = 0;
  let rawWODays = 0; // Sundays where employee didn't come
  let rawHLDays = 0; // Holidays where employee didn't come
  let absentDays = 0;
  let totalOTMinutes = 0;
  let totalCameDays = 0;
  let halfDayCount = 0;
  let totalShortMinutes = 0;
  
  const classifications = [];
  
  // Config values
  const weekdayStandardMins = (config.weekdayStandardHours || 9) * 60; // 9 hours = 540 mins
  const sundayStandardMins = (config.sundayStandardHours || 8) * 60; // 8 hours = 480 mins
  const weekdayHalfDayMins = (config.weekdayHalfDayThreshold || 4.5) * 60;
  const shortHoursTolerance = (config.shortHoursTolerance || 15); // 15 min tolerance
  
  // Check if this employee has "Only Sunday, No OT" setting
  const onlySundayNoOT = masterEmp.onlySundayNoOT === true;
  
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
        
        if (hasOut && workMins > 0) {
          // Calculate how short from 8 hours
          const shortFromStandard = sundayStandardMins - workMins;
          
          if (shortFromStandard <= shortHoursTolerance) {
            // Within 15 min tolerance OR worked 8+ hours = 1 full day
            dayValue = 1;
            
            // Calculate OT (only if NOT onlySundayNoOT and extra hours beyond 8)
            if (config.enableOvertime && !onlySundayNoOT && workMins > sundayStandardMins) {
              otMinutes = workMins - sundayStandardMins;
            }
          } else if (workMins >= weekdayHalfDayMins) {
            // Worked at least 4.5 hours but less than 7.75 hours = still 1 day (as per user requirement)
            // User said: if 15-20 min short, still count as 1 day
            // This means minor shortage should still be 1 day
            dayValue = 1;
            
            // Track short minutes (only if more than tolerance)
            if (config.enableShortHoursDeduction && shortFromStandard > shortHoursTolerance) {
              shortMinutes = shortFromStandard;
            }
          } else if (workMins > 0) {
            // Very less work - half day
            dayValue = 0.5;
            isHalfDay = true;
            halfDayCount++;
          }
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
        
        if (hasOut && workMins > 0) {
          const shortFromStandard = sundayStandardMins - workMins;
          
          if (shortFromStandard <= shortHoursTolerance) {
            dayValue = 1;
            if (config.enableOvertime && !onlySundayNoOT && workMins > sundayStandardMins) {
              otMinutes = workMins - sundayStandardMins;
            }
          } else if (workMins >= weekdayHalfDayMins) {
            dayValue = 1;
            if (config.enableShortHoursDeduction && shortFromStandard > shortHoursTolerance) {
              shortMinutes = shortFromStandard;
            }
          } else if (workMins > 0) {
            dayValue = 0.5;
            isHalfDay = true;
            halfDayCount++;
          }
        } else if (!hasOut) {
          dayValue = 1;
        }
        
        holidayWorkedDays += dayValue;
        
      } else {
        // REGULAR WEEKDAY
        classification = DAY_CLASSIFICATIONS.PRESENT;
        
        if (hasOut && workMins > 0) {
          // Calculate how short from 9 hours
          const shortFromStandard = weekdayStandardMins - workMins;
          
          if (shortFromStandard <= shortHoursTolerance) {
            // Within 15 min tolerance OR worked 9+ hours = 1 full day
            dayValue = 1;
            
            // Calculate OT (only if NOT onlySundayNoOT)
            if (config.enableOvertime && !onlySundayNoOT && workMins > weekdayStandardMins) {
              otMinutes = workMins - weekdayStandardMins;
            }
          } else if (workMins >= weekdayHalfDayMins) {
            // Worked 4.5+ hours but less than 8.75 hours
            dayValue = 1;
            
            // Track short minutes (only if more than tolerance)
            if (config.enableShortHoursDeduction && shortFromStandard > shortHoursTolerance) {
              shortMinutes = shortFromStandard;
            }
          } else if (workMins > 0) {
            // Less than 4.5 hours = half day
            dayValue = 0.5;
            isHalfDay = true;
            halfDayCount++;
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
      netOTHours: 0,
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
      onlySundayNoOT: onlySundayNoOT,
    };
  }
  
  // Apply sandwich rule (if enabled)
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
  
  // Calculate OT Hours
  const otHours = totalOTMinutes / 60;
  
  // Calculate short hours
  const shortHours = totalShortMinutes / 60;
  
  // NET OT = OT Hours - Short Hours (as per user requirement)
  const netOTHours = Math.max(0, otHours - shortHours);
  
  // OT Days = Net OT Hours / 9 (conversion base)
  const otConversionBase = config.otConversionBase || 9;
  const otDays = netOTHours / otConversionBase;
  
  // SALARY CALCULATION (as per user's exact formula)
  // Per Day Salary = Monthly Salary / Days in Month
  const perDaySalary = masterEmp.salary / daysInMonth;
  
  // PRESENT DAYS = Days in Month - Absent Days - Sandwich Days
  // If no absent and no sandwich: Present = full month (e.g., 28 days)
  // Sunday NOT working is NOT absence - it's paid WO (unless sandwiched)
  const presentDaysCalculated = daysInMonth - absentDays - sandwichDays;
  
  // TOTAL PAYABLE DAYS = Present Days + Sunday Working + Holiday Working + OT Days
  // Sunday/Holiday working is EXTRA pay on top of base salary
  const totalPayableDays = presentDaysCalculated + sundayWorkedDays + holidayWorkedDays + otDays;
  
  // Total Salary = Per Day Salary × Total Payable Days
  const totalSalary = perDaySalary * totalPayableDays;
  
  // For display purposes, calculate component breakdowns
  const baseSalary = perDaySalary * presentDays;
  const sundayAmount = perDaySalary * sundayWorkedDays;
  const holidayAmount = perDaySalary * holidayWorkedDays;
  const otAmount = perDaySalary * otDays;
  
  // Short hours tracking (for reference, but deduction is already in net OT)
  const shortDays = shortHours / (config.shortHoursConversionBase || 9);
  
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
    paidDays: Math.round(presentDays * 100) / 100, // For backward compatibility
    absentDays,
    otMinutes: totalOTMinutes,
    otHours: Math.round(otHours * 100) / 100,
    netOTHours: Math.round(netOTHours * 100) / 100,
    otDays: Math.round(otDays * 100) / 100,
    shortMinutes: totalShortMinutes,
    shortHours: Math.round(shortHours * 100) / 100,
    shortDays: Math.round(shortDays * 100) / 100,
    shortDeduction: Math.round(perDaySalary * shortDays), // For reference
    totalPayableDays: Math.round(totalPayableDays * 100) / 100,
    baseSalary: Math.round(baseSalary),
    sundayAmount: Math.round(sundayAmount),
    holidayAmount: Math.round(holidayAmount),
    grossSalary: Math.round(baseSalary + sundayAmount + holidayAmount),
    otAmount: Math.round(otAmount),
    totalSalary: Math.round(totalSalary),
    halfDayCount,
    dailyBreakdown,
    isZeroAttendance: false,
    onlySundayNoOT: onlySundayNoOT,
  };
};

/**
 * Apply extended sandwich rule
 * A WO/HL day is NOT paid if both nearest working days on either side are Absent
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
  const onlySundayNoOTCount = results.filter(r => r.onlySundayNoOT).length;
  
  return {
    totalEmployees,
    totalSalary,
    totalOT,
    totalShortDeduction,
    zeroSalaryCount,
    halfDayCount,
    onlySundayNoOTCount,
  };
};
