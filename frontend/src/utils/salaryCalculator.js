// Salary calculation engine
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
      daysInMonth
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
 */
const calculateEmployeeSalary = (attEmp, masterEmp, config, daysInMonth) => {
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
  let totalShortMinutes = 0; // Track short hours (when worked less than standard)
  
  const classifications = [];
  
  // Process each day
  attEmp.dailyData.forEach((day) => {
    const {
      day: dayNum,
      dayName,
      inTime,
      outTime,
      workHours,
      otTime,
      status,
      isSunday,
      isHoliday,
      hasIn,
      hasOut,
    } = day;
    
    let classification = DAY_CLASSIFICATIONS.ABSENT;
    let dayValue = 0;
    let otMinutes = 0;
    let isHalfDay = false;
    let shortMinutes = 0; // Track short hours for this day
    
    if (hasIn) {
      totalCameDays++;
      
      if (isSunday) {
        // Sunday Worked
        classification = DAY_CLASSIFICATIONS.SUNDAY_WORKED;
        
        if (hasOut) {
          const workMins = calculateWorkMinutes(inTime, outTime);
          const sundayThresholdMins = config.sundayHalfDayThreshold * 60;
          
          if (config.enableHalfDay && workMins < sundayThresholdMins && workMins > 0) {
            dayValue = 0.5;
            isHalfDay = true;
            halfDayCount++;
          } else if (workMins > 0) {
            dayValue = 1;
          }
          
          // Sunday OT
          if (config.enableOvertime) {
            const sundayStandardMins = config.sundayStandardHours * 60;
            const overtimeMins = workMins - sundayStandardMins;
            if (overtimeMins > config.otGraceMinutes) {
              otMinutes = overtimeMins;
            }
          }
        } else {
          // Sunday with IN but no OUT
          if (config.sundayMissingOutPunch === 'full') {
            dayValue = 1;
          } else if (config.sundayMissingOutPunch === 'half') {
            dayValue = 0.5;
            isHalfDay = true;
            halfDayCount++;
          } else {
            dayValue = 0;
          }
        }
        
        sundayWorkedDays += dayValue;
        
      } else if (isHoliday) {
        // Holiday Worked
        classification = DAY_CLASSIFICATIONS.HOLIDAY_WORKED;
        
        if (hasOut) {
          const workMins = calculateWorkMinutes(inTime, outTime);
          const sundayThresholdMins = config.sundayHalfDayThreshold * 60;
          
          if (config.enableHalfDay && workMins < sundayThresholdMins && workMins > 0) {
            dayValue = 0.5;
            isHalfDay = true;
            halfDayCount++;
          } else if (workMins > 0) {
            dayValue = 1;
          }
        } else {
          dayValue = 1; // HL worked but no out punch - count as full
        }
        
        holidayWorkedDays += dayValue;
        
      } else {
        // Regular weekday - PRESENT
        classification = DAY_CLASSIFICATIONS.PRESENT;
        
        // Parse work hours from the workHours column
        let workMins = parseTimeToMinutes(workHours);
        
        if (workMins > 0) {
          const weekdayThresholdMins = config.weekdayHalfDayThreshold * 60;
          const weekdayStandardMins = config.weekdayStandardHours * 60;
          
          if (config.enableHalfDay && workMins < weekdayThresholdMins) {
            dayValue = 0.5;
            isHalfDay = true;
            halfDayCount++;
          } else {
            dayValue = 1;
          }
          
          // Track short hours (when worked less than standard)
          if (config.enableShortHoursDeduction && workMins < weekdayStandardMins && workMins >= weekdayThresholdMins) {
            shortMinutes = weekdayStandardMins - workMins;
          }
          
          // Weekday OT
          if (config.enableOvertime) {
            const overtimeMins = workMins - weekdayStandardMins;
            if (overtimeMins > config.otGraceMinutes) {
              otMinutes = overtimeMins;
            }
          }
        } else {
          // IN exists but no work hours (missing OUT punch)
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
      // No IN time
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
    
    dailyBreakdown.push({
      day: dayNum,
      dayName,
      inTime: inTime || '--:--',
      outTime: outTime || '--:--',
      workHours: workHours || '00:00',
      classification,
      dayValue,
      isHalfDay,
      otMinutes,
      shortMinutes,
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
  
  // Calculate salary
  const perDaySalary = masterEmp.salary / daysInMonth;
  const paidDays = presentDays + effectiveWO + effectiveHL;
  const otHours = totalOTMinutes / 60;
  const otDays = otHours / config.otConversionBase;
  
  const grossSalary = perDaySalary * (paidDays + sundayWorkedDays + holidayWorkedDays);
  const otAmount = perDaySalary * otDays;
  const totalSalary = grossSalary + otAmount;
  
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
 * A WO or HL day is NOT paid if BOTH nearest working days on either side are Absent
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
    
    // Check if we should apply sandwich to this type
    if (current.classification === DAY_CLASSIFICATIONS.WEEK_OFF && !config.applySandwichToWO) continue;
    if (current.classification === DAY_CLASSIFICATIONS.HOLIDAY_OFF && !config.applySandwichToHL) continue;
    
    // Look LEFT - skip consecutive WO/HL, find first P/S/H or A
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
    
    // Look RIGHT - skip consecutive WO/HL, find first P/S/H or A
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
    
    // Sandwich: both sides are absent
    if (leftFound === 'absent' && rightFound === 'absent') {
      if (current.classification === DAY_CLASSIFICATIONS.WEEK_OFF) {
        sandwichWO++;
      } else {
        sandwichHL++;
      }
    }
    
    // Edge case: beginning of month (no left), check only right
    if (leftFound === null && rightFound === 'absent') {
      if (current.classification === DAY_CLASSIFICATIONS.WEEK_OFF) {
        sandwichWO++;
      } else {
        sandwichHL++;
      }
    }
    
    // Edge case: end of month (no right), check only left
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
  const zeroSalaryCount = results.filter(r => r.totalSalary === 0).length;
  const halfDayCount = results.reduce((sum, r) => sum + r.halfDayCount, 0);
  
  return {
    totalEmployees,
    totalSalary,
    totalOT,
    zeroSalaryCount,
    halfDayCount,
  };
};
