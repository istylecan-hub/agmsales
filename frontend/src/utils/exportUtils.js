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
    'Short Hours': r.shortHours || 0,
    'Short Days': r.shortDays || 0,
    'Gross Salary': r.grossSalary,
    'OT Amount': r.otAmount,
    'Short Deduction': r.shortDeduction || 0,
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
    'Short Hours': results.reduce((s, r) => s + (r.shortHours || 0), 0).toFixed(2),
    'Short Days': results.reduce((s, r) => s + (r.shortDays || 0), 0).toFixed(2),
    'Gross Salary': summary.totalSalary - summary.totalOT + (summary.totalShortDeduction || 0),
    'OT Amount': summary.totalOT,
    'Short Deduction': summary.totalShortDeduction || 0,
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
    { wch: 10 }, // Short Hours
    { wch: 10 }, // Short Days
    { wch: 12 }, // Gross
    { wch: 12 }, // OT Amount
    { wch: 12 }, // Short Deduction
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
  doc.text(`Total Salary: ₹${summary.totalSalary.toLocaleString('en-IN')}`, 70, 25);
  doc.text(`Total OT: ₹${summary.totalOT.toLocaleString('en-IN')}`, 130, 25);
  doc.text(`Short Ded: -₹${(summary.totalShortDeduction || 0).toLocaleString('en-IN')}`, 190, 25);
  doc.text(`Zero Salary: ${summary.zeroSalaryCount}`, 250, 25);
  
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
    r.paidDays,
    r.otHours,
    r.shortHours || 0,
    `₹${r.grossSalary.toLocaleString('en-IN')}`,
    `₹${r.otAmount.toLocaleString('en-IN')}`,
    `-₹${(r.shortDeduction || 0).toLocaleString('en-IN')}`,
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
    results.reduce((s, r) => s + r.paidDays, 0).toFixed(1),
    results.reduce((s, r) => s + r.otHours, 0).toFixed(1),
    results.reduce((s, r) => s + (r.shortHours || 0), 0).toFixed(1),
    `₹${(summary.totalSalary - summary.totalOT + (summary.totalShortDeduction || 0)).toLocaleString('en-IN')}`,
    `₹${summary.totalOT.toLocaleString('en-IN')}`,
    `-₹${(summary.totalShortDeduction || 0).toLocaleString('en-IN')}`,
    `₹${summary.totalSalary.toLocaleString('en-IN')}`,
  ]);
  
  doc.autoTable({
    startY: 32,
    head: [[
      'S.No', 'Code', 'Name', 'Dept', 'Salary',
      'Present', 'Sun', 'WO', 'Paid', 'OT Hrs', 'Short Hrs',
      'Gross', 'OT Amt', 'Short Ded', 'Total'
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
      3: { cellWidth: 15 },
      4: { cellWidth: 18, halign: 'right' },
      5: { cellWidth: 12, halign: 'center' },
      6: { cellWidth: 10, halign: 'center' },
      7: { cellWidth: 10, halign: 'center' },
      8: { cellWidth: 12, halign: 'center' },
      9: { cellWidth: 12, halign: 'center' },
      10: { cellWidth: 12, halign: 'center' },
      11: { cellWidth: 18, halign: 'right' },
      12: { cellWidth: 16, halign: 'right' },
      13: { cellWidth: 16, halign: 'right' },
      14: { cellWidth: 18, halign: 'right' },
    },
    margin: { left: 5, right: 5 },
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
    'Short Minutes': day.shortMinutes || 0,
  }));
  
  const worksheet = XLSX.utils.json_to_sheet(data);
  const workbook = XLSX.utils.book_new();
  
  worksheet['!cols'] = [
    { wch: 6 }, { wch: 10 }, { wch: 10 }, { wch: 10 },
    { wch: 12 }, { wch: 18 }, { wch: 10 }, { wch: 10 }, { wch: 12 }, { wch: 12 }
  ];
  
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Daily Breakdown');
  XLSX.writeFile(workbook, `${employee.name}_Breakdown.xlsx`);
};

/**
 * Generate Salary Slip PDF for individual employee
 */
