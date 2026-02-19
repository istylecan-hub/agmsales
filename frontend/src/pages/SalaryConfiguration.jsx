import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { calculateSalaries } from '../utils/salaryCalculator';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Separator } from '../components/ui/separator';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';
import {
  Calculator,
  Clock,
  Calendar,
  AlertTriangle,
  ArrowRight,
  Settings,
  RefreshCw,
} from 'lucide-react';

export default function SalaryConfiguration() {
  const navigate = useNavigate();
  const { 
    t, 
    config, 
    setConfig, 
    employees, 
    attendanceData, 
    setCalculationResults,
    setCurrentStep,
    isLoading,
    setIsLoading,
  } = useApp();

  const updateConfig = (key, value) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const handleCalculate = async () => {
    if (!attendanceData) {
      toast.error('Please upload attendance data first');
      navigate('/attendance');
      return;
    }

    if (employees.length === 0) {
      toast.error('Please add employees first');
      navigate('/employees');
      return;
    }

    setIsLoading(true);

    try {
      // Simulate async processing
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const results = calculateSalaries(
        attendanceData,
        employees,
        config,
        attendanceData.daysInMonth
      );

      setCalculationResults(results);
      setCurrentStep(4);
      toast.success(`Calculated salary for ${results.results.length} employees`);
      navigate('/reports');
    } catch (error) {
      toast.error(`Calculation failed: ${error.message}`);
      console.error('Calculation error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const resetToDefaults = () => {
    setConfig({
      useInOutForAttendance: true,
      weekdayStandardHours: 9,
      sundayStandardHours: 8,
      enableOvertime: true,
      useSheetOT: true,
      otGraceMinutes: 15,
      otConversionBase: 9,
      enableHalfDay: true,
      weekdayHalfDayThreshold: 4.5,
      sundayHalfDayThreshold: 4,
      countSundayAsExtraDay: true,
      sundayMissingOutPunch: 'full',
      holidayNotWorkedIsPaid: true,
      holidayWorkedIsExtraDay: true,
      weekOffIsPaid: true,
      enableSandwich: true,
      applySandwichToWO: true,
      applySandwichToHL: true,
      zeroAttendanceZeroSalary: true,
      weekdayMissingOutPunch: 'full',
      enableShortHoursDeduction: true,
      shortHoursConversionBase: 9,
    });
    toast.success('Configuration reset to defaults');
  };

  return (
    <div className="space-y-6" data-testid="salary-configuration-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight font-[Manrope]">{t('configuration')}</h1>
          <p className="text-muted-foreground mt-1">Configure salary calculation rules</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={resetToDefaults} className="gap-2" data-testid="reset-config-btn">
            <RefreshCw className="w-4 h-4" />
            Reset Defaults
          </Button>
          <Button 
            onClick={handleCalculate} 
            className="gap-2"
            disabled={!attendanceData || employees.length === 0 || isLoading}
            data-testid="calculate-salary-btn"
          >
            {isLoading ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Calculator className="w-4 h-4" />
            )}
            {t('calculate')}
          </Button>
        </div>
      </div>

      {/* Warning if no attendance */}
      {!attendanceData && (
        <Alert variant="destructive" data-testid="no-attendance-warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>No Attendance Data</AlertTitle>
          <AlertDescription>
            Please upload attendance data before configuring salary rules.
            <Button 
              variant="link" 
              className="px-2 h-auto"
              onClick={() => navigate('/attendance')}
            >
              Go to Attendance Upload
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Configuration Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 3A. Attendance Detection */}
        <Card data-testid="config-attendance-detection">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Settings className="w-5 h-5" />
              3A. Attendance Detection
            </CardTitle>
            <CardDescription>How to determine if employee was present</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="useInOut" className="flex-1">
                Use IN/OUT time to determine attendance
                <span className="block text-xs text-muted-foreground mt-1">
                  If IN time exists → employee came that day
                </span>
              </Label>
              <Switch
                id="useInOut"
                checked={config.useInOutForAttendance}
                onCheckedChange={(v) => updateConfig('useInOutForAttendance', v)}
                data-testid="use-in-out-switch"
              />
            </div>
          </CardContent>
        </Card>

        {/* 3B. Working Hours Standard */}
        <Card data-testid="config-working-hours">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Clock className="w-5 h-5" />
              3B. Working Hours Standard
            </CardTitle>
            <CardDescription>Standard working hours per day</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="weekdayHours">Weekday Standard (hours)</Label>
                <Input
                  id="weekdayHours"
                  type="number"
                  value={config.weekdayStandardHours}
                  onChange={(e) => updateConfig('weekdayStandardHours', parseFloat(e.target.value) || 9)}
                  min="1"
                  max="24"
                  data-testid="weekday-hours-input"
                />
              </div>
              <div>
                <Label htmlFor="sundayHours">Sunday Standard (hours)</Label>
                <Input
                  id="sundayHours"
                  type="number"
                  value={config.sundayStandardHours}
                  onChange={(e) => updateConfig('sundayStandardHours', parseFloat(e.target.value) || 8)}
                  min="1"
                  max="24"
                  data-testid="sunday-hours-input"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 3C. Overtime Rules */}
        <Card data-testid="config-overtime">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Clock className="w-5 h-5 text-orange-500" />
              3C. Overtime Rules
            </CardTitle>
            <CardDescription>Configure overtime calculation</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="enableOT">Enable Overtime Calculation</Label>
              <Switch
                id="enableOT"
                checked={config.enableOvertime}
                onCheckedChange={(v) => updateConfig('enableOvertime', v)}
                data-testid="enable-ot-switch"
              />
            </div>
            {config.enableOvertime && (
              <>
                <Separator />
                <div>
                  <Label htmlFor="otConversion">OT to Days Conversion Base (hours)</Label>
                  <Input
                    id="otConversion"
                    type="number"
                    value={config.otConversionBase}
                    onChange={(e) => updateConfig('otConversionBase', parseFloat(e.target.value) || 9)}
                    min="1"
                    max="24"
                    data-testid="ot-conversion-input"
                  />
                  <p className="text-xs text-muted-foreground mt-1">Net OT hours ÷ {config.otConversionBase} = OT days</p>
                </div>
                <p className="text-xs text-green-600 bg-green-500/10 p-2 rounded">
                  ✓ OT = (Work Hours - Standard Hours). Weekday: 9 hrs standard, Sunday: 8 hrs standard.
                  <br />
                  ✓ Net OT = OT Hours - Short Hours. फिर OT Days में convert होगा।
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* 3D. Half Day Rule */}
        <Card data-testid="config-half-day">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Calendar className="w-5 h-5" />
              3D. Half Day Rule
            </CardTitle>
            <CardDescription>When to mark as half day</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="enableHalfDay">Enable Half Day Detection</Label>
              <Switch
                id="enableHalfDay"
                checked={config.enableHalfDay}
                onCheckedChange={(v) => updateConfig('enableHalfDay', v)}
                data-testid="enable-half-day-switch"
              />
            </div>
            {config.enableHalfDay && (
              <>
                <Separator />
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="weekdayHalfThreshold">Weekday Threshold (hours)</Label>
                    <Input
                      id="weekdayHalfThreshold"
                      type="number"
                      step="0.5"
                      value={config.weekdayHalfDayThreshold}
                      onChange={(e) => updateConfig('weekdayHalfDayThreshold', parseFloat(e.target.value) || 4.5)}
                      min="1"
                      max="12"
                      data-testid="weekday-half-threshold-input"
                    />
                    <p className="text-xs text-muted-foreground mt-1">Below this = 0.5 day</p>
                  </div>
                  <div>
                    <Label htmlFor="sundayHalfThreshold">Sunday Threshold (hours)</Label>
                    <Input
                      id="sundayHalfThreshold"
                      type="number"
                      step="0.5"
                      value={config.sundayHalfDayThreshold}
                      onChange={(e) => updateConfig('sundayHalfDayThreshold', parseFloat(e.target.value) || 4)}
                      min="1"
                      max="12"
                      data-testid="sunday-half-threshold-input"
                    />
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* 3E. Sunday Working */}
        <Card data-testid="config-sunday-working">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Calendar className="w-5 h-5 text-blue-500" />
              3E. Sunday Working
            </CardTitle>
            <CardDescription>How to handle Sunday attendance</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="sundayExtra">Sunday with IN = Extra Working Day</Label>
              <Switch
                id="sundayExtra"
                checked={config.countSundayAsExtraDay}
                onCheckedChange={(v) => updateConfig('countSundayAsExtraDay', v)}
                data-testid="sunday-extra-switch"
              />
            </div>
            <Separator />
            <div>
              <Label>If Sunday has IN but no OUT</Label>
              <Select
                value={config.sundayMissingOutPunch}
                onValueChange={(v) => updateConfig('sundayMissingOutPunch', v)}
              >
                <SelectTrigger className="mt-2" data-testid="sunday-missing-out-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="full">Count as 1 full day</SelectItem>
                  <SelectItem value="half">Count as 0.5 day</SelectItem>
                  <SelectItem value="none">Don't count</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* 3F. Holiday Rules */}
        <Card data-testid="config-holiday-rules">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Calendar className="w-5 h-5 text-green-500" />
              3F. Holiday Rules
            </CardTitle>
            <CardDescription>How to handle holidays (HL status)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="hlNotWorkedPaid">
                HL not worked = Paid holiday
                <span className="block text-xs text-muted-foreground">Subject to sandwich rule</span>
              </Label>
              <Switch
                id="hlNotWorkedPaid"
                checked={config.holidayNotWorkedIsPaid}
                onCheckedChange={(v) => updateConfig('holidayNotWorkedIsPaid', v)}
                data-testid="hl-not-worked-paid-switch"
              />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <Label htmlFor="hlWorkedExtra">
                HL worked (has IN) = Extra working day
                <span className="block text-xs text-muted-foreground">Treated like Sunday worked</span>
              </Label>
              <Switch
                id="hlWorkedExtra"
                checked={config.holidayWorkedIsExtraDay}
                onCheckedChange={(v) => updateConfig('holidayWorkedIsExtraDay', v)}
                data-testid="hl-worked-extra-switch"
              />
            </div>
          </CardContent>
        </Card>

        {/* 3H. Sandwich Rule */}
        <Card data-testid="config-sandwich-rule">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <AlertTriangle className="w-5 h-5 text-yellow-500" />
              3H. Sandwich Rule
            </CardTitle>
            <CardDescription>Deduct WO/HL if surrounded by absents</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="enableSandwich">Enable Sandwich Deduction</Label>
              <Switch
                id="enableSandwich"
                checked={config.enableSandwich}
                onCheckedChange={(v) => updateConfig('enableSandwich', v)}
                data-testid="enable-sandwich-switch"
              />
            </div>
            {config.enableSandwich && (
              <>
                <Separator />
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="sandwichWO">Apply to Week Off (WO)</Label>
                    <Switch
                      id="sandwichWO"
                      checked={config.applySandwichToWO}
                      onCheckedChange={(v) => updateConfig('applySandwichToWO', v)}
                      data-testid="sandwich-wo-switch"
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="sandwichHL">Apply to Holidays (HL)</Label>
                    <Switch
                      id="sandwichHL"
                      checked={config.applySandwichToHL}
                      onCheckedChange={(v) => updateConfig('applySandwichToHL', v)}
                      data-testid="sandwich-hl-switch"
                    />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground bg-secondary/50 p-2 rounded">
                  A WO/HL day is NOT paid if both nearest working days on either side are Absent (extended sandwich rule)
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* 3I. Zero Attendance & 3K Missing Punch */}
        <Card data-testid="config-other-rules">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Settings className="w-5 h-5" />
              3I/3K. Other Rules
            </CardTitle>
            <CardDescription>Zero attendance and missing punch handling</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="zeroAttendance">
                Zero Attendance = Zero Salary
                <span className="block text-xs text-muted-foreground">If 0 days with IN → Salary = 0</span>
              </Label>
              <Switch
                id="zeroAttendance"
                checked={config.zeroAttendanceZeroSalary}
                onCheckedChange={(v) => updateConfig('zeroAttendanceZeroSalary', v)}
                data-testid="zero-attendance-switch"
              />
            </div>
            <Separator />
            <div>
              <Label>Weekday: IN exists but no OUT punch</Label>
              <Select
                value={config.weekdayMissingOutPunch}
                onValueChange={(v) => updateConfig('weekdayMissingOutPunch', v)}
              >
                <SelectTrigger className="mt-2" data-testid="weekday-missing-punch-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="full">Count as 1 full day (0 OT)</SelectItem>
                  <SelectItem value="half">Count as 0.5 day</SelectItem>
                  <SelectItem value="absent">Mark as Absent</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* 3L. Short Hours Deduction */}
        <Card data-testid="config-short-hours">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Clock className="w-5 h-5 text-red-500" />
              3L. Short Hours Deduction
            </CardTitle>
            <CardDescription>Deduct for working less than standard hours</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="enableShortHours">
                Enable Short Hours Deduction
                <span className="block text-xs text-muted-foreground">Track hours worked below standard</span>
              </Label>
              <Switch
                id="enableShortHours"
                checked={config.enableShortHoursDeduction}
                onCheckedChange={(v) => updateConfig('enableShortHoursDeduction', v)}
                data-testid="enable-short-hours-switch"
              />
            </div>
            {config.enableShortHoursDeduction && (
              <>
                <Separator />
                <div>
                  <Label htmlFor="shortConversion">Short Hours to Days Conversion Base</Label>
                  <Input
                    id="shortConversion"
                    type="number"
                    value={config.shortHoursConversionBase}
                    onChange={(e) => updateConfig('shortHoursConversionBase', parseFloat(e.target.value) || 9)}
                    min="1"
                    max="24"
                    data-testid="short-hours-conversion-input"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Short hours ÷ {config.shortHoursConversionBase} = Deduction days
                  </p>
                </div>
                <p className="text-xs text-muted-foreground bg-red-500/10 p-2 rounded">
                  Example: If someone works 7 hours instead of 9 hours on 5 days = 10 short hours = {(10 / config.shortHoursConversionBase).toFixed(2)} day deduction
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Calculate Button (Bottom) */}
      <Card className="bg-primary/5 border-primary/20" data-testid="calculate-section">
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div>
              <h3 className="font-semibold text-lg">Ready to Calculate?</h3>
              <p className="text-sm text-muted-foreground">
                {attendanceData 
                  ? `${attendanceData.totalEmployees} employees detected for ${attendanceData.daysInMonth} days`
                  : 'Please upload attendance data first'
                }
              </p>
            </div>
            <Button 
              size="lg"
              onClick={handleCalculate}
              disabled={!attendanceData || employees.length === 0 || isLoading}
              className="gap-2 min-w-48"
              data-testid="calculate-salary-btn-bottom"
            >
              {isLoading ? (
                <RefreshCw className="w-5 h-5 animate-spin" />
              ) : (
                <Calculator className="w-5 h-5" />
              )}
              Calculate Salary
              <ArrowRight className="w-5 h-5" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
