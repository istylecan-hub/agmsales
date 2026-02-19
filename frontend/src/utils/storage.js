// LocalStorage utility functions

import { STORAGE_KEYS, DEFAULT_CONFIG } from './constants';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export const storage = {
  // Employees
  getEmployees: () => {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.EMPLOYEES);
      const employees = data ? JSON.parse(data) : [];
      console.log('[Storage] Loaded employees from localStorage:', employees.length);
      return employees;
    } catch (e) {
      console.error('[Storage] Error reading employees:', e);
      return [];
    }
  },
  
  setEmployees: (employees) => {
    try {
      localStorage.setItem(STORAGE_KEYS.EMPLOYEES, JSON.stringify(employees));
      console.log('[Storage] Saved employees to localStorage:', employees.length);
      
      // Also sync to MongoDB (async, non-blocking)
      storage.syncEmployeesToServer(employees);
      
      return true;
    } catch (e) {
      console.error('[Storage] Error saving employees:', e);
      if (e.name === 'QuotaExceededError') {
        console.error('[Storage] LocalStorage quota exceeded!');
      }
      return false;
    }
  },
  
  // Sync employees to MongoDB server
  syncEmployeesToServer: async (employees) => {
    try {
      const response = await fetch(`${API_URL}/api/employees`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(employees),
      });
      const result = await response.json();
      if (result.success) {
        console.log('[Storage] Synced employees to server:', employees.length);
      } else {
        console.warn('[Storage] Server sync warning:', result.message);
      }
    } catch (e) {
      console.warn('[Storage] Could not sync to server (offline?):', e.message);
    }
  },
  
  // Load employees from MongoDB server
  loadEmployeesFromServer: async () => {
    try {
      const response = await fetch(`${API_URL}/api/employees`);
      const result = await response.json();
      if (result.success && result.data && result.data.length > 0) {
        console.log('[Storage] Loaded employees from server:', result.data.length);
        // Save to localStorage as backup
        localStorage.setItem(STORAGE_KEYS.EMPLOYEES, JSON.stringify(result.data));
        return result.data;
      }
      return null;
    } catch (e) {
      console.warn('[Storage] Could not load from server:', e.message);
      return null;
    }
  },
  
  addEmployee: (employee) => {
    const employees = storage.getEmployees();
    employees.push(employee);
    return storage.setEmployees(employees);
  },
  
  updateEmployee: (code, updates) => {
    const employees = storage.getEmployees();
    const index = employees.findIndex(e => e.code === code);
    if (index !== -1) {
      employees[index] = { ...employees[index], ...updates };
      return storage.setEmployees(employees);
    }
    return false;
  },
  
  deleteEmployee: (code) => {
    const employees = storage.getEmployees();
    const filtered = employees.filter(e => e.code !== code);
    return storage.setEmployees(filtered);
  },
  
  // Configuration
  getConfig: () => {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.CONFIG);
      return data ? { ...DEFAULT_CONFIG, ...JSON.parse(data) } : DEFAULT_CONFIG;
    } catch (e) {
      console.error('Error reading config from storage:', e);
      return DEFAULT_CONFIG;
    }
  },
  
  setConfig: (config) => {
    try {
      localStorage.setItem(STORAGE_KEYS.CONFIG, JSON.stringify(config));
      return true;
    } catch (e) {
      console.error('Error saving config to storage:', e);
      return false;
    }
  },
  
  // Attendance Data
  getAttendanceData: () => {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.ATTENDANCE_DATA);
      return data ? JSON.parse(data) : null;
    } catch (e) {
      console.error('Error reading attendance from storage:', e);
      return null;
    }
  },
  
  setAttendanceData: (data) => {
    try {
      localStorage.setItem(STORAGE_KEYS.ATTENDANCE_DATA, JSON.stringify(data));
      return true;
    } catch (e) {
      console.error('Error saving attendance to storage:', e);
      return false;
    }
  },
  
  // Last Calculation Results
  getLastCalculation: () => {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.LAST_CALCULATION);
      return data ? JSON.parse(data) : null;
    } catch (e) {
      console.error('Error reading calculation from storage:', e);
      return null;
    }
  },
  
  setLastCalculation: (data) => {
    try {
      localStorage.setItem(STORAGE_KEYS.LAST_CALCULATION, JSON.stringify(data));
      return true;
    } catch (e) {
      console.error('Error saving calculation to storage:', e);
      return false;
    }
  },
  
  // Clear all data
  clearAll: () => {
    try {
      Object.values(STORAGE_KEYS).forEach(key => localStorage.removeItem(key));
      return true;
    } catch (e) {
      console.error('Error clearing storage:', e);
      return false;
    }
  },
};
