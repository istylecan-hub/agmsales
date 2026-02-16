import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import {
  Users,
  IndianRupee,
  Clock,
  AlertCircle,
  ArrowRight,
  Upload,
  FileSpreadsheet,
  TrendingUp,
} from 'lucide-react';

export default function Dashboard() {
  const { t, employees, calculationResults, attendanceData } = useApp();
  const navigate = useNavigate();

  const stats = [
    {
      title: t('totalEmployees'),
      value: employees.length,
      icon: Users,
      color: 'text-blue-500',
      bgColor: 'bg-blue-500/10',
    },
    {
      title: t('totalSalary'),
      value: calculationResults?.summary?.totalSalary
        ? `₹${calculationResults.summary.totalSalary.toLocaleString('en-IN')}`
        : '₹0',
      icon: IndianRupee,
      color: 'text-green-500',
      bgColor: 'bg-green-500/10',
    },
    {
      title: t('totalOT'),
      value: calculationResults?.summary?.totalOT
        ? `₹${calculationResults.summary.totalOT.toLocaleString('en-IN')}`
        : '₹0',
      icon: Clock,
      color: 'text-orange-500',
      bgColor: 'bg-orange-500/10',
    },
    {
      title: t('zeroSalary'),
      value: calculationResults?.summary?.zeroSalaryCount ?? 0,
      icon: AlertCircle,
      color: 'text-red-500',
      bgColor: 'bg-red-500/10',
    },
  ];

  const wizardSteps = [
    {
      step: 1,
      title: 'Employee Master',
      description: 'Add or import employee data',
      icon: Users,
      path: '/employees',
      completed: employees.length > 0,
    },
    {
      step: 2,
      title: 'Upload Attendance',
      description: 'Upload monthly attendance file',
      icon: Upload,
      path: '/attendance',
      completed: !!attendanceData,
    },
    {
      step: 3,
      title: 'Configure Rules',
      description: 'Set salary calculation rules',
      icon: TrendingUp,
      path: '/configuration',
      completed: !!attendanceData,
    },
    {
      step: 4,
      title: 'View Reports',
      description: 'Download salary reports',
      icon: FileSpreadsheet,
      path: '/reports',
      completed: !!calculationResults,
    },
  ];

  const completedSteps = wizardSteps.filter(s => s.completed).length;
  const progress = (completedSteps / wizardSteps.length) * 100;

  return (
    <div className="space-y-8" data-testid="dashboard-page">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold tracking-tight font-[Manrope]">{t('dashboard')}</h1>
        <p className="text-muted-foreground mt-1">{t('subtitle')}</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <Card key={index} className="hover:-translate-y-0.5 hover:shadow-md transition-all duration-200" data-testid={`stat-card-${index}`}>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{stat.title}</p>
                    <p className="text-2xl font-bold font-[JetBrains_Mono] mt-1">{stat.value}</p>
                  </div>
                  <div className={`p-3 rounded-xl ${stat.bgColor}`}>
                    <Icon className={`w-6 h-6 ${stat.color}`} />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Progress Section */}
      <Card data-testid="progress-section">
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Salary Processing Progress</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-muted-foreground">Overall Progress</span>
              <span className="font-medium">{completedSteps} of {wizardSteps.length} steps</span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {wizardSteps.map((item) => {
              const Icon = item.icon;
              return (
                <div
                  key={item.step}
                  className={`
                    p-4 rounded-xl border-2 cursor-pointer transition-all duration-200
                    ${item.completed
                      ? 'border-green-500/50 bg-green-500/5'
                      : 'border-border hover:border-primary/50'
                    }
                  `}
                  onClick={() => navigate(item.path)}
                  data-testid={`wizard-step-${item.step}`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className={`
                      w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold
                      ${item.completed
                        ? 'bg-green-500 text-white'
                        : 'bg-secondary text-muted-foreground'
                      }
                    `}>
                      {item.step}
                    </div>
                    <Icon className={`w-5 h-5 ${item.completed ? 'text-green-500' : 'text-muted-foreground'}`} />
                  </div>
                  <h3 className="font-medium text-sm">{item.title}</h3>
                  <p className="text-xs text-muted-foreground mt-1">{item.description}</p>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="hover:shadow-md transition-all duration-200" data-testid="quick-action-employees">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-lg">Manage Employees</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Add, edit, or import employee master data
                </p>
              </div>
              <Button onClick={() => navigate('/employees')} className="gap-2" data-testid="go-to-employees-btn">
                Go to Employees
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-all duration-200" data-testid="quick-action-attendance">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-lg">Upload Attendance</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Upload monthly attendance Excel file
                </p>
              </div>
              <Button onClick={() => navigate('/attendance')} className="gap-2" data-testid="go-to-attendance-btn">
                Upload File
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Calculation Summary */}
      {calculationResults && (
        <Card data-testid="recent-calculation-summary">
          <CardHeader>
            <CardTitle className="text-lg font-semibold">Last Calculation Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-secondary/50 rounded-lg">
                <p className="text-2xl font-bold font-[JetBrains_Mono] text-green-500">
                  {calculationResults.summary.totalEmployees}
                </p>
                <p className="text-xs text-muted-foreground mt-1">Employees Processed</p>
              </div>
              <div className="text-center p-4 bg-secondary/50 rounded-lg">
                <p className="text-2xl font-bold font-[JetBrains_Mono]">
                  ₹{(calculationResults.summary.totalSalary - calculationResults.summary.totalOT).toLocaleString('en-IN')}
                </p>
                <p className="text-xs text-muted-foreground mt-1">Gross Salary</p>
              </div>
              <div className="text-center p-4 bg-secondary/50 rounded-lg">
                <p className="text-2xl font-bold font-[JetBrains_Mono] text-orange-500">
                  ₹{calculationResults.summary.totalOT.toLocaleString('en-IN')}
                </p>
                <p className="text-xs text-muted-foreground mt-1">Total OT</p>
              </div>
              <div className="text-center p-4 bg-secondary/50 rounded-lg">
                <p className="text-2xl font-bold font-[JetBrains_Mono] text-red-500">
                  {calculationResults.summary.zeroSalaryCount}
                </p>
                <p className="text-xs text-muted-foreground mt-1">Zero Salary</p>
              </div>
            </div>
            <div className="mt-4 flex justify-end">
              <Button variant="outline" onClick={() => navigate('/reports')} className="gap-2" data-testid="view-full-report-btn">
                View Full Report
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
