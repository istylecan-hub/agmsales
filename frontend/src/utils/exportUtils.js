// Export utilities for Excel and PDF generation
import * as XLSX from 'xlsx';
import jsPDF from 'jspdf';
import 'jspdf-autotable';

/**
 * Export salary report to Excel with formatting
 */
export const exportSalaryToExcel = (results, summary) => {
  const data = results.map((r, index) => ({
    'S.No': index + 1,
    'Emp Code': r.code,
    'Name': r.name,
    'Department': r.department || '',
    'Monthly Salary': r.monthlySalary,
    'Days in Month': r.daysInMonth,
    'Per Day Salary': r.perDaySalary,
    'Present Days': r.presentDays,
    'Sunday Worked': r.sundayWorked,
    'Holiday Worked': r.holidayWorked,
    'Effective WO': r.effectiveWO,
    'Effective HL': r.effectiveHL,
    'Sandwich Days': r.sandwichDays,
    'Paid Days': r.paidDays,
    'Absent Days': r.absentDays,
    'OT Hours': r.otHours,
    'OT Days': r.otDays,
    'Gross Salary': r.grossSalary,
    'OT Amount': r.otAmount,
    'Total Salary': r.totalSalary,
  }));
  
  // Add totals row
  data.push({
    'S.No': '',
    'Emp Code': '',
    'Name': 'TOTAL',
    'Department': '',
    'Monthly Salary': results.reduce((s, r) => s + r.monthlySalary, 0),
    'Days in Month': '',
    'Per Day Salary': '',
    'Present Days': results.reduce((s, r) => s + r.presentDays, 0).toFixed(2),
    'Sunday Worked': results.reduce((s, r) => s + r.sundayWorked, 0).toFixed(2),
    'Holiday Worked': results.reduce((s, r) => s + r.holidayWorked, 0).toFixed(2),
    'Effective WO': results.reduce((s, r) => s + r.effectiveWO, 0),
    'Effective HL': results.reduce((s, r) => s + r.effectiveHL, 0),
    'Sandwich Days': results.reduce((s, r) => s + r.sandwichDays, 0),
    'Paid Days': results.reduce((s, r) => s + r.paidDays, 0).toFixed(2),
    'Absent Days': results.reduce((s, r) => s + r.absentDays, 0),
    'OT Hours': results.reduce((s, r) => s + r.otHours, 0).toFixed(2),
    'OT Days': results.reduce((s, r) => s + r.otDays, 0).toFixed(2),
    'Gross Salary': summary.totalSalary - summary.totalOT,
    'OT Amount': summary.totalOT,
    'Total Salary': summary.totalSalary,
  });
  
  const worksheet = XLSX.utils.json_to_sheet(data);
  const workbook = XLSX.utils.book_new();
  
  // Set column widths
  const colWidths = [
    { wch: 5 },  // S.No
    { wch: 10 }, // Emp Code
    { wch: 20 }, // Name
    { wch: 15 }, // Department
    { wch: 12 }, // Monthly Salary
    { wch: 10 }, // Days in Month
    { wch: 12 }, // Per Day
    { wch: 10 }, // Present
    { wch: 12 }, // Sunday Worked
    { wch: 12 }, // Holiday Worked
    { wch: 10 }, // Eff WO
    { wch: 10 }, // Eff HL
    { wch: 12 }, // Sandwich
    { wch: 10 }, // Paid Days
    { wch: 10 }, // Absent
    { wch: 10 }, // OT Hours
    { wch: 10 }, // OT Days
    { wch: 12 }, // Gross
    { wch: 12 }, // OT Amount
    { wch: 12 }, // Total
  ];
  worksheet['!cols'] = colWidths;
  
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Salary Report');
  
  const date = new Date().toISOString().split('T')[0];
  XLSX.writeFile(workbook, `AGM_Salary_Report_${date}.xlsx`);
};

/**
 * Export salary report to PDF
 */
