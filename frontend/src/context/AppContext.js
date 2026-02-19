import React, { createContext, useContext, useState, useEffect } from 'react';
import { storage } from '../utils/storage';
import { DEFAULT_CONFIG, TRANSLATIONS } from '../utils/constants';

const AppContext = createContext(null);

export const AppProvider = ({ children }) => {
  // Language state
  const [language, setLanguage] = useState('en');
  
  // Theme state
  const [isDarkMode, setIsDarkMode] = useState(false);
  
  // Employee data
  const [employees, setEmployees] = useState([]);
  
  // Configuration
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  
  // Attendance data
  const [attendanceData, setAttendanceData] = useState(null);
  
  // Calculation results
  const [calculationResults, setCalculationResults] = useState(null);
  
  // Current step in wizard
  const [currentStep, setCurrentStep] = useState(1);
  
  // Loading states
  const [isLoading, setIsLoading] = useState(false);
  
  // Load data from localStorage on mount
  useEffect(() => {
    const savedEmployees = storage.getEmployees();
    const savedConfig = storage.getConfig();
    const savedAttendance = storage.getAttendanceData();
    const savedCalculation = storage.getLastCalculation();
    
    if (savedEmployees.length > 0) setEmployees(savedEmployees);
    setConfig(savedConfig);
    if (savedAttendance) setAttendanceData(savedAttendance);
    if (savedCalculation) setCalculationResults(savedCalculation);
    
    // Check for dark mode preference
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const savedTheme = localStorage.getItem('agm_theme');
    setIsDarkMode(savedTheme === 'dark' || (!savedTheme && prefersDark));
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
  
  // Save employees to localStorage when changed
  useEffect(() => {
    // Always save employees array (even if empty)
    storage.setEmployees(employees);
  }, [employees]);
  
  // Save config to localStorage when changed
  useEffect(() => {
    storage.setConfig(config);
  }, [config]);
  
  // Save attendance data when changed
  useEffect(() => {
    if (attendanceData) {
      storage.setAttendanceData(attendanceData);
    }
  }, [attendanceData]);
  
  // Save calculation results when changed
  useEffect(() => {
    if (calculationResults) {
      storage.setLastCalculation(calculationResults);
    }
  }, [calculationResults]);
  
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
