// Storage utility functions - sensitive data in React state only, NOT localStorage

import { STORAGE_KEYS, DEFAULT_CONFIG } from './constants';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Helper to get auth headers
const getAuthHeaders = () => {
  const token = sessionStorage.getItem('auth_token');
  if (token) {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    };
  }
  return { 'Content-Type': 'application/json' };
};

export const storage = {
  // Employees - NO localStorage, only server sync
  getEmployees: () => {
    // No longer read from localStorage for security
    return [];
  },
  
  setEmployees: (employees) => {
    // Only sync to MongoDB server, no localStorage
    storage.syncEmployeesToServer(employees);
    return true;
  },
  
  // Sync employees to MongoDB server
  syncEmployeesToServer: async (employees) => {
    try {
      const response = await fetch(`${API_URL}/api/employees`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(employees),
      });
      if (response.status === 401) {
        console.warn('[Storage] Unauthorized - user not logged in');
        return;
      }
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
      const response = await fetch(`${API_URL}/api/employees`, {
        headers: getAuthHeaders(),
      });
      if (response.status === 401) {
        console.warn('[Storage] Unauthorized - token missing or expired');
        return null;
      }
      const result = await response.json();
      if (result.success && result.data && result.data.length > 0) {
        console.log('[Storage] Loaded employees from server:', result.data.length);
        return result.data;
      }
      return null;
    } catch (e) {
      console.warn('[Storage] Could not load from server:', e.message);
      return null;
    }
  },
  
  // Configuration - kept in localStorage (non-sensitive settings only)
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
  
  // Attendance Data - React state only, NO localStorage
  getAttendanceData: () => null,
  setAttendanceData: () => true,
  
  // Calculation Results - React state only, NO localStorage
  getLastCalculation: () => null,
  setLastCalculation: () => true,
  
  // Clear all sensitive data
  clearAll: () => {
    try {
      // Only remove config from localStorage (theme handled separately)
      localStorage.removeItem(STORAGE_KEYS.CONFIG);
      return true;
    } catch (e) {
      console.error('Error clearing storage:', e);
      return false;
    }
  },
  
  // Clear salary module data - now just returns true (data is in React state)
  clearSalaryData: () => {
    console.log('[Storage] Salary data cleared (state only)');
    return true;
  },
};
