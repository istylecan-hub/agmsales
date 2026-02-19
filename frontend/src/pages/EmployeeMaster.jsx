import React, { useState, useRef, useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { parseEmployeeMasterExcel, exportEmployeesToExcel, normalizeEmpCode } from '../utils/excelParser';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../components/ui/alert-dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import {
  Plus,
  Upload,
  Download,
  Search,
  Pencil,
  Trash2,
  Users,
  FileSpreadsheet,
} from 'lucide-react';

export default function EmployeeMaster() {
  const { t, employees, addEmployee, updateEmployee, deleteEmployee, importEmployees } = useApp();
  const fileInputRef = useRef(null);
  
  const [searchQuery, setSearchQuery] = useState('');
  const [filterDepartment, setFilterDepartment] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    department: '',
    salary: '',
    dateOfJoining: '',
    status: 'active',
    onlySundayNoOT: false, // Only Sunday pay, no OT for this employee
  });

  // Get unique departments
  const departments = useMemo(() => {
    const depts = new Set(employees.map(e => e.department).filter(Boolean));
    return Array.from(depts);
  }, [employees]);

  // Filter employees
  const filteredEmployees = useMemo(() => {
    return employees.filter(emp => {
      const matchesSearch = 
        emp.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        String(emp.code).includes(searchQuery);
      const matchesDept = filterDepartment === 'all' || emp.department === filterDepartment;
      const matchesStatus = filterStatus === 'all' || emp.status === filterStatus;
      return matchesSearch && matchesDept && matchesStatus;
    });
  }, [employees, searchQuery, filterDepartment, filterStatus]);

  const resetForm = () => {
    setFormData({
      code: '',
      name: '',
      department: '',
      salary: '',
      dateOfJoining: '',
      status: 'active',
      onlySundayNoOT: false,
    });
  };

  const handleAddEmployee = () => {
    if (!formData.code || !formData.name || !formData.salary) {
      toast.error('Please fill in required fields (Code, Name, Salary)');
      return;
    }

    const normalizedCode = normalizeEmpCode(formData.code);
    if (employees.some(e => normalizeEmpCode(e.code) === normalizedCode)) {
      toast.error('Employee with this code already exists');
      return;
    }

    addEmployee({
      ...formData,
      code: normalizedCode,
      salary: parseFloat(formData.salary),
      onlySundayNoOT: formData.onlySundayNoOT || false,
    });

    toast.success('Employee added successfully');
    setIsAddModalOpen(false);
    resetForm();
  };

  const handleEditEmployee = () => {
    if (!formData.name || !formData.salary) {
      toast.error('Please fill in required fields');
      return;
    }

    updateEmployee(selectedEmployee.code, {
      ...formData,
      salary: parseFloat(formData.salary),
      onlySundayNoOT: formData.onlySundayNoOT || false,
    });

    toast.success('Employee updated successfully');
    setIsEditModalOpen(false);
    resetForm();
  };

  const handleDeleteEmployee = () => {
    deleteEmployee(selectedEmployee.code);
    toast.success('Employee deleted successfully');
    setIsDeleteDialogOpen(false);
    setSelectedEmployee(null);
  };

  const openEditModal = (employee) => {
    setSelectedEmployee(employee);
    setFormData({
      code: employee.code,
      name: employee.name,
      department: employee.department || '',
      salary: String(employee.salary),
      dateOfJoining: employee.dateOfJoining || '',
      status: employee.status || 'active',
    });
    setIsEditModalOpen(true);
  };

  const openDeleteDialog = (employee) => {
    setSelectedEmployee(employee);
    setIsDeleteDialogOpen(true);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const importedEmployees = await parseEmployeeMasterExcel(file);
      importEmployees(importedEmployees);
      toast.success(`Imported ${importedEmployees.length} employees`);
    } catch (error) {
      toast.error(`Import failed: ${error.message}`);
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleExport = () => {
    if (employees.length === 0) {
      toast.error('No employees to export');
      return;
    }
    exportEmployeesToExcel(employees);
    toast.success('Employee master exported');
  };

  return (
    <div className="space-y-6" data-testid="employee-master-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight font-[Manrope]">{t('employees')}</h1>
          <p className="text-muted-foreground mt-1">Manage employee master data</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => { resetForm(); setIsAddModalOpen(true); }} className="gap-2" data-testid="add-employee-btn">
            <Plus className="w-4 h-4" />
            {t('addEmployee')}
          </Button>
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            accept=".xlsx,.xls"
            onChange={handleFileUpload}
          />
          <Button variant="outline" onClick={() => fileInputRef.current?.click()} className="gap-2" data-testid="import-excel-btn">
            <Upload className="w-4 h-4" />
            {t('importExcel')}
          </Button>
          <Button variant="outline" onClick={handleExport} className="gap-2" data-testid="export-excel-btn">
            <Download className="w-4 h-4" />
            {t('exportExcel')}
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <Users className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <p className="text-2xl font-bold font-[JetBrains_Mono]">{employees.length}</p>
              <p className="text-xs text-muted-foreground">Total Employees</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-green-500/10 rounded-lg">
              <Users className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <p className="text-2xl font-bold font-[JetBrains_Mono]">
                {employees.filter(e => e.status === 'active').length}
              </p>
              <p className="text-xs text-muted-foreground">Active</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-orange-500/10 rounded-lg">
              <FileSpreadsheet className="w-5 h-5 text-orange-500" />
            </div>
            <div>
              <p className="text-2xl font-bold font-[JetBrains_Mono]">{departments.length}</p>
              <p className="text-xs text-muted-foreground">Departments</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-purple-500/10 rounded-lg">
              <Users className="w-5 h-5 text-purple-500" />
            </div>
            <div>
              <p className="text-2xl font-bold font-[JetBrains_Mono]">
                {employees.filter(e => e.status === 'inactive').length}
              </p>
              <p className="text-xs text-muted-foreground">Inactive</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder={t('search')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
                data-testid="employee-search-input"
              />
            </div>
            <Select value={filterDepartment} onValueChange={setFilterDepartment}>
              <SelectTrigger className="w-full md:w-48" data-testid="department-filter">
                <SelectValue placeholder="Department" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Departments</SelectItem>
                {departments.map(dept => (
                  <SelectItem key={dept} value={dept}>{dept}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-full md:w-36" data-testid="status-filter">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Employee Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-20">{t('employeeCode')}</TableHead>
                  <TableHead>{t('employeeName')}</TableHead>
                  <TableHead>{t('department')}</TableHead>
                  <TableHead className="text-right">{t('monthlySalary')}</TableHead>
                  <TableHead>{t('dateOfJoining')}</TableHead>
                  <TableHead>{t('status')}</TableHead>
                  <TableHead className="text-right">{t('actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredEmployees.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                      {employees.length === 0 
                        ? 'No employees yet. Add or import employees to get started.'
                        : 'No employees match your filters.'
                      }
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredEmployees.map((emp) => (
                    <TableRow key={emp.code} data-testid={`employee-row-${emp.code}`}>
                      <TableCell className="font-mono font-medium">{emp.code}</TableCell>
                      <TableCell className="font-medium">{emp.name}</TableCell>
                      <TableCell>{emp.department || '-'}</TableCell>
                      <TableCell className="text-right font-mono">
                        ₹{emp.salary.toLocaleString('en-IN')}
                      </TableCell>
                      <TableCell>{emp.dateOfJoining || '-'}</TableCell>
                      <TableCell>
                        <Badge variant={emp.status === 'active' ? 'default' : 'secondary'}>
                          {emp.status || 'active'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openEditModal(emp)}
                            data-testid={`edit-employee-${emp.code}`}
                          >
                            <Pencil className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openDeleteDialog(emp)}
                            className="text-destructive hover:text-destructive"
                            data-testid={`delete-employee-${emp.code}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Add Employee Modal */}
      <Dialog open={isAddModalOpen} onOpenChange={setIsAddModalOpen}>
        <DialogContent data-testid="add-employee-modal">
          <DialogHeader>
            <DialogTitle>{t('addEmployee')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="code">{t('employeeCode')} *</Label>
                <Input
                  id="code"
                  value={formData.code}
                  onChange={(e) => setFormData(prev => ({ ...prev, code: e.target.value }))}
                  placeholder="e.g., 15"
                  data-testid="employee-code-input"
                />
              </div>
              <div>
                <Label htmlFor="salary">{t('monthlySalary')} *</Label>
                <Input
                  id="salary"
                  type="number"
                  value={formData.salary}
                  onChange={(e) => setFormData(prev => ({ ...prev, salary: e.target.value }))}
                  placeholder="e.g., 15000"
                  data-testid="employee-salary-input"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="name">{t('employeeName')} *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="e.g., Sanjeev Kumar"
                data-testid="employee-name-input"
              />
            </div>
            <div>
              <Label htmlFor="department">{t('department')}</Label>
              <Input
                id="department"
                value={formData.department}
                onChange={(e) => setFormData(prev => ({ ...prev, department: e.target.value }))}
                placeholder="e.g., Production"
                data-testid="employee-department-input"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="doj">{t('dateOfJoining')}</Label>
                <Input
                  id="doj"
                  type="date"
                  value={formData.dateOfJoining}
                  onChange={(e) => setFormData(prev => ({ ...prev, dateOfJoining: e.target.value }))}
                  data-testid="employee-doj-input"
                />
              </div>
              <div>
                <Label htmlFor="status">{t('status')}</Label>
                <Select
                  value={formData.status}
                  onValueChange={(value) => setFormData(prev => ({ ...prev, status: value }))}
                >
                  <SelectTrigger data-testid="employee-status-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">{t('active')}</SelectItem>
                    <SelectItem value="inactive">{t('inactive')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddModalOpen(false)} data-testid="cancel-add-employee">
              {t('cancel')}
            </Button>
            <Button onClick={handleAddEmployee} data-testid="save-add-employee">
              {t('save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Employee Modal */}
      <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
        <DialogContent data-testid="edit-employee-modal">
          <DialogHeader>
            <DialogTitle>{t('edit')} Employee</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>{t('employeeCode')}</Label>
                <Input value={formData.code} disabled className="bg-muted" />
              </div>
              <div>
                <Label htmlFor="edit-salary">{t('monthlySalary')} *</Label>
                <Input
                  id="edit-salary"
                  type="number"
                  value={formData.salary}
                  onChange={(e) => setFormData(prev => ({ ...prev, salary: e.target.value }))}
                  data-testid="edit-employee-salary-input"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="edit-name">{t('employeeName')} *</Label>
              <Input
                id="edit-name"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                data-testid="edit-employee-name-input"
              />
            </div>
            <div>
              <Label htmlFor="edit-department">{t('department')}</Label>
              <Input
                id="edit-department"
                value={formData.department}
                onChange={(e) => setFormData(prev => ({ ...prev, department: e.target.value }))}
                data-testid="edit-employee-department-input"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="edit-doj">{t('dateOfJoining')}</Label>
                <Input
                  id="edit-doj"
                  type="date"
                  value={formData.dateOfJoining}
                  onChange={(e) => setFormData(prev => ({ ...prev, dateOfJoining: e.target.value }))}
                  data-testid="edit-employee-doj-input"
                />
              </div>
              <div>
                <Label>{t('status')}</Label>
                <Select
                  value={formData.status}
                  onValueChange={(value) => setFormData(prev => ({ ...prev, status: value }))}
                >
                  <SelectTrigger data-testid="edit-employee-status-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">{t('active')}</SelectItem>
                    <SelectItem value="inactive">{t('inactive')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditModalOpen(false)} data-testid="cancel-edit-employee">
              {t('cancel')}
            </Button>
            <Button onClick={handleEditEmployee} data-testid="save-edit-employee">
              {t('save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent data-testid="delete-employee-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Employee</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete {selectedEmployee?.name} (Code: {selectedEmployee?.code})?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="cancel-delete-employee">{t('cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteEmployee}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              data-testid="confirm-delete-employee"
            >
              {t('delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
