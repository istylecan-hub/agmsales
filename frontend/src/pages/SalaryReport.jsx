import React, { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { exportSalaryToExcel, exportSalaryToPDF, exportEmployeeBreakdownToExcel, generateSalarySlipPDF } from '../utils/exportUtils';
import { DAY_CLASSIFICATIONS } from '../utils/constants';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/alert';
import { toast } from 'sonner';
import {
  FileSpreadsheet,
  FileText,
  Download,
  Receipt,
  Search,
  Users,
  IndianRupee,
  Clock,
  AlertCircle,
  ArrowUpDown,
  Eye,
  Calendar,
  X,
  Save,
  History,
  TrendingUp,
  ArrowLeftRight,
  Edit,
  Trash2,
  Check,
  Wallet,
} from 'lucide-react';

export default function SalaryReport() {
  const navigate = useNavigate();
  const { t, calculationResults, employees, config: salaryConfig, attendanceData } = useApp();
  
  // Get month/year from attendanceData
  const selectedMonth = attendanceData?.selectedMonth || new Date().getMonth() + 1;
  const selectedYear = attendanceData?.selectedYear || new Date().getFullYear();
  const daysInMonth = attendanceData?.daysInMonth || 30;
  
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState('code');
  const [sortOrder, setSortOrder] = useState('asc');
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  
  // Salary History states
  const [salaryHistory, setSalaryHistory] = useState([]);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [isCompareModalOpen, setIsCompareModalOpen] = useState(false);
  const [isGrowthModalOpen, setIsGrowthModalOpen] = useState(false);
  const [selectedHistoryRecord, setSelectedHistoryRecord] = useState(null);
  const [compareMonth1, setCompareMonth1] = useState('');
  const [compareMonth2, setCompareMonth2] = useState('');
  const [comparisonData, setComparisonData] = useState(null);
  const [growthEmployee, setGrowthEmployee] = useState('');
  const [growthData, setGrowthData] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  
  const API_URL = process.env.REACT_APP_BACKEND_URL;

  // Helper to get auth token
  const getAuthHeaders = () => {
    const token = sessionStorage.getItem('auth_token');
    return token ? { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` } : { 'Content-Type': 'application/json' };
  };

  // Load salary history on mount
  useEffect(() => {
    loadSalaryHistory();
  }, []);

  const loadSalaryHistory = async () => {
    setIsLoadingHistory(true);
    try {
      const res = await fetch(`${API_URL}/api/salary/history`, {
        headers: getAuthHeaders(),
      });
      const data = await res.json();
      if (data.success) {
        setSalaryHistory(data.data || []);
      }
    } catch (err) {
      console.error('Error loading salary history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const handleSaveSalary = async () => {
    if (!calculationResults?.results || !selectedMonth || !selectedYear) {
      toast.error('No salary data to save');
      return;
    }
    
    setIsSaving(true);
    try {
      const payload = {
        month: parseInt(selectedMonth),
        year: parseInt(selectedYear),
        daysInMonth: parseInt(daysInMonth) || 30,
        employees: calculationResults.results.map(r => ({
          code: String(r.code || ''),
          name: String(r.name || ''),
          department: String(r.department || ''),
          baseSalary: parseFloat(r.monthlySalary) || 0,
          presentDays: parseFloat(r.presentDays) || 0,
          absentDays: parseFloat(r.absentDays) || 0,
          sandwichDays: parseFloat(r.sandwichDays) || 0,
          sundayWorking: parseFloat(r.sundayWorked) || 0,
          otHours: parseFloat(r.otHours) || 0,
          shortHours: parseFloat(r.shortHours) || 0,
          netOTHours: parseFloat(r.netOTHours) || 0,
          totalPayableDays: parseFloat(r.totalPayableDays) || 0,
          totalSalary: parseFloat(r.totalSalary) || 0,
          perDaySalary: parseFloat(r.perDaySalary) || 0,
          otAmount: parseFloat(r.otAmount) || 0,
          deductions: parseFloat(r.deductions) || 0
        })),
        totalPayout: parseFloat(calculationResults.summary?.totalSalary) || 0,
        config: salaryConfig || {}
      };
      
      console.log('Saving salary payload:', payload);
      
      const res = await fetch(`${API_URL}/api/salary/save`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload)
      });
      
      const text = await res.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch {
        console.error('Invalid JSON response:', text);
        toast.error('Server error: Invalid response');
        return;
      }
      
      if (res.ok && data.success) {
        toast.success(`Salary saved for ${selectedMonth}/${selectedYear}`);
        loadSalaryHistory();
      } else {
        console.error('Save failed:', data);
        toast.error(data.message || data.detail || 'Failed to save salary');
      }
    } catch (err) {
      console.error('Save salary error:', err);
      toast.error('Error saving salary: ' + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleViewHistoryRecord = async (record) => {
    try {
      const res = await fetch(`${API_URL}/api/salary/history/${record.year}/${record.month}`, {
        headers: getAuthHeaders(),
      });
      const data = await res.json();
      if (data.success) {
        setSelectedHistoryRecord(data.data);
        setIsHistoryModalOpen(true);
      } else {
        toast.error('Failed to load salary record');
      }
    } catch (err) {
      toast.error('Error loading salary record');
    }
  };

  const handleDeleteHistoryRecord = async (record) => {
    if (!window.confirm(`Delete salary record for ${record.month}/${record.year}?`)) return;
    
    try {
      const res = await fetch(`${API_URL}/api/salary/history/${record.year}/${record.month}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      const data = await res.json();
      if (data.success) {
        toast.success('Salary record deleted');
        loadSalaryHistory();
      } else {
        toast.error(data.message || 'Failed to delete');
      }
    } catch (err) {
      toast.error('Error deleting record');
    }
  };

  const handleCompareMonths = async () => {
    if (!compareMonth1 || !compareMonth2) {
      toast.error('Select both months to compare');
      return;
    }
    
    const [y1, m1] = compareMonth1.split('-');
    const [y2, m2] = compareMonth2.split('-');
    
    try {
      const res = await fetch(`${API_URL}/api/salary/compare/${y1}/${m1}/${y2}/${m2}`, {
        headers: getAuthHeaders(),
      });
      const data = await res.json();
      if (data.success) {
        setComparisonData(data.data);
      } else {
        toast.error(data.message || 'Failed to compare');
      }
    } catch (err) {
      toast.error('Error comparing months');
    }
  };

  const handleEmployeeGrowth = async () => {
    if (!growthEmployee) {
      toast.error('Select an employee');
      return;
    }
    
    try {
      const res = await fetch(`${API_URL}/api/salary/employee/${growthEmployee}/growth`, {
        headers: getAuthHeaders(),
      });
      const data = await res.json();
      if (data.success) {
        setGrowthData(data.data);
      } else {
        toast.error(data.message || 'No growth data found');
      }
    } catch (err) {
      toast.error('Error loading growth data');
    }
  };

  const getMonthName = (month) => {
    const months = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return months[month] || '';
  };

  // Filter and sort results
  const filteredResults = useMemo(() => {
    if (!calculationResults?.results) return [];
    
    let filtered = calculationResults.results.filter(r => 
      r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      String(r.code).includes(searchQuery)
    );
    
    filtered.sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];
      
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }
      
      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });
    
    return filtered;
  }, [calculationResults, searchQuery, sortField, sortOrder]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const handleViewDetails = (employee) => {
    setSelectedEmployee(employee);
    setIsDetailModalOpen(true);
  };

  const handleDownloadExcel = () => {
    if (!calculationResults) {
      toast.error('No calculation results to export');
      return;
    }
    exportSalaryToExcel(calculationResults.results, calculationResults.summary);
    toast.success('Excel report downloaded');
  };

  const handleDownloadPDF = () => {
    if (!calculationResults) {
      toast.error('No calculation results to export');
      return;
    }
    exportSalaryToPDF(calculationResults.results, calculationResults.summary);
    toast.success('PDF report downloaded');
  };

  const handleDownloadEmployeeBreakdown = (employee) => {
    exportEmployeeBreakdownToExcel(employee);
    toast.success(`Breakdown for ${employee.name} downloaded`);
  };

  const handleDownloadSalarySlip = (employee) => {
    generateSalarySlipPDF(employee);
    toast.success(`Salary slip for ${employee.name} downloaded`);
  };

  const getClassificationBadge = (classification) => {
    switch (classification) {
      case DAY_CLASSIFICATIONS.PRESENT:
        return <Badge className="bg-green-500/10 text-green-500 border-green-500/20">Present</Badge>;
      case DAY_CLASSIFICATIONS.ABSENT:
        return <Badge className="bg-red-500/10 text-red-500 border-red-500/20">Absent</Badge>;
      case DAY_CLASSIFICATIONS.SUNDAY_WORKED:
        return <Badge className="bg-blue-500/10 text-blue-500 border-blue-500/20">Sun Worked</Badge>;
      case DAY_CLASSIFICATIONS.HOLIDAY_WORKED:
        return <Badge className="bg-purple-500/10 text-purple-500 border-purple-500/20">HL Worked</Badge>;
      case DAY_CLASSIFICATIONS.WEEK_OFF:
        return <Badge className="bg-gray-500/10 text-gray-500 border-gray-500/20">Week Off</Badge>;
      case DAY_CLASSIFICATIONS.HOLIDAY_OFF:
        return <Badge className="bg-cyan-500/10 text-cyan-500 border-cyan-500/20">Holiday</Badge>;
      default:
        return <Badge variant="secondary">{classification}</Badge>;
    }
  };

  if (!calculationResults) {
    return (
      <div className="space-y-6" data-testid="salary-report-page">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-4xl font-bold tracking-tight font-[Manrope]">{t('reports')}</h1>
            <p className="text-muted-foreground mt-1">View and download salary reports</p>
          </div>
          <Button 
            variant="outline" 
            onClick={() => setIsHistoryModalOpen(true)} 
            className="gap-2"
            data-testid="view-history-btn-empty"
          >
            <History className="w-4 h-4" />
            Salary History ({salaryHistory.length})
          </Button>
        </div>
        
        <Alert data-testid="no-results-alert">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>No Calculation Results</AlertTitle>
          <AlertDescription>
            Please upload attendance and calculate salaries first.
            <Button 
              variant="link" 
              className="px-2 h-auto"
              onClick={() => navigate('/attendance')}
            >
              Go to Attendance Upload
            </Button>
          </AlertDescription>
        </Alert>

        {/* Salary History Section - Always visible */}
        {salaryHistory.length > 0 && (
          <Card data-testid="saved-salary-history-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="w-5 h-5 text-purple-500" />
                Saved Salary Records
                <Badge variant="secondary">{salaryHistory.length} months</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">
                Previously saved salary calculations. Click delete (🗑️) to remove a record before uploading new attendance for that month.
              </p>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Month/Year</TableHead>
                      <TableHead className="text-center">Employees</TableHead>
                      <TableHead className="text-right">Total Payout</TableHead>
                      <TableHead className="text-center">Saved On</TableHead>
                      <TableHead className="text-center">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {salaryHistory.map((record) => (
                      <TableRow key={record.record_id}>
                        <TableCell className="font-medium">
                          {getMonthName(record.month)} {record.year}
                        </TableCell>
                        <TableCell className="text-center">{record.employeeCount}</TableCell>
                        <TableCell className="text-right font-mono">
                          ₹{record.totalPayout?.toLocaleString() || 0}
                        </TableCell>
                        <TableCell className="text-center text-muted-foreground text-sm">
                          {record.savedAt ? new Date(record.savedAt).toLocaleDateString() : '-'}
                        </TableCell>
                        <TableCell className="text-center">
                          <div className="flex justify-center gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleViewHistoryRecord(record)}
                              title="View Details"
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleDeleteHistoryRecord(record)}
                              title="Delete Record"
                              className="text-red-500 hover:text-red-600 hover:bg-red-500/10"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        )}

        {/* History Modal - Reuse existing */}
        <Dialog open={isHistoryModalOpen} onOpenChange={setIsHistoryModalOpen}>
          <DialogContent className="max-w-4xl max-h-[90vh]" data-testid="history-modal">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <History className="w-5 h-5" />
                Salary History
              </DialogTitle>
              <DialogDescription>
                View, compare, and manage saved salary records
              </DialogDescription>
            </DialogHeader>
            
            <ScrollArea className="max-h-[400px]">
              {isLoadingHistory ? (
                <div className="text-center py-8 text-muted-foreground">Loading...</div>
              ) : salaryHistory.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No salary records saved yet
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Month/Year</TableHead>
                      <TableHead className="text-center">Employees</TableHead>
                      <TableHead className="text-right">Total Payout</TableHead>
                      <TableHead className="text-center">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {salaryHistory.map((record) => (
                      <TableRow key={record.record_id}>
                        <TableCell className="font-medium">
                          {getMonthName(record.month)} {record.year}
                        </TableCell>
                        <TableCell className="text-center">{record.employeeCount}</TableCell>
                        <TableCell className="text-right font-mono">
                          ₹{record.totalPayout?.toLocaleString() || 0}
                        </TableCell>
                        <TableCell className="text-center">
                          <div className="flex justify-center gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleViewHistoryRecord(record)}
                              title="View Details"
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleDeleteHistoryRecord(record)}
                              title="Delete"
                              className="text-red-500 hover:text-red-600"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </ScrollArea>
          </DialogContent>
        </Dialog>
      </div>
    );
  }

  const { summary } = calculationResults;

  return (
    <div className="space-y-6" data-testid="salary-report-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight font-[Manrope]">{t('reports')}</h1>
          <p className="text-muted-foreground mt-1">
            Salary calculation results 
            {selectedMonth && selectedYear && (
              <span className="ml-2 text-primary font-medium">
                ({getMonthName(selectedMonth)} {selectedYear})
              </span>
            )}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button 
            onClick={handleSaveSalary} 
            disabled={isSaving || !calculationResults}
            className="gap-2 bg-green-600 hover:bg-green-700" 
            data-testid="save-salary-btn"
          >
            <Save className="w-4 h-4" />
            {isSaving ? 'Saving...' : 'Save Salary'}
          </Button>
          <Button 
            variant="outline" 
            onClick={() => setIsHistoryModalOpen(true)} 
            className="gap-2"
            data-testid="view-history-btn"
          >
            <History className="w-4 h-4" />
            Past Months ({salaryHistory.length})
          </Button>
          <Button onClick={handleDownloadExcel} className="gap-2" data-testid="download-excel-btn">
            <FileSpreadsheet className="w-4 h-4" />
            {t('downloadExcel')}
          </Button>
          <Button variant="outline" onClick={handleDownloadPDF} className="gap-2" data-testid="download-pdf-btn">
            <FileText className="w-4 h-4" />
            {t('downloadPDF')}
          </Button>
        </div>
      </div>

      {/* Summary Dashboard */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4" data-testid="summary-dashboard">
        <Card className="hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('totalEmployees')}</p>
                <p className="text-3xl font-bold font-[JetBrains_Mono] mt-1">{summary.totalEmployees}</p>
              </div>
              <div className="p-3 bg-blue-500/10 rounded-xl">
                <Users className="w-6 h-6 text-blue-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('totalSalary')}</p>
                <p className="text-2xl font-bold font-[JetBrains_Mono] mt-1">
                  ₹{summary.totalSalary.toLocaleString('en-IN')}
                </p>
              </div>
              <div className="p-3 bg-green-500/10 rounded-xl">
                <IndianRupee className="w-6 h-6 text-green-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('totalOT')}</p>
                <p className="text-2xl font-bold font-[JetBrains_Mono] mt-1 text-orange-500">
                  ₹{summary.totalOT.toLocaleString('en-IN')}
                </p>
              </div>
              <div className="p-3 bg-orange-500/10 rounded-xl">
                <Clock className="w-6 h-6 text-orange-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        {(summary.totalAdvance || 0) > 0 && (
          <Card className="hover:-translate-y-0.5 hover:shadow-md transition-all duration-200 border-amber-500/30">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Advance</p>
                  <p className="text-2xl font-bold font-[JetBrains_Mono] mt-1 text-amber-600">
                    -₹{(summary.totalAdvance || 0).toLocaleString('en-IN')}
                  </p>
                </div>
                <div className="p-3 bg-amber-500/10 rounded-xl">
                  <Wallet className="w-6 h-6 text-amber-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {(summary.totalAdvance || 0) > 0 && (
          <Card className="hover:-translate-y-0.5 hover:shadow-md transition-all duration-200 border-emerald-500/30">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Net Payable</p>
                  <p className="text-2xl font-bold font-[JetBrains_Mono] mt-1 text-emerald-600">
                    ₹{(summary.totalNetSalary || summary.totalSalary).toLocaleString('en-IN')}
                  </p>
                </div>
                <div className="p-3 bg-emerald-500/10 rounded-xl">
                  <IndianRupee className="w-6 h-6 text-emerald-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <Card className="hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('zeroSalary')}</p>
                <p className="text-3xl font-bold font-[JetBrains_Mono] mt-1 text-red-500">
                  {summary.zeroSalaryCount}
                </p>
              </div>
              <div className="p-3 bg-red-500/10 rounded-xl">
                <AlertCircle className="w-6 h-6 text-red-500" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search & Filter */}
      <Card>
        <CardContent className="p-4">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search by name or code..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
              data-testid="report-search-input"
            />
          </div>
        </CardContent>
      </Card>

      {/* Salary Table */}
      <Card data-testid="salary-table-card">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="sticky left-0 bg-card z-10">S.No</TableHead>
                  <TableHead 
                    className="cursor-pointer hover:bg-secondary/50"
                    onClick={() => handleSort('code')}
                  >
                    <div className="flex items-center gap-1">
                      Code
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </TableHead>
                  <TableHead 
                    className="cursor-pointer hover:bg-secondary/50"
                    onClick={() => handleSort('name')}
                  >
                    <div className="flex items-center gap-1">
                      Name
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </TableHead>
                  <TableHead>Dept</TableHead>
                  <TableHead className="text-right">Monthly</TableHead>
                  <TableHead className="text-right">Per Day</TableHead>
                  <TableHead className="text-center">Present</TableHead>
                  <TableHead className="text-center">Sun</TableHead>
                  <TableHead className="text-center">HL</TableHead>
                  <TableHead className="text-center">WO</TableHead>
                  <TableHead className="text-center">Sand.</TableHead>
                  <TableHead className="text-center">Paid</TableHead>
                  <TableHead className="text-center">Absent</TableHead>
                  <TableHead className="text-center">OT Hrs</TableHead>
                  <TableHead className="text-center">Short Hrs</TableHead>
                  <TableHead className="text-center">Net OT</TableHead>
                  <TableHead className="text-center">OT Days</TableHead>
                  <TableHead className="text-center">Payable</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                  <TableHead className="text-right">Advance</TableHead>
                  <TableHead className="text-right">Net Pay</TableHead>
                  <TableHead className="text-center">Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredResults.map((result, index) => (
                  <TableRow 
                    key={result.code}
                    className={result.isZeroAttendance ? 'bg-red-500/5' : ''}
                    data-testid={`salary-row-${result.code}`}
                  >
                    <TableCell className="sticky left-0 bg-card font-medium">{index + 1}</TableCell>
                    <TableCell className="font-mono">{result.code}</TableCell>
                    <TableCell className="font-medium">{result.name}</TableCell>
                    <TableCell className="text-muted-foreground">{result.department || '-'}</TableCell>
                    <TableCell className="text-right font-mono">₹{result.monthlySalary.toLocaleString('en-IN')}</TableCell>
                    <TableCell className="text-right font-mono text-sm">₹{result.perDaySalary.toFixed(0)}</TableCell>
                    <TableCell className="text-center">
                      <Badge variant="outline" className="font-mono">{result.presentDays}</Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge 
                        variant={result.sundayWorked > 0 ? 'default' : 'secondary'}
                        className="font-mono"
                      >
                        {result.sundayWorked}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge 
                        variant={result.holidayWorked > 0 ? 'default' : 'secondary'}
                        className="font-mono"
                      >
                        {result.holidayWorked}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center font-mono text-sm">{result.effectiveWO}</TableCell>
                    <TableCell className="text-center">
                      {result.sandwichDays > 0 ? (
                        <Badge className="bg-yellow-500/10 text-yellow-600 font-mono">{result.sandwichDays}</Badge>
                      ) : (
                        <span className="font-mono text-sm">0</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge className="bg-green-500/10 text-green-600 font-mono">{result.paidDays}</Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      {result.absentDays > 0 ? (
                        <Badge className="bg-red-500/10 text-red-500 font-mono">{result.absentDays}</Badge>
                      ) : (
                        <span className="font-mono text-sm">0</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      {result.otHours > 0 ? (
                        <Badge className="bg-orange-500/10 text-orange-500 font-mono">{result.otHours}</Badge>
                      ) : (
                        <span className="font-mono text-sm">0</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      {result.shortHours > 0 ? (
                        <Badge className="bg-red-500/10 text-red-500 font-mono">{result.shortHours}</Badge>
                      ) : (
                        <span className="font-mono text-sm">0</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      {(result.netOTHours || 0) > 0 ? (
                        <Badge className="bg-green-500/10 text-green-600 font-mono">{result.netOTHours || 0}</Badge>
                      ) : (
                        <span className="font-mono text-sm">0</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      {result.otDays > 0 ? (
                        <Badge className="bg-blue-500/10 text-blue-500 font-mono">{result.otDays}</Badge>
                      ) : (
                        <span className="font-mono text-sm">0</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge className="bg-primary/10 text-primary font-mono font-bold">{result.totalPayableDays}</Badge>
                    </TableCell>
                    <TableCell className="text-right font-mono font-bold">
                      ₹{result.totalSalary.toLocaleString('en-IN')}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {(result.advanceAmount || 0) > 0 ? (
                        <span className="text-amber-600">-₹{result.advanceAmount.toLocaleString('en-IN')}</span>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right font-mono font-bold">
                      {(result.advanceAmount || 0) > 0 ? (
                        <span className="text-emerald-600">₹{(result.netSalary ?? result.totalSalary).toLocaleString('en-IN')}</span>
                      ) : (
                        <span>₹{result.totalSalary.toLocaleString('en-IN')}</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      <div className="flex justify-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleViewDetails(result)}
                          title="View Details"
                          data-testid={`view-details-${result.code}`}
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDownloadSalarySlip(result)}
                          title="Download Salary Slip"
                          className="text-green-600 hover:text-green-700"
                          data-testid={`salary-slip-${result.code}`}
                        >
                          <Receipt className="w-4 h-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Totals Row */}
      <Card className="bg-primary/5 border-primary/20" data-testid="totals-card">
        <CardContent className="p-4">
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4 text-center">
            <div>
              <p className="text-sm text-muted-foreground">Total Present Days</p>
              <p className="text-xl font-bold font-[JetBrains_Mono]">
                {filteredResults.reduce((s, r) => s + r.presentDays, 0).toFixed(1)}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Total Sunday Working</p>
              <p className="text-xl font-bold font-[JetBrains_Mono] text-blue-500">
                {filteredResults.reduce((s, r) => s + r.sundayWorked, 0).toFixed(1)}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Total OT Days</p>
              <p className="text-xl font-bold font-[JetBrains_Mono] text-orange-500">
                {filteredResults.reduce((s, r) => s + r.otDays, 0).toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Gross Salary</p>
              <p className="text-xl font-bold font-[JetBrains_Mono]">
                ₹{summary.totalSalary.toLocaleString('en-IN')}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Total Advance</p>
              <p className="text-xl font-bold font-[JetBrains_Mono] text-amber-600">
                -₹{(summary.totalAdvance || 0).toLocaleString('en-IN')}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Net Payable</p>
              <p className="text-xl font-bold font-[JetBrains_Mono] text-emerald-600">
                ₹{(summary.totalNetSalary || summary.totalSalary).toLocaleString('en-IN')}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Employee Detail Modal */}
      <Dialog open={isDetailModalOpen} onOpenChange={setIsDetailModalOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh]" data-testid="employee-detail-modal">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>
                {selectedEmployee?.name} (Code: {selectedEmployee?.code})
              </span>
              <div className="flex gap-2">
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => selectedEmployee && handleDownloadSalarySlip(selectedEmployee)}
                  className="gap-2 bg-green-600 hover:bg-green-700"
                  data-testid="download-salary-slip-btn"
                >
                  <Receipt className="w-4 h-4" />
                  Salary Slip
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => selectedEmployee && handleDownloadEmployeeBreakdown(selectedEmployee)}
                  className="gap-2"
                  data-testid="download-breakdown-btn"
                >
                  <Download className="w-4 h-4" />
                  Breakdown
                </Button>
              </div>
            </DialogTitle>
            <DialogDescription>
              Detailed salary breakdown and attendance summary
            </DialogDescription>
          </DialogHeader>
          
          {selectedEmployee && (
            <div className="space-y-4">
              {/* Employee Summary */}
              <div className="grid grid-cols-2 md:grid-cols-6 gap-3 p-4 bg-secondary/30 rounded-lg">
                <div className="text-center">
                  <p className="text-xs text-muted-foreground">Monthly Salary</p>
                  <p className="font-bold font-[JetBrains_Mono]">₹{selectedEmployee.monthlySalary.toLocaleString('en-IN')}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted-foreground">Present Days</p>
                  <p className="font-bold font-[JetBrains_Mono] text-green-500">{selectedEmployee.presentDays}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted-foreground">Sunday Working</p>
                  <p className="font-bold font-[JetBrains_Mono] text-blue-500">{selectedEmployee.sundayWorked}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted-foreground">OT Days</p>
                  <p className="font-bold font-[JetBrains_Mono] text-orange-500">{selectedEmployee.otDays}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted-foreground">Total Payable Days</p>
                  <p className="font-bold font-[JetBrains_Mono] text-primary">{selectedEmployee.totalPayableDays}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted-foreground">Total Salary</p>
                  <p className="font-bold font-[JetBrains_Mono]">₹{selectedEmployee.totalSalary.toLocaleString('en-IN')}</p>
                </div>
              </div>

              {/* Calculation Formula */}
              <div className="p-3 bg-blue-500/10 rounded-lg text-sm">
                <p className="font-semibold text-blue-600 mb-2">Calculation Formula:</p>
                <div className="space-y-1 text-muted-foreground">
                  <p>• Per Day = ₹{selectedEmployee.monthlySalary} ÷ {selectedEmployee.daysInMonth} = ₹{selectedEmployee.perDaySalary.toFixed(2)}</p>
                  <p>• Present Days = {selectedEmployee.daysInMonth} - {selectedEmployee.absentDays} absent - {selectedEmployee.sandwichDays} sandwich = {selectedEmployee.presentDays}</p>
                  <p>• Net OT = {selectedEmployee.otHours} hrs - {selectedEmployee.shortHours} short hrs = {selectedEmployee.netOTHours || 0} hrs</p>
                  <p>• OT Days = {selectedEmployee.netOTHours || 0} ÷ 9 = {selectedEmployee.otDays} days</p>
                  <p>• Payable Days = {selectedEmployee.presentDays} + {selectedEmployee.sundayWorked} Sun + {selectedEmployee.otDays} OT = {selectedEmployee.totalPayableDays}</p>
                  <p className="font-semibold text-primary">• Total = ₹{selectedEmployee.perDaySalary.toFixed(2)} × {selectedEmployee.totalPayableDays} = ₹{selectedEmployee.totalSalary}</p>
                  {(selectedEmployee.advanceAmount || 0) > 0 && (
                    <p className="font-semibold text-amber-600">• Advance Deducted = -₹{selectedEmployee.advanceAmount.toLocaleString('en-IN')}</p>
                  )}
                  {(selectedEmployee.advanceAmount || 0) > 0 && (
                    <p className="font-semibold text-emerald-600">• Net Payable = ₹{(selectedEmployee.netSalary ?? selectedEmployee.totalSalary).toLocaleString('en-IN')}</p>
                  )}
                </div>
                {selectedEmployee.onlySundayNoOT && (
                  <p className="mt-2 text-orange-500 font-semibold">⚠️ This employee has "Only Sunday, No OT" setting enabled</p>
                )}
              </div>

              {/* Daily Breakdown Table */}
              <ScrollArea className="h-[400px]">
                <Table>
                  <TableHeader className="sticky top-0 bg-card">
                    <TableRow>
                      <TableHead className="w-12">Day</TableHead>
                      <TableHead className="w-16">Name</TableHead>
                      <TableHead>IN</TableHead>
                      <TableHead>OUT</TableHead>
                      <TableHead>Work</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-center">Value</TableHead>
                      <TableHead className="text-center">OT (min)</TableHead>
                      <TableHead className="text-center">Short (min)</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {selectedEmployee.dailyBreakdown.map((day) => (
                      <TableRow key={day.day} data-testid={`breakdown-day-${day.day}`}>
                        <TableCell className="font-mono font-bold">{day.day}</TableCell>
                        <TableCell className="text-muted-foreground">{day.dayName}</TableCell>
                        <TableCell className="font-mono">
                          {day.inTime !== '--:--' ? (
                            <span className="text-green-600">{day.inTime}</span>
                          ) : (
                            <span className="text-muted-foreground">--:--</span>
                          )}
                        </TableCell>
                        <TableCell className="font-mono">
                          {day.outTime !== '--:--' ? (
                            <span className="text-blue-600">{day.outTime}</span>
                          ) : (
                            <span className="text-muted-foreground">--:--</span>
                          )}
                        </TableCell>
                        <TableCell className="font-mono">{day.workHours}</TableCell>
                        <TableCell>{getClassificationBadge(day.classification)}</TableCell>
                        <TableCell className="text-center">
                          {day.isHalfDay ? (
                            <Badge className="bg-yellow-500/10 text-yellow-600">0.5</Badge>
                          ) : (
                            <span className="font-mono">{day.dayValue}</span>
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          {day.otMinutes > 0 ? (
                            <Badge className="bg-orange-500/10 text-orange-500 font-mono">{day.otMinutes}</Badge>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          {day.shortMinutes > 0 ? (
                            <Badge className="bg-red-500/10 text-red-500 font-mono">{day.shortMinutes}</Badge>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>

              {/* Summary Footer */}
              <div className="grid grid-cols-3 md:grid-cols-6 gap-2 p-3 bg-secondary/30 rounded-lg text-xs">
                <div className="text-center">
                  <p className="text-muted-foreground">Sundays</p>
                  <p className="font-bold">{selectedEmployee.sundayWorked}</p>
                </div>
                <div className="text-center">
                  <p className="text-muted-foreground">Holidays</p>
                  <p className="font-bold">{selectedEmployee.holidayWorked}</p>
                </div>
                <div className="text-center">
                  <p className="text-muted-foreground">Eff. WO</p>
                  <p className="font-bold">{selectedEmployee.effectiveWO}</p>
                </div>
                <div className="text-center">
                  <p className="text-muted-foreground">Eff. HL</p>
                  <p className="font-bold">{selectedEmployee.effectiveHL}</p>
                </div>
                <div className="text-center">
                  <p className="text-muted-foreground">Sandwich</p>
                  <p className="font-bold text-yellow-600">{selectedEmployee.sandwichDays}</p>
                </div>
                <div className="text-center">
                  <p className="text-muted-foreground">Absent</p>
                  <p className="font-bold text-red-500">{selectedEmployee.absentDays}</p>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Salary History Modal */}
      <Dialog open={isHistoryModalOpen} onOpenChange={setIsHistoryModalOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh]" data-testid="history-modal">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <History className="w-5 h-5" />
                Saved Salary Records
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setIsHistoryModalOpen(false);
                    setIsCompareModalOpen(true);
                  }}
                  className="gap-2"
                >
                  <ArrowLeftRight className="w-4 h-4" />
                  Compare Months
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setIsHistoryModalOpen(false);
                    setIsGrowthModalOpen(true);
                  }}
                  className="gap-2"
                >
                  <TrendingUp className="w-4 h-4" />
                  Employee Growth
                </Button>
              </div>
            </DialogTitle>
            <DialogDescription>
              View, compare and track salary history
            </DialogDescription>
          </DialogHeader>
          
          <ScrollArea className="max-h-[60vh]">
            {salaryHistory.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <History className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>No saved salary records yet</p>
                <p className="text-sm">Click "Save Salary" to save current calculations</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Month/Year</TableHead>
                    <TableHead className="text-right">Employees</TableHead>
                    <TableHead className="text-right">Total Payout</TableHead>
                    <TableHead>Saved On</TableHead>
                    <TableHead className="text-center">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {salaryHistory.map((record) => (
                    <TableRow key={record.record_id}>
                      <TableCell className="font-medium">
                        <Badge variant="outline">
                          {getMonthName(record.month)} {record.year}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {record.employeeCount}
                      </TableCell>
                      <TableCell className="text-right font-mono font-bold">
                        ₹{(record.totalPayout || 0).toLocaleString('en-IN')}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {record.savedAt ? new Date(record.savedAt).toLocaleDateString() : '-'}
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex justify-center gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleViewHistoryRecord(record)}
                            title="View Details"
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDeleteHistoryRecord(record)}
                            title="Delete"
                            className="text-red-500 hover:text-red-600"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </ScrollArea>

          {/* Show selected history record details */}
          {selectedHistoryRecord && (
            <div className="mt-4 border-t pt-4">
              <h4 className="font-semibold mb-3">
                Details for {getMonthName(selectedHistoryRecord.month)} {selectedHistoryRecord.year}
              </h4>
              <ScrollArea className="max-h-[300px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Code</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead className="text-center">Present</TableHead>
                      <TableHead className="text-center">OT Hrs</TableHead>
                      <TableHead className="text-center">Payable</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(selectedHistoryRecord.employees || []).map((emp) => (
                      <TableRow key={emp.code}>
                        <TableCell className="font-mono">{emp.code}</TableCell>
                        <TableCell>{emp.name}</TableCell>
                        <TableCell className="text-center">{emp.presentDays}</TableCell>
                        <TableCell className="text-center">{emp.otHours || 0}</TableCell>
                        <TableCell className="text-center">{emp.totalPayableDays}</TableCell>
                        <TableCell className="text-right font-mono font-bold">
                          ₹{(emp.totalSalary || 0).toLocaleString('en-IN')}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Compare Months Modal */}
      <Dialog open={isCompareModalOpen} onOpenChange={setIsCompareModalOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh]" data-testid="compare-modal">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ArrowLeftRight className="w-5 h-5" />
              Compare Salary Months
            </DialogTitle>
            <DialogDescription>
              Select two months to compare salary data
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Month 1</label>
              <Select value={compareMonth1} onValueChange={setCompareMonth1}>
                <SelectTrigger>
                  <SelectValue placeholder="Select month" />
                </SelectTrigger>
                <SelectContent>
                  {salaryHistory.map((r) => (
                    <SelectItem key={r.record_id} value={r.record_id}>
                      {getMonthName(r.month)} {r.year}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground mb-1 block">Month 2</label>
              <Select value={compareMonth2} onValueChange={setCompareMonth2}>
                <SelectTrigger>
                  <SelectValue placeholder="Select month" />
                </SelectTrigger>
                <SelectContent>
                  {salaryHistory.map((r) => (
                    <SelectItem key={r.record_id} value={r.record_id}>
                      {getMonthName(r.month)} {r.year}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          
          <Button onClick={handleCompareMonths} className="w-full mb-4">
            Compare
          </Button>

          {comparisonData && (
            <div className="space-y-4">
              {/* Summary */}
              <div className="grid grid-cols-3 gap-4 p-4 bg-secondary/30 rounded-lg">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">{comparisonData.month1.label}</p>
                  <p className="text-xl font-bold font-mono">
                    ₹{(comparisonData.summary.totalPayout1 || 0).toLocaleString('en-IN')}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Difference</p>
                  <p className={`text-xl font-bold font-mono ${comparisonData.summary.difference >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {comparisonData.summary.difference >= 0 ? '+' : ''}₹{(comparisonData.summary.difference || 0).toLocaleString('en-IN')}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">{comparisonData.month2.label}</p>
                  <p className="text-xl font-bold font-mono">
                    ₹{(comparisonData.summary.totalPayout2 || 0).toLocaleString('en-IN')}
                  </p>
                </div>
              </div>

              {/* Employee-wise comparison */}
              <ScrollArea className="max-h-[400px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Employee</TableHead>
                      <TableHead className="text-right">{comparisonData.month1.label}</TableHead>
                      <TableHead className="text-right">{comparisonData.month2.label}</TableHead>
                      <TableHead className="text-right">Diff</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(comparisonData.employees || []).map((emp) => (
                      <TableRow key={emp.code}>
                        <TableCell>
                          <span className="font-mono text-sm">{emp.code}</span>
                          <span className="ml-2">{emp.name}</span>
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          ₹{(emp.salary1 || 0).toLocaleString('en-IN')}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          ₹{(emp.salary2 || 0).toLocaleString('en-IN')}
                        </TableCell>
                        <TableCell className={`text-right font-mono font-bold ${emp.difference >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {emp.difference >= 0 ? '+' : ''}₹{(emp.difference || 0).toLocaleString('en-IN')}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Employee Growth Modal */}
      <Dialog open={isGrowthModalOpen} onOpenChange={setIsGrowthModalOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh]" data-testid="growth-modal">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              Employee Salary Growth
            </DialogTitle>
            <DialogDescription>
              Track salary growth over time
            </DialogDescription>
          </DialogHeader>
          
          <div className="flex gap-4 mb-4">
            <div className="flex-1">
              <Select value={growthEmployee} onValueChange={setGrowthEmployee}>
                <SelectTrigger>
                  <SelectValue placeholder="Select employee" />
                </SelectTrigger>
                <SelectContent>
                  {employees.map((emp) => (
                    <SelectItem key={emp.code} value={emp.code}>
                      {emp.code} - {emp.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handleEmployeeGrowth}>
              View Growth
            </Button>
          </div>

          {growthData && (
            <div className="space-y-4">
              {/* Summary */}
              <div className="grid grid-cols-3 gap-4 p-4 bg-secondary/30 rounded-lg">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Months Tracked</p>
                  <p className="text-2xl font-bold">{growthData.monthsTracked}</p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Total Growth</p>
                  <p className={`text-2xl font-bold ${growthData.totalGrowth >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {growthData.totalGrowth >= 0 ? '+' : ''}₹{(growthData.totalGrowth || 0).toLocaleString('en-IN')}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Avg Monthly</p>
                  <p className={`text-2xl font-bold ${growthData.avgMonthlyGrowth >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {growthData.avgMonthlyGrowth >= 0 ? '+' : ''}₹{(growthData.avgMonthlyGrowth || 0).toLocaleString('en-IN')}
                  </p>
                </div>
              </div>

              {/* Monthly history */}
              <ScrollArea className="max-h-[400px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Month</TableHead>
                      <TableHead className="text-right">Base Salary</TableHead>
                      <TableHead className="text-center">Present Days</TableHead>
                      <TableHead className="text-center">OT Hours</TableHead>
                      <TableHead className="text-right">Total Earned</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(growthData.history || []).map((month, idx) => (
                      <TableRow key={month.label}>
                        <TableCell>
                          <Badge variant="outline">{month.label}</Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          ₹{(month.baseSalary || 0).toLocaleString('en-IN')}
                        </TableCell>
                        <TableCell className="text-center">{month.presentDays}</TableCell>
                        <TableCell className="text-center">{month.otHours || 0}</TableCell>
                        <TableCell className="text-right font-mono font-bold">
                          ₹{(month.totalSalary || 0).toLocaleString('en-IN')}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