export const generateSalarySlipPDF = (employee, month = '', year = '') => {
  const doc = new jsPDF('p', 'mm', 'a4'); // Portrait A4
  
  const pageWidth = doc.internal.pageSize.getWidth();
  const margin = 15;
  let yPos = margin;
  
  // Company Header
  doc.setFillColor(47, 84, 150);
  doc.rect(0, 0, pageWidth, 35, 'F');
  
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(22);
  doc.setFont('helvetica', 'bold');
  doc.text('AGM SALES', pageWidth / 2, 15, { align: 'center' });
  
  doc.setFontSize(12);
  doc.setFont('helvetica', 'normal');
  doc.text('SALARY SLIP', pageWidth / 2, 25, { align: 'center' });
  
  if (month || year) {
    doc.setFontSize(10);
    doc.text(`Month: ${month} ${year}`, pageWidth / 2, 32, { align: 'center' });
  }
  
  yPos = 45;
  doc.setTextColor(0, 0, 0);
  
  // Employee Details Box
  doc.setDrawColor(200, 200, 200);
  doc.setFillColor(248, 249, 250);
  doc.roundedRect(margin, yPos, pageWidth - 2 * margin, 35, 3, 3, 'FD');
  
  yPos += 8;
  doc.setFontSize(10);
  doc.setFont('helvetica', 'bold');
  doc.text('Employee Details', margin + 5, yPos);
  
  yPos += 8;
  doc.setFont('helvetica', 'normal');
  doc.text(`Employee Code: ${employee.code}`, margin + 5, yPos);
  doc.text(`Department: ${employee.department || 'N/A'}`, pageWidth / 2, yPos);
  
  yPos += 7;
  doc.text(`Employee Name: ${employee.name}`, margin + 5, yPos);
  doc.text(`Monthly Salary: ₹${employee.monthlySalary.toLocaleString('en-IN')}`, pageWidth / 2, yPos);
  
  yPos += 7;
  doc.text(`Days in Month: ${employee.daysInMonth}`, margin + 5, yPos);
  doc.text(`Per Day: ₹${employee.perDaySalary.toFixed(2)}`, pageWidth / 2, yPos);
  
  yPos += 15;
  
  // Attendance Summary
  doc.setFillColor(248, 249, 250);
  doc.roundedRect(margin, yPos, pageWidth - 2 * margin, 45, 3, 3, 'FD');
  
  yPos += 8;
  doc.setFont('helvetica', 'bold');
  doc.text('Attendance Summary', margin + 5, yPos);
  
  yPos += 10;
  doc.setFont('helvetica', 'normal');
  
  // Row 1
  doc.text(`Present Days: ${employee.presentDays}`, margin + 5, yPos);
  doc.text(`Sunday Worked: ${employee.sundayWorked}`, margin + 60, yPos);
  doc.text(`Holiday Worked: ${employee.holidayWorked}`, margin + 115, yPos);
  
  yPos += 7;
  // Row 2
  doc.text(`Week Off (WO): ${employee.effectiveWO}`, margin + 5, yPos);
  doc.text(`Holidays (HL): ${employee.effectiveHL}`, margin + 60, yPos);
  doc.text(`Absent Days: ${employee.absentDays}`, margin + 115, yPos);
  
  yPos += 7;
  // Row 3
  doc.text(`OT Hours: ${employee.otHours}`, margin + 5, yPos);
  doc.text(`OT Days: ${employee.otDays}`, margin + 60, yPos);
  doc.text(`Sandwich Deducted: ${employee.sandwichDays}`, margin + 115, yPos);
  
  yPos += 7;
  // Row 4 - Short hours
  doc.text(`Short Hours: ${employee.shortHours || 0}`, margin + 5, yPos);
  doc.text(`Short Days: ${(employee.shortDays || 0).toFixed(2)}`, margin + 60, yPos);
  
  yPos += 15;
  
  // Earnings Table
  doc.setFillColor(34, 139, 34); // Green
  doc.rect(margin, yPos, (pageWidth - 2 * margin) / 2 - 5, 8, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.text('EARNINGS', margin + 25, yPos + 6);
  
  // Deductions Header
  doc.setFillColor(220, 53, 69); // Red
  doc.rect(pageWidth / 2 + 2.5, yPos, (pageWidth - 2 * margin) / 2 - 5, 8, 'F');
  doc.text('DEDUCTIONS', pageWidth / 2 + 27, yPos + 6);
  
  yPos += 10;
  doc.setTextColor(0, 0, 0);
  doc.setFont('helvetica', 'normal');
  
  // Earnings
  const earningsX = margin + 5;
  const earningsValX = margin + 70;
  
  doc.text('Basic (Present + WO + HL):', earningsX, yPos);
  const basicAmount = employee.perDaySalary * (employee.presentDays + employee.effectiveWO + employee.effectiveHL);
  doc.text(`₹${Math.round(basicAmount).toLocaleString('en-IN')}`, earningsValX, yPos);
  
  yPos += 7;
  doc.text('Sunday Working:', earningsX, yPos);
  const sundayAmount = employee.perDaySalary * employee.sundayWorked;
  doc.text(`₹${Math.round(sundayAmount).toLocaleString('en-IN')}`, earningsValX, yPos);
  
  yPos += 7;
  doc.text('Holiday Working:', earningsX, yPos);
  const holidayAmount = employee.perDaySalary * employee.holidayWorked;
  doc.text(`₹${Math.round(holidayAmount).toLocaleString('en-IN')}`, earningsValX, yPos);
  
  yPos += 7;
  doc.text('Overtime Amount:', earningsX, yPos);
  doc.text(`₹${employee.otAmount.toLocaleString('en-IN')}`, earningsValX, yPos);
  
  // Deductions
  const deductX = pageWidth / 2 + 7;
  const deductValX = pageWidth / 2 + 65;
  
  yPos -= 21; // Go back up
  
  doc.text('Short Hours Deduction:', deductX, yPos);
  doc.text(`₹${(employee.shortDeduction || 0).toLocaleString('en-IN')}`, deductValX, yPos);
  
  yPos += 7;
  doc.text('Sandwich Deduction:', deductX, yPos);
  const sandwichDeduct = employee.perDaySalary * employee.sandwichDays;
  doc.text(`₹${Math.round(sandwichDeduct).toLocaleString('en-IN')}`, deductValX, yPos);
  
  yPos += 7;
  doc.text('Absent Deduction:', deductX, yPos);
  const absentDeduct = employee.perDaySalary * employee.absentDays;
  doc.text(`₹${Math.round(absentDeduct).toLocaleString('en-IN')}`, deductValX, yPos);
  
  yPos += 25;
  
  // Gross and Net Salary
  doc.setDrawColor(47, 84, 150);
  doc.setLineWidth(0.5);
  doc.line(margin, yPos, pageWidth - margin, yPos);
  
  yPos += 8;
  doc.setFontSize(11);
  
  // Gross
  doc.setFont('helvetica', 'bold');
  doc.text('Gross Salary:', margin + 5, yPos);
  doc.text(`₹${employee.grossSalary.toLocaleString('en-IN')}`, margin + 70, yPos);
  
  // OT
  doc.text('(+) OT Amount:', pageWidth / 2 + 7, yPos);
  doc.text(`₹${employee.otAmount.toLocaleString('en-IN')}`, pageWidth / 2 + 60, yPos);
  
  yPos += 8;
  // Short Deduction
  doc.text('(-) Short Deduction:', pageWidth / 2 + 7, yPos);
  doc.setTextColor(220, 53, 69);
  doc.text(`₹${(employee.shortDeduction || 0).toLocaleString('en-IN')}`, pageWidth / 2 + 60, yPos);
  doc.setTextColor(0, 0, 0);
  
  yPos += 12;
  
  // NET PAYABLE - Big box
  doc.setFillColor(47, 84, 150);
  doc.roundedRect(margin, yPos, pageWidth - 2 * margin, 20, 3, 3, 'F');
  
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(14);
  doc.text('NET PAYABLE:', margin + 10, yPos + 13);
  doc.setFontSize(16);
  doc.text(`₹${employee.totalSalary.toLocaleString('en-IN')}`, pageWidth - margin - 50, yPos + 13);
  
  yPos += 30;
  doc.setTextColor(0, 0, 0);
  
  // Total Payable Days
  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  doc.text(`Total Payable Days: Present (${employee.presentDays}) + Sunday (${employee.sundayWorked}) + OT Days (${employee.otDays}) = ${employee.totalPayableDays || (employee.presentDays + employee.sundayWorked + employee.otDays).toFixed(2)}`, margin, yPos);
  
  yPos += 15;
  
  // Footer
  doc.setDrawColor(200, 200, 200);
  doc.line(margin, yPos, pageWidth - margin, yPos);
  
  yPos += 10;
  doc.setFontSize(8);
  doc.setTextColor(128, 128, 128);
  doc.text('This is a computer generated salary slip.', pageWidth / 2, yPos, { align: 'center' });
  doc.text(`Generated on: ${new Date().toLocaleDateString('en-IN')}`, pageWidth / 2, yPos + 5, { align: 'center' });
  
  // Save
  const date = new Date().toISOString().split('T')[0];
  doc.save(`Salary_Slip_${employee.name}_${date}.pdf`);
};