export const exportSalaryToPDF = (results, summary) => {
  const doc = new jsPDF('l', 'mm', 'a4'); // Landscape
  
  // Title
  doc.setFontSize(18);
  doc.setTextColor(47, 84, 150);
  doc.text('AGM SALES - Salary Report', 14, 15);
  
  // Summary
  doc.setFontSize(10);
  doc.setTextColor(0, 0, 0);
  doc.text(`Total Employees: ${summary.totalEmployees}`, 14, 25);
  doc.text(`Total Salary: ₹${summary.totalSalary.toLocaleString('en-IN')}`, 80, 25);
  doc.text(`Total OT: ₹${summary.totalOT.toLocaleString('en-IN')}`, 150, 25);
  doc.text(`Zero Salary: ${summary.zeroSalaryCount}`, 220, 25);
  
  // Table
  const tableData = results.map((r, index) => [
    index + 1,
    r.code,
    r.name,
    r.department || '-',
    `₹${r.monthlySalary.toLocaleString('en-IN')}`,
    r.presentDays,
    r.sundayWorked,
    r.effectiveWO,
    r.effectiveHL,
    r.sandwichDays,
    r.paidDays,
    r.otHours,
    r.otDays,
    `₹${r.grossSalary.toLocaleString('en-IN')}`,
    `₹${r.otAmount.toLocaleString('en-IN')}`,
    `₹${r.totalSalary.toLocaleString('en-IN')}`,
  ]);
  
  // Add totals
  tableData.push([
    '',
    '',
    'TOTAL',
    '',
    '',
    results.reduce((s, r) => s + r.presentDays, 0).toFixed(1),
    results.reduce((s, r) => s + r.sundayWorked, 0).toFixed(1),
    results.reduce((s, r) => s + r.effectiveWO, 0),
    results.reduce((s, r) => s + r.effectiveHL, 0),
    results.reduce((s, r) => s + r.sandwichDays, 0),
    results.reduce((s, r) => s + r.paidDays, 0).toFixed(1),
    results.reduce((s, r) => s + r.otHours, 0).toFixed(1),
    results.reduce((s, r) => s + r.otDays, 0).toFixed(2),
    `₹${(summary.totalSalary - summary.totalOT).toLocaleString('en-IN')}`,
    `₹${summary.totalOT.toLocaleString('en-IN')}`,
    `₹${summary.totalSalary.toLocaleString('en-IN')}`,
  ]);
  
  doc.autoTable({
    startY: 32,
    head: [[
      'S.No', 'Code', 'Name', 'Dept', 'Salary',
      'Present', 'Sun', 'WO', 'HL', 'Sand.',
      'Paid', 'OT Hrs', 'OT Days', 'Gross', 'OT Amt', 'Total'
    ]],
    body: tableData,
    theme: 'grid',
    headStyles: {
      fillColor: [47, 84, 150],
      textColor: [255, 255, 255],
      fontSize: 7,
      fontStyle: 'bold',
    },
    bodyStyles: {
      fontSize: 7,
    },
    alternateRowStyles: {
      fillColor: [240, 248, 255],
    },
    columnStyles: {
      0: { cellWidth: 8 },
      1: { cellWidth: 12 },
      2: { cellWidth: 25 },
      3: { cellWidth: 18 },
      4: { cellWidth: 18, halign: 'right' },
      5: { cellWidth: 12, halign: 'center' },
      6: { cellWidth: 10, halign: 'center' },
      7: { cellWidth: 10, halign: 'center' },
      8: { cellWidth: 10, halign: 'center' },
      9: { cellWidth: 10, halign: 'center' },
      10: { cellWidth: 12, halign: 'center' },
      11: { cellWidth: 12, halign: 'center' },
      12: { cellWidth: 12, halign: 'center' },
      13: { cellWidth: 18, halign: 'right' },
      14: { cellWidth: 16, halign: 'right' },
      15: { cellWidth: 18, halign: 'right' },
    },
    margin: { left: 8, right: 8 },
  });
  
  const date = new Date().toISOString().split('T')[0];
  doc.save(`AGM_Salary_Report_${date}.pdf`);
};

/**
 * Export employee daily breakdown to Excel
 */
export const exportEmployeeBreakdownToExcel = (employee) => {
  const data = employee.dailyBreakdown.map(day => ({
    'Day': day.day,
    'Day Name': day.dayName,
    'IN Time': day.inTime,
    'OUT Time': day.outTime,
    'Work Hours': day.workHours,
    'Classification': day.classification,
    'Day Value': day.dayValue,
    'Half Day': day.isHalfDay ? 'Yes' : 'No',
    'OT Minutes': day.otMinutes,
  }));
  
  const worksheet = XLSX.utils.json_to_sheet(data);
  const workbook = XLSX.utils.book_new();
  
  worksheet['!cols'] = [
    { wch: 6 }, { wch: 10 }, { wch: 10 }, { wch: 10 },
    { wch: 12 }, { wch: 18 }, { wch: 10 }, { wch: 10 }, { wch: 12 }
  ];
  
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Daily Breakdown');
  XLSX.writeFile(workbook, `${employee.name}_Breakdown.xlsx`);
};
