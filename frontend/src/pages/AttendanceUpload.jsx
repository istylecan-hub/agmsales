import React, { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { parseAttendanceExcel, normalizeEmpCode } from '../utils/excelParser';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
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
      
      // Match with employee master
      const employeeCodeSet = new Set(employees.map(e => normalizeEmpCode(e.code)));
      const attendanceCodeSet = new Set(parsed.employees.map(e => normalizeEmpCode(e.code)));
      
      const inAttendanceNotInMaster = parsed.employees
        .filter(e => !employeeCodeSet.has(normalizeEmpCode(e.code)))
        .map(e => ({ code: e.code, name: e.name }));
      
      const inMasterNotInAttendance = employees
        .filter(e => !attendanceCodeSet.has(normalizeEmpCode(e.code)))
        .map(e => ({ code: e.code, name: e.name }));
      
      // Calculate preview data for each employee
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
    setCurrentStep(3);
    navigate('/configuration');
  };

  const handleReset = () => {
    setPreviewData(null);
    setMatchStatus(null);
    setAttendanceData(null);
  };

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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
          </div>

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

          {/* Preview Table */}
          <Card data-testid="attendance-preview-card">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Attendance Preview</span>
                <div className="flex gap-2">
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
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {previewData.map((emp, index) => (
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
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
