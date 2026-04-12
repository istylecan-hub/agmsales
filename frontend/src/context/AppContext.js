import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { storage } from '../utils/storage';
import { DEFAULT_CONFIG, TRANSLATIONS } from '../utils/constants';

const AppContext = createContext(null);

export const AppProvider = ({ children }) => {
  // Flag to track if initial load is complete
  const isInitialLoadComplete = useRef(false);
  
  // Language state
  const [language, setLanguage] = useState('en');
  
  // Theme state
  const [isDarkMode, setIsDarkMode] = useState(false);
  
  // Employee data - start empty, load from server
  const [employees, setEmployees] = useState([]);
  
  // Configuration - initialize from localStorage (non-sensitive settings)
  const [config, setConfig] = useState(() => storage.getConfig());
  
  // Attendance data - React state only, NO localStorage
  const [attendanceData, setAttendanceData] = useState(null);
  
  // Calculation results - React state only, NO localStorage
  const [calculationResults, setCalculationResults] = useState(null);
  
  // Current step in wizard
  const [currentStep, setCurrentStep] = useState(1);
  
  // Loading states
  const [isLoading, setIsLoading] = useState(false);
  
  // Load employees from server and handle theme on mount
  useEffect(() => {
    // Clean up any old sensitive data from localStorage
    localStorage.removeItem('agm_employees');
    localStorage.removeItem('agm_attendance_data');
    localStorage.removeItem('agm_last_calculation');
    localStorage.removeItem('agm_attendance');
    localStorage.removeItem('agm_calculation');
    
    // Check for dark mode preference
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const savedTheme = localStorage.getItem('agm_theme');
    setIsDarkMode(savedTheme === 'dark' || (!savedTheme && prefersDark));
    
    // Load employees from MongoDB server
    const loadFromServer = async () => {
      console.log('[AppContext] Loading employees from server...');
      try {
        const serverEmployees = await storage.loadEmployeesFromServer();
        if (serverEmployees && serverEmployees.length > 0) {
          console.log('[AppContext] Loaded employees from server:', serverEmployees.length);
          setEmployees(serverEmployees);
        }
      } catch (e) {
        console.warn('[AppContext] Server load failed:', e);
      }
    };
    
    loadFromServer();
    
    // Mark initial load as complete after a small delay
    setTimeout(() => {
      isInitialLoadComplete.current = true;
    }, 500);
  }, []);
  
  // Apply dark mode class
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('agm_theme', isDarkMode ? 'dark' : 'light');
  }, [isDarkMode]);
  
  // Sync employees to server when changed (only after initial load)
  useEffect(() => {
    if (isInitialLoadComplete.current) {
      storage.setEmployees(employees);
    }
  }, [employees]);
  
  // Save config to localStorage when changed (non-sensitive settings)
  useEffect(() => {
    if (isInitialLoadComplete.current) {
      storage.setConfig(config);
    }
  }, [config]);
  
  // Translation helper
  const t = (key) => {
    return TRANSLATIONS[language]?.[key] || TRANSLATIONS.en[key] || key;
  };
  
  // Toggle language
  const toggleLanguage = () => {
    setLanguage(prev => prev === 'en' ? 'hi' : 'en');
  };
  
  // Toggle theme
  const toggleTheme = () => {
    setIsDarkMode(prev => !prev);
  };
  
  // Employee CRUD operations
  const addEmployee = (employee) => {
    setEmployees(prev => [...prev, employee]);
  };
  
  const updateEmployee = (code, updates) => {
    setEmployees(prev => 
      prev.map(emp => emp.code === code ? { ...emp, ...updates } : emp)
    );
  };
  
  const deleteEmployee = (code) => {
    setEmployees(prev => prev.filter(emp => emp.code !== code));
  };
  
  const importEmployees = (newEmployees, replace = false) => {
    if (replace) {
      setEmployees(newEmployees);
    } else {
      // Merge - update existing, add new
      setEmployees(prev => {
        const existingCodes = new Set(prev.map(e => e.code));
        const toAdd = newEmployees.filter(e => !existingCodes.has(e.code));
        const updated = prev.map(emp => {
          const match = newEmployees.find(e => e.code === emp.code);
          return match ? { ...emp, ...match } : emp;
        });
        return [...updated, ...toAdd];
      });
    }
  };
  
  // Reset wizard
  const resetWizard = () => {
    setAttendanceData(null);
    setCalculationResults(null);
    setCurrentStep(1);
  };
  
  const value = {
    // Language
    language,
    setLanguage,
    toggleLanguage,
    t,
    
    // Theme
    isDarkMode,
    toggleTheme,
    
    // Employees
    employees,
    setEmployees,
    addEmployee,
    updateEmployee,
    deleteEmployee,
    importEmployees,
    
    // Config
    config,
    setConfig,
    
    // Attendance
    attendanceData,
    setAttendanceData,
    
    // Results
    calculationResults,
    setCalculationResults,
    
    // Wizard
    currentStep,
    setCurrentStep,
    resetWizard,
    
    // Loading
    isLoading,
    setIsLoading,
  };
  
  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
};
