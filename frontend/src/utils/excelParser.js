// Excel parsing logic for attendance files
import * as XLSX from 'xlsx';

/**
 * Parse time string (HH:MM) to minutes
 */
export const parseTimeToMinutes = (timeStr) => {
  if (!timeStr || timeStr === '--:--' || timeStr === '' || timeStr === '00:00') {
    return 0;
  }
  const parts = String(timeStr).split(':');
  if (parts.length !== 2) return 0;
  const hours = parseInt(parts[0], 10) || 0;
  const mins = parseInt(parts[1], 10) || 0;
  return hours * 60 + mins;
};

/**
 * Calculate minutes between two time strings
 */
export const calculateWorkMinutes = (inTime, outTime) => {
  const inMins = parseTimeToMinutes(inTime);
  const outMins = parseTimeToMinutes(outTime);
  if (inMins === 0 || outMins === 0) return 0;
  return outMins > inMins ? outMins - inMins : 0;
};

/**
 * Normalize employee code - strip leading zeros and convert to integer for matching
 */
export const normalizeEmpCode = (code) => {
  if (code === null || code === undefined) return null;
  const strCode = String(code).trim();
  const numCode = parseInt(strCode, 10);
  return isNaN(numCode) ? strCode : numCode;
};

/**
 * Check if a time value indicates presence
 */
export const hasInTime = (timeStr) => {
  return timeStr && timeStr !== '--:--' && timeStr !== '' && String(timeStr).trim() !== '';
};

/**
 * Parse the 10-row-per-employee attendance Excel format
 */
export const parseAttendanceExcel = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: 'array' });
        const sheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[sheetName];
        
        // Convert to array of arrays
        const rawData = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '' });
        
        const employees = [];
        let currentRow = 0;
        let daysInMonth = 0;
        
        while (currentRow < rawData.length) {
          // Find employee block - look for "Empcode" in column A of row 1
          const row0 = rawData[currentRow] || [];
          const row1 = rawData[currentRow + 1] || [];
          
          // Check if this is a valid employee block
          // Row 0: Department header (Col A = "Dept. Name", Col C = department name)
          // Row 1: Employee info (Col A = "Empcode", Col C = employee code, Col H = name)
          if (row0[0] && String(row0[0]).toLowerCase().includes('dept')) {
            const department = row0[2] || '';
            
            if (row1[0] && String(row1[0]).toLowerCase().includes('empcode')) {
              const empCode = normalizeEmpCode(row1[2]);
              const empName = row1[7] || ''; // Column H (index 7)
              
              // Parse dates from row 2
              const row2 = rawData[currentRow + 2] || []; // Date numbers
              const row3 = rawData[currentRow + 3] || []; // Day names
              const row4 = rawData[currentRow + 4] || []; // IN times
              const row5 = rawData[currentRow + 5] || []; // OUT times
              const row6 = rawData[currentRow + 6] || []; // Work hours
              const row7 = rawData[currentRow + 7] || []; // Break time
              const row8 = rawData[currentRow + 8] || []; // OT time
              const row9 = rawData[currentRow + 9] || []; // Status
              
              // Detect days in month from row 2 (dates 1, 2, 3, ... 28/29/30/31)
              let maxDay = 0;
              for (let col = 1; col <= 32; col++) {
                const dayNum = parseInt(row2[col], 10);
                if (dayNum && dayNum > 0 && dayNum <= 31) {
                  maxDay = Math.max(maxDay, dayNum);
                }
              }
              if (maxDay > daysInMonth) daysInMonth = maxDay;
              
              // Parse daily attendance data
              const dailyData = [];
              for (let col = 1; col <= maxDay; col++) {
                const dayNum = parseInt(row2[col], 10) || col;
                const dayName = String(row3[col] || '').trim();
                const inTime = String(row4[col] || '').trim();
                const outTime = String(row5[col] || '').trim();
                const workHours = String(row6[col] || '').trim();
                const breakTime = String(row7[col] || '').trim();
                const otTime = String(row8[col] || '').trim();
                const status = String(row9[col] || '').trim().toUpperCase();
                
                dailyData.push({
                  day: dayNum,
                  dayName: dayName,
                  inTime: inTime,
                  outTime: outTime,
                  workHours: workHours,
                  breakTime: breakTime,
                  otTime: otTime,
                  status: status,
                  isSunday: dayName.toLowerCase().startsWith('sun'),
                  isHoliday: status === 'HL',
                  hasIn: hasInTime(inTime),
                  hasOut: hasInTime(outTime),
                });
              }
              
              employees.push({
                code: empCode,
                name: empName,
                department: department,
                dailyData: dailyData,
              });
              
              currentRow += 10; // Move to next employee block
            } else {
              currentRow++;
            }
          } else {
            currentRow++;
          }
        }
        
        resolve({
          employees,
          daysInMonth,
          totalEmployees: employees.length,
        });
      } catch (error) {
        reject(new Error(`Failed to parse Excel file: ${error.message}`));
      }
    };
    
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsArrayBuffer(file);
  });
};

/**
 * Parse employee master Excel file
 * Expected columns: Empcode, Name, Salary (and optionally Department, DateOfJoining)
 */
export const parseEmployeeMasterExcel = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: 'array' });
        const sheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[sheetName];
        
        // Convert to JSON with headers
        const rawData = XLSX.utils.sheet_to_json(worksheet, { defval: '' });
        
        const employees = rawData.map((row, index) => {
          // Try different possible column names
          const code = normalizeEmpCode(
            row.Empcode || row.empcode || row.Code || row.code || 
            row['Employee Code'] || row['Emp Code'] || row.EmpCode || ''
          );
          
          const name = row.Name || row.name || row['Employee Name'] || 
            row.EmployeeName || row['Emp Name'] || '';
          
          const salary = parseFloat(
            row.Salary || row.salary || row['Monthly Salary'] || 
            row.MonthlySalary || row['Basic Salary'] || 0
          );
          
          const department = row.Department || row.department || row.Dept || '';
          
          const dateOfJoining = row.DateOfJoining || row['Date of Joining'] || 
            row.DOJ || row.doj || '';
          
          return {
            code: code,
            name: String(name).trim(),
            salary: salary,
            department: String(department).trim(),
            dateOfJoining: dateOfJoining ? String(dateOfJoining) : '',
            status: 'active',
          };
        }).filter(emp => emp.code !== null && emp.code !== '');
        
        resolve(employees);
      } catch (error) {
        reject(new Error(`Failed to parse employee Excel: ${error.message}`));
      }
    };
    
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsArrayBuffer(file);
  });
};

/**
 * Export employees to Excel
 */
export const exportEmployeesToExcel = (employees) => {
  const data = employees.map((emp, index) => ({
    'S.No': index + 1,
    'Empcode': emp.code,
    'Name': emp.name,
    'Department': emp.department || '',
    'Monthly Salary': emp.salary,
    'Date of Joining': emp.dateOfJoining || '',
    'Status': emp.status || 'active',
  }));
  
  const worksheet = XLSX.utils.json_to_sheet(data);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Employee Master');
  
  // Auto-fit columns
  const colWidths = [
    { wch: 6 }, { wch: 10 }, { wch: 25 }, { wch: 15 }, 
    { wch: 15 }, { wch: 15 }, { wch: 10 }
  ];
  worksheet['!cols'] = colWidths;
  
  XLSX.writeFile(workbook, 'Employee_Master.xlsx');
};
