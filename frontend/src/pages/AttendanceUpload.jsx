import React, { useState, useRef, useCallback, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { parseAttendanceExcel, normalizeEmpCode } from '../utils/excelParser';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { ScrollArea } from '../components/ui/scroll-area';
import { Checkbox } from '../components/ui/checkbox';
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
  DialogFooter,
} from '../components/ui/dialog';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/alert';
import { toast } from 'sonner';
import {
  Upload,
  FileSpreadsheet,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  RefreshCw,
  Calendar,
  Users,
  Pencil,
  Search,
  Save,
  X,
  CalendarDays,
  Plus,
} from 'lucide-react';

export default function AttendanceUpload() {
  const navigate = useNavigate();
  const { t, employees, attendanceData, setAttendanceData, setCurrentStep } = useApp();
  const fileInputRef = useRef(null);
  
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [previewData, setPreviewData] = useState(null);
  const [matchStatus, setMatchStatus] = useState(null);
  
  // Edit mode states
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [editingAttendance, setEditingAttendance] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Holiday management states
  const [manualHolidays, setManualHolidays] = useState([]);
  const [isHolidayModalOpen, setIsHolidayModalOpen] = useState(false);
  
  // Month/Year selection states
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1); // 1-12
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  
  // Get days in selected month
  const getDaysInMonth = (month, year) => {
    return new Date(year, month, 0).getDate();
  };
  
  // Calculate correct daysInMonth based on selected month/year
  const correctDaysInMonth = getDaysInMonth(selectedMonth, selectedYear);

  // Get day names for the month
  const getDayName = (dayNum, daysInMonth) => {
    if (!attendanceData || !attendanceData.employees[0]) return '';
    const dayData = attendanceData.employees[0].dailyData.find(d => d.day === dayNum);
    return dayData?.dayName || '';
  };

  // Sync preview data when attendanceData changes
  useEffect(() => {
    if (attendanceData && !previewData) {
      const employeeCodeSet = new Set(employees.map(e => normalizeEmpCode(e.code)));
      const attendanceCodeSet = new Set(attendanceData.employees.map(e => normalizeEmpCode(e.code)));
      
      const inAttendanceNotInMaster = attendanceData.employees
        .filter(e => !employeeCodeSet.has(normalizeEmpCode(e.code)))
        .map(e => ({ code: e.code, name: e.name }));
      
      const inMasterNotInAttendance = employees
        .filter(e => !attendanceCodeSet.has(normalizeEmpCode(e.code)))
        .map(e => ({ code: e.code, name: e.name }));
      
      const preview = attendanceData.employees.map(emp => {
        const totalInDays = emp.dailyData.filter(d => d.hasIn).length;
        const sundaysWithIn = emp.dailyData.filter(d => d.isSunday && d.hasIn).length;
        const matchedInMaster = employeeCodeSet.has(normalizeEmpCode(emp.code));
        
        return {
          code: emp.code,
          name: emp.name,
          department: emp.department,
          totalInDays,
          sundaysWithIn,
          matchedInMaster,
        };
      });
      
      setPreviewData(preview);
      setMatchStatus({
        inAttendanceNotInMaster,
        inMasterNotInAttendance,
        matchedCount: attendanceData.employees.length - inAttendanceNotInMaster.length,
      });
      
      // Load existing manual holidays if any
      if (attendanceData.manualHolidays) {
        setManualHolidays(attendanceData.manualHolidays);
      }
    }
  }, [attendanceData, employees, previewData]);

  const processFile = async (file) => {
    if (!file) return;
    
    const validTypes = [
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-excel',
    ];
    
    if (!validTypes.includes(file.type) && !file.name.match(/\.(xlsx|xls)$/i)) {
      toast.error('Please upload an Excel file (.xlsx or .xls)');
      return;
    }

    setIsProcessing(true);
    setProcessingProgress(10);

    try {
      setProcessingProgress(30);
      const parsed = await parseAttendanceExcel(file);
      setProcessingProgress(70);
      
      const employeeCodeSet = new Set(employees.map(e => normalizeEmpCode(e.code)));
      const attendanceCodeSet = new Set(parsed.employees.map(e => normalizeEmpCode(e.code)));
      
      const inAttendanceNotInMaster = parsed.employees
        .filter(e => !employeeCodeSet.has(normalizeEmpCode(e.code)))
        .map(e => ({ code: e.code, name: e.name }));
      
      const inMasterNotInAttendance = employees
        .filter(e => !attendanceCodeSet.has(normalizeEmpCode(e.code)))
        .map(e => ({ code: e.code, name: e.name }));
      
      const preview = parsed.employees.map(emp => {
        const totalInDays = emp.dailyData.filter(d => d.hasIn).length;
        const sundaysWithIn = emp.dailyData.filter(d => d.isSunday && d.hasIn).length;
        const matchedInMaster = employeeCodeSet.has(normalizeEmpCode(emp.code));
        
        return {
          code: emp.code,
          name: emp.name,
          department: emp.department,
          totalInDays,
          sundaysWithIn,
          matchedInMaster,
        };
      });
      
      setProcessingProgress(100);
      setPreviewData(preview);
      setMatchStatus({
        inAttendanceNotInMaster,
        inMasterNotInAttendance,
        matchedCount: parsed.employees.length - inAttendanceNotInMaster.length,
      });
      setAttendanceData(parsed);
      setManualHolidays([]); // Reset holidays for new file
      
      toast.success(`Parsed ${parsed.totalEmployees} employees for ${parsed.daysInMonth} days`);
    } catch (error) {
      toast.error(`Failed to parse file: ${error.message}`);
      console.error('Parse error:', error);
    } finally {
      setIsProcessing(false);
      setProcessingProgress(0);
    }
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    processFile(file);
  }, [employees]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    processFile(file);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleProceed = () => {
    // Apply manual holidays and correct days in month before proceeding
    const updatedEmployees = (attendanceData?.employees || []).map(emp => ({
      ...emp,
      dailyData: emp.dailyData.map(day => {
        if (manualHolidays.includes(day.day)) {
          return {
            ...day,
            isHoliday: true,
            status: 'HL',
          };
        }
        return day;
      }),
    }));
    
    setAttendanceData({
      ...attendanceData,
      employees: updatedEmployees,
      manualHolidays: manualHolidays,
      daysInMonth: correctDaysInMonth, // Use selected month's correct days
      selectedMonth: selectedMonth,
      selectedYear: selectedYear,
    });
    
    setCurrentStep(3);
    navigate('/configuration');
  };

  const handleReset = () => {
    setPreviewData(null);
    setMatchStatus(null);
    setAttendanceData(null);
    setManualHolidays([]);
  };

  // Holiday management functions
  const toggleHoliday = (dayNum) => {
    setManualHolidays(prev => {
      if (prev.includes(dayNum)) {
        return prev.filter(d => d !== dayNum);
      } else {
        return [...prev, dayNum].sort((a, b) => a - b);
      }
    });
  };

  const applyHolidays = () => {
    if (!attendanceData) return;
    
    const updatedEmployees = attendanceData.employees.map(emp => ({
      ...emp,
      dailyData: emp.dailyData.map(day => {
        if (manualHolidays.includes(day.day)) {
          return {
            ...day,
            isHoliday: true,
            status: 'HL',
          };
        } else {
          // Remove holiday status if previously marked but now unchecked
          if (day.status === 'HL' && attendanceData.manualHolidays?.includes(day.day)) {
            return {
              ...day,
              isHoliday: false,
              status: '',
            };
          }
        }
        return day;
      }),
    }));
    
    setAttendanceData({
      ...attendanceData,
      employees: updatedEmployees,
      manualHolidays: manualHolidays,
    });
    
    setIsHolidayModalOpen(false);
    toast.success(`${manualHolidays.length} holidays marked successfully`);
  };

  // Edit attendance functions
  const openEditModal = (emp) => {
    const attendanceEmp = attendanceData.employees.find(
      e => normalizeEmpCode(e.code) === normalizeEmpCode(emp.code)
    );
    if (attendanceEmp) {
      setSelectedEmployee(attendanceEmp);
      setEditingAttendance([...attendanceEmp.dailyData]);
      setIsEditModalOpen(true);
    }
  };

  const updateDayAttendance = (dayIndex, field, value) => {
    setEditingAttendance(prev => {
      const updated = [...prev];
      updated[dayIndex] = {
        ...updated[dayIndex],
        [field]: value,
        hasIn: field === 'inTime' ? (value && value !== '--:--' && value !== '') : updated[dayIndex].hasIn,
        hasOut: field === 'outTime' ? (value && value !== '--:--' && value !== '') : updated[dayIndex].hasOut,
      };
      return updated;
    });
  };

  const saveAttendanceEdits = () => {
    if (!selectedEmployee || !attendanceData) return;
    
    const updatedEmployees = attendanceData.employees.map(emp => {
      if (normalizeEmpCode(emp.code) === normalizeEmpCode(selectedEmployee.code)) {
        return {
          ...emp,
          dailyData: editingAttendance,
        };
      }
      return emp;
    });
    
    setAttendanceData({
      ...attendanceData,
      employees: updatedEmployees,
    });
    
    // Update preview
    const updatedPreview = previewData.map(p => {
      if (normalizeEmpCode(p.code) === normalizeEmpCode(selectedEmployee.code)) {
        const totalInDays = editingAttendance.filter(d => d.hasIn || (d.inTime && d.inTime !== '--:--')).length;
        const sundaysWithIn = editingAttendance.filter(d => d.isSunday && (d.hasIn || (d.inTime && d.inTime !== '--:--'))).length;
        return { ...p, totalInDays, sundaysWithIn };
      }
      return p;
    });
    setPreviewData(updatedPreview);
    
    toast.success(`Attendance updated for ${selectedEmployee.name}`);
    setIsEditModalOpen(false);
  };

  // Filter employees for search
  const filteredPreview = useMemo(() => {
    if (!previewData) return [];
    if (!searchQuery) return previewData;
    return previewData.filter(emp =>
      emp.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      String(emp.code).includes(searchQuery)
    );
  }, [previewData, searchQuery]);

  // Generate days array for holiday selection
  const daysArray = useMemo(() => {
    if (!attendanceData) return [];
    const days = [];
    for (let i = 1; i <= attendanceData.daysInMonth; i++) {
      const dayData = attendanceData.employees[0]?.dailyData.find(d => d.day === i);
      days.push({
        day: i,
        dayName: dayData?.dayName || '',
        isSunday: dayData?.isSunday || false,
        existingHoliday: dayData?.status === 'HL' && !attendanceData.manualHolidays?.includes(i),
      });
    }
    return days;
  }, [attendanceData]);

  return (
    <div className="space-y-6" data-testid="attendance-upload-page">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold tracking-tight font-[Manrope]">{t('attendance')}</h1>
        <p className="text-muted-foreground mt-1">Upload monthly attendance file from biometric machine</p>
      </div>

      {/* Employee Master Warning */}
      {employees.length === 0 && (
        <Alert variant="destructive" data-testid="no-employees-warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>No Employee Master Data</AlertTitle>
          <AlertDescription>
            Please add employees to the master list first before uploading attendance.
            <Button 
              variant="link" 
              className="px-2 h-auto"
              onClick={() => navigate('/employees')}
              data-testid="go-to-employees-link"
            >
              Go to Employees
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Upload Zone */}
      {!previewData ? (
        <Card data-testid="upload-zone-card">
          <CardContent className="p-8">
            <div
              className={`
                border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
                transition-all duration-200
                ${isDragging 
                  ? 'border-primary bg-primary/5 scale-[1.02]' 
                  : 'border-border hover:border-primary/50 hover:bg-secondary/50'
                }
                ${isProcessing ? 'pointer-events-none opacity-50' : ''}
              `}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => !isProcessing && fileInputRef.current?.click()}
              data-testid="upload-dropzone"
            >
              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept=".xlsx,.xls"
                onChange={handleFileSelect}
              />
              
              {isProcessing ? (
                <div className="space-y-4">
                  <RefreshCw className="w-16 h-16 mx-auto text-primary animate-spin" />
                  <p className="text-lg font-medium">Processing file...</p>
                  <Progress value={processingProgress} className="w-64 mx-auto" />
                </div>
              ) : (
                <>
                  <Upload className={`w-16 h-16 mx-auto mb-4 ${isDragging ? 'text-primary' : 'text-muted-foreground'}`} />
                  <p className="text-lg font-medium mb-2">{t('dragDrop')}</p>
                  <p className="text-sm text-muted-foreground mb-4">
                    Supports .xlsx and .xls files
                  </p>
                  <Button variant="outline" className="gap-2" data-testid="browse-files-btn">
                    <FileSpreadsheet className="w-4 h-4" />
                    Browse Files
                  </Button>
                </>
              )}
            </div>

            {/* File Format Info */}
            <div className="mt-6 p-4 bg-secondary/50 rounded-lg">
              <h3 className="font-medium mb-2">Expected File Format:</h3>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Each employee occupies 10 rows in the file</li>
                <li>• Row 0: Department header | Row 1: Employee code & name</li>
                <li>• Row 2-3: Dates and day names | Row 4-5: IN/OUT times</li>
                <li>• Row 6-8: Work hours, Break time, OT | Row 9: Status (P/A/WO/HL)</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Preview Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card data-testid="employees-detected-card">
              <CardContent className="p-6 flex items-center gap-4">
                <div className="p-3 bg-blue-500/10 rounded-xl">
                  <Users className="w-8 h-8 text-blue-500" />
                </div>
                <div>
                  <p className="text-3xl font-bold font-[JetBrains_Mono]">{attendanceData?.totalEmployees}</p>
                  <p className="text-sm text-muted-foreground">Employees Detected</p>
                </div>
              </CardContent>
            </Card>
            <Card data-testid="days-detected-card">
              <CardContent className="p-6 flex items-center gap-4">
                <div className="p-3 bg-green-500/10 rounded-xl">
                  <Calendar className="w-8 h-8 text-green-500" />
                </div>
                <div>
                  <p className="text-3xl font-bold font-[JetBrains_Mono]">{attendanceData?.daysInMonth}</p>
                  <p className="text-sm text-muted-foreground">Days in Month</p>
                </div>
              </CardContent>
            </Card>
            <Card data-testid="matched-employees-card">
              <CardContent className="p-6 flex items-center gap-4">
                <div className="p-3 bg-purple-500/10 rounded-xl">
                  <CheckCircle2 className="w-8 h-8 text-purple-500" />
                </div>
                <div>
                  <p className="text-3xl font-bold font-[JetBrains_Mono]">{matchStatus?.matchedCount}</p>
                  <p className="text-sm text-muted-foreground">Matched with Master</p>
                </div>
              </CardContent>
            </Card>
            <Card data-testid="holidays-card" className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => setIsHolidayModalOpen(true)}>
              <CardContent className="p-6 flex items-center gap-4">
                <div className="p-3 bg-cyan-500/10 rounded-xl">
                  <CalendarDays className="w-8 h-8 text-cyan-500" />
                </div>
                <div>
                  <p className="text-3xl font-bold font-[JetBrains_Mono]">{manualHolidays.length}</p>
                  <p className="text-sm text-muted-foreground">Holidays Marked</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Holiday Management Card */}
          <Card className="border-cyan-500/30 bg-cyan-500/5" data-testid="holiday-management-card">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center justify-between text-lg">
                <div className="flex items-center gap-2">
                  <CalendarDays className="w-5 h-5 text-cyan-500" />
                  Holiday Management
                </div>
                <Button 
                  onClick={() => setIsHolidayModalOpen(true)} 
                  className="gap-2"
                  data-testid="manage-holidays-btn"
                >
                  <Plus className="w-4 h-4" />
                  Mark Holidays
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {manualHolidays.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {manualHolidays.map(day => {
                    const dayData = daysArray.find(d => d.day === day);
                    return (
                      <Badge 
                        key={day} 
                        className="bg-cyan-500/20 text-cyan-700 border-cyan-500/30 px-3 py-1"
                      >
                        {day} ({dayData?.dayName || ''})
                      </Badge>
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  कोई holiday mark नहीं है। अगर इस month में कोई छुट्टी है (जैसे 26 Jan), तो "Mark Holidays" button पर click करके mark करें।
                </p>
              )}
            </CardContent>
          </Card>

          {/* Warnings */}
          {matchStatus?.inAttendanceNotInMaster.length > 0 && (
            <Alert variant="destructive" data-testid="unmatched-in-attendance-alert">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Employees in Attendance but NOT in Master</AlertTitle>
              <AlertDescription>
                <div className="flex flex-wrap gap-2 mt-2">
                  {matchStatus.inAttendanceNotInMaster.map((emp, i) => (
                    <Badge key={i} variant="destructive">
                      {emp.code}: {emp.name}
                    </Badge>
                  ))}
                </div>
                <p className="mt-2 text-sm">These employees will be skipped during salary calculation.</p>
              </AlertDescription>
            </Alert>
          )}

          {matchStatus?.inMasterNotInAttendance.length > 0 && (
            <Alert data-testid="missing-from-attendance-alert">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Employees in Master but NOT in Attendance</AlertTitle>
              <AlertDescription>
                <div className="flex flex-wrap gap-2 mt-2">
                  {matchStatus.inMasterNotInAttendance.slice(0, 10).map((emp, i) => (
                    <Badge key={i} variant="secondary">
                      {emp.code}: {emp.name}
                    </Badge>
                  ))}
                  {matchStatus.inMasterNotInAttendance.length > 10 && (
                    <Badge variant="secondary">
                      +{matchStatus.inMasterNotInAttendance.length - 10} more
                    </Badge>
                  )}
                </div>
              </AlertDescription>
            </Alert>
          )}

          {/* Preview Table with Search and Edit */}
          <Card data-testid="attendance-preview-card">
            <CardHeader>
              <CardTitle className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <span>Attendance Preview</span>
                <div className="flex flex-wrap gap-2">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      placeholder="Search employee..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10 w-48"
                      data-testid="attendance-search-input"
                    />
                  </div>
                  <Button variant="outline" onClick={handleReset} className="gap-2" data-testid="upload-new-file-btn">
                    <RefreshCw className="w-4 h-4" />
                    Upload New File
                  </Button>
                  <Button 
                    onClick={handleProceed} 
                    className="gap-2"
                    disabled={matchStatus?.matchedCount === 0}
                    data-testid="proceed-to-config-btn"
                  >
                    Proceed to Configuration
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto max-h-96">
                <Table>
                  <TableHeader className="sticky top-0 bg-card">
                    <TableRow>
                      <TableHead>Emp Code</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Department</TableHead>
                      <TableHead className="text-center">Days with IN</TableHead>
                      <TableHead className="text-center">Sundays with IN</TableHead>
                      <TableHead className="text-center">In Master</TableHead>
                      <TableHead className="text-center">Edit</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredPreview.map((emp, index) => (
                      <TableRow key={index} data-testid={`preview-row-${emp.code}`}>
                        <TableCell className="font-mono">{emp.code}</TableCell>
                        <TableCell className="font-medium">{emp.name}</TableCell>
                        <TableCell>{emp.department || '-'}</TableCell>
                        <TableCell className="text-center">
                          <Badge variant="outline" className="font-mono">
                            {emp.totalInDays}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge 
                            variant={emp.sundaysWithIn > 0 ? 'default' : 'secondary'}
                            className="font-mono"
                          >
                            {emp.sundaysWithIn}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-center">
                          {emp.matchedInMaster ? (
                            <CheckCircle2 className="w-5 h-5 text-green-500 mx-auto" />
                          ) : (
                            <AlertTriangle className="w-5 h-5 text-red-500 mx-auto" />
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openEditModal(emp)}
                            data-testid={`edit-attendance-${emp.code}`}
                          >
                            <Pencil className="w-4 h-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* Holiday Selection Modal */}
      <Dialog open={isHolidayModalOpen} onOpenChange={setIsHolidayModalOpen}>
        <DialogContent className="max-w-2xl" data-testid="holiday-modal">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CalendarDays className="w-5 h-5 text-cyan-500" />
              Mark Holidays for This Month
            </DialogTitle>
          </DialogHeader>
          
          <div className="py-4">
            <p className="text-sm text-muted-foreground mb-4">
              इस month में जो भी holidays हैं (जैसे 26 Jan - Republic Day), उन्हें select करें। 
              Selected dates पर जो employees नहीं आए, उन्हें paid holiday मिलेगा।
            </p>
            
            <ScrollArea className="h-[400px] pr-4">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {daysArray.map(({ day, dayName, isSunday, existingHoliday }) => (
                  <div
                    key={day}
                    className={`
                      flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all
                      ${manualHolidays.includes(day) 
                        ? 'border-cyan-500 bg-cyan-500/10' 
                        : existingHoliday
                          ? 'border-green-500 bg-green-500/10'
                          : isSunday 
                            ? 'border-blue-500/30 bg-blue-500/5' 
                            : 'border-border hover:border-cyan-500/50'
                      }
                    `}
                    onClick={() => !existingHoliday && toggleHoliday(day)}
                    data-testid={`holiday-day-${day}`}
                  >
                    <Checkbox
                      checked={manualHolidays.includes(day) || existingHoliday}
                      disabled={existingHoliday}
                      onCheckedChange={() => !existingHoliday && toggleHoliday(day)}
                    />
                    <div className="flex-1">
                      <p className={`font-mono font-bold ${isSunday ? 'text-blue-500' : ''}`}>
                        {day}
                      </p>
                      <p className={`text-xs ${isSunday ? 'text-blue-500' : 'text-muted-foreground'}`}>
                        {dayName}
                        {isSunday && ' (Week Off)'}
                        {existingHoliday && ' (Sheet HL)'}
                      </p>
                    </div>
                    {manualHolidays.includes(day) && (
                      <Badge className="bg-cyan-500 text-white text-xs">HL</Badge>
                    )}
                    {existingHoliday && (
                      <Badge className="bg-green-500 text-white text-xs">Sheet</Badge>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
            
            {manualHolidays.length > 0 && (
              <div className="mt-4 p-3 bg-cyan-500/10 rounded-lg">
                <p className="text-sm font-medium">
                  Selected Holidays: {manualHolidays.map(d => {
                    const dayData = daysArray.find(dd => dd.day === d);
                    return `${d} (${dayData?.dayName})`;
                  }).join(', ')}
                </p>
              </div>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsHolidayModalOpen(false)} data-testid="cancel-holiday">
              <X className="w-4 h-4 mr-2" />
              Cancel
            </Button>
            <Button onClick={applyHolidays} className="bg-cyan-600 hover:bg-cyan-700" data-testid="apply-holidays">
              <Save className="w-4 h-4 mr-2" />
              Apply Holidays ({manualHolidays.length})
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Attendance Modal */}
      <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh]" data-testid="edit-attendance-modal">
          <DialogHeader>
            <DialogTitle>
              Edit Attendance - {selectedEmployee?.name} (Code: {selectedEmployee?.code})
            </DialogTitle>
          </DialogHeader>
          
          <ScrollArea className="h-[500px] pr-4">
            <Table>
              <TableHeader className="sticky top-0 bg-card">
                <TableRow>
                  <TableHead className="w-12">Day</TableHead>
                  <TableHead className="w-16">Name</TableHead>
                  <TableHead className="w-28">IN Time</TableHead>
                  <TableHead className="w-28">OUT Time</TableHead>
                  <TableHead className="w-28">Work Hours</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {editingAttendance.map((day, index) => (
                  <TableRow 
                    key={index} 
                    className={`
                      ${day.isSunday ? 'bg-blue-500/5' : ''}
                      ${day.isHoliday || manualHolidays.includes(day.day) ? 'bg-cyan-500/5' : ''}
                    `}
                  >
                    <TableCell className="font-mono font-bold">{day.day}</TableCell>
                    <TableCell className={`text-sm ${day.isSunday ? 'text-blue-500 font-medium' : 'text-muted-foreground'}`}>
                      {day.dayName}
                    </TableCell>
                    <TableCell>
                      <Input
                        type="time"
                        value={day.inTime !== '--:--' ? day.inTime : ''}
                        onChange={(e) => updateDayAttendance(index, 'inTime', e.target.value || '--:--')}
                        className="h-8 text-sm"
                        data-testid={`edit-in-time-${day.day}`}
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="time"
                        value={day.outTime !== '--:--' ? day.outTime : ''}
                        onChange={(e) => updateDayAttendance(index, 'outTime', e.target.value || '--:--')}
                        className="h-8 text-sm"
                        data-testid={`edit-out-time-${day.day}`}
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="text"
                        value={day.workHours}
                        onChange={(e) => updateDayAttendance(index, 'workHours', e.target.value)}
                        placeholder="HH:MM"
                        className="h-8 text-sm font-mono"
                        data-testid={`edit-work-hours-${day.day}`}
                      />
                    </TableCell>
                    <TableCell>
                      <Badge 
                        variant={day.isHoliday || manualHolidays.includes(day.day) ? 'default' : 'secondary'}
                        className={day.isHoliday || manualHolidays.includes(day.day) ? 'bg-cyan-500/20 text-cyan-600' : ''}
                      >
                        {manualHolidays.includes(day.day) ? 'HL' : day.status || (day.isSunday ? 'SUN' : '-')}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </ScrollArea>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditModalOpen(false)} data-testid="cancel-edit-attendance">
              <X className="w-4 h-4 mr-2" />
              Cancel
            </Button>
            <Button onClick={saveAttendanceEdits} data-testid="save-edit-attendance">
              <Save className="w-4 h-4 mr-2" />
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
