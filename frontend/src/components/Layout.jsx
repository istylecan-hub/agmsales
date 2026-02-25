import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { Button } from './ui/button';
import {
  LayoutDashboard,
  Users,
  Calendar,
  Settings,
  FileSpreadsheet,
  Menu,
  X,
  Sun,
  Moon,
  Languages,
  ChevronLeft,
  ChevronRight,
  FileText,
  Package,
  Upload,
  Tags,
  AlertCircle,
  BarChart3,
} from 'lucide-react';

export const Layout = ({ children }) => {
  const { t, toggleLanguage, language, isDarkMode, toggleTheme } = useApp();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'dashboard' },
    { path: '/employees', icon: Users, label: 'employees' },
    { path: '/attendance', icon: Calendar, label: 'attendance' },
    { path: '/configuration', icon: Settings, label: 'configuration' },
    { path: '/reports', icon: FileSpreadsheet, label: 'reports' },
    { path: '/invoice-extractor', icon: FileText, label: 'invoiceExtractor' },
    // OrderHub Section
    { path: '/orderhub', icon: Package, label: 'OrderHub', isNew: true },
    { path: '/orderhub/upload', icon: Upload, label: 'Upload Orders' },
    { path: '/orderhub/reports', icon: BarChart3, label: 'Order Reports' },
    { path: '/orderhub/master-skus', icon: Tags, label: 'Master SKUs' },
    { path: '/orderhub/unmapped', icon: AlertCircle, label: 'Unmapped SKUs' },
  ];

  const NavItem = ({ item, mobile = false }) => {
    const isActive = location.pathname === item.path;
    const Icon = item.icon;

    return (
      <NavLink
        to={item.path}
        onClick={() => mobile && setMobileMenuOpen(false)}
        className={`
          flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200
          ${isActive 
            ? 'bg-primary text-primary-foreground shadow-sm' 
            : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
          }
          ${sidebarCollapsed && !mobile ? 'justify-center' : ''}
        `}
        data-testid={`nav-${item.label}`}
      >
        <Icon className="w-5 h-5 flex-shrink-0" />
        {(!sidebarCollapsed || mobile) && (
          <span className="font-medium text-sm flex items-center gap-2">
            {t(item.label)}
            {item.isNew && (
              <span className="text-[10px] px-1.5 py-0.5 bg-orange-500 text-white rounded-full font-bold">
                NEW
              </span>
            )}
          </span>
        )}
      </NavLink>
    );
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 z-50 h-16 bg-card border-b border-border flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            data-testid="mobile-menu-toggle"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </Button>
          <h1 className="text-lg font-bold tracking-tight">{t('appName')}</h1>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={toggleLanguage} data-testid="language-toggle-mobile">
            <Languages className="w-5 h-5" />
          </Button>
          <Button variant="ghost" size="icon" onClick={toggleTheme} data-testid="theme-toggle-mobile">
            {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </Button>
        </div>
      </header>

      {/* Mobile Sidebar Overlay */}
      {mobileMenuOpen && (
        <div
          className="lg:hidden fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Mobile Sidebar */}
      <aside
        className={`
          lg:hidden fixed top-16 left-0 bottom-0 z-50 w-64 bg-card border-r border-border
          transform transition-transform duration-300
          ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <nav className="p-4 space-y-1">
          {navItems.map((item) => (
            <NavItem key={item.path} item={item} mobile />
          ))}
        </nav>
      </aside>

      {/* Desktop Sidebar */}
      <aside
        className={`
          hidden lg:flex flex-col fixed top-0 left-0 bottom-0 z-40
          bg-card/50 backdrop-blur-xl border-r border-border
          transition-all duration-300
          ${sidebarCollapsed ? 'w-16' : 'w-64'}
        `}
      >
        {/* Logo */}
        <div className={`
          h-16 flex items-center border-b border-border
          ${sidebarCollapsed ? 'justify-center px-2' : 'px-6'}
        `}>
          {!sidebarCollapsed && (
            <div>
              <h1 className="text-xl font-bold tracking-tight">{t('appName')}</h1>
              <p className="text-xs text-muted-foreground">{t('subtitle')}</p>
            </div>
          )}
          {sidebarCollapsed && (
            <span className="text-lg font-bold">AGM</span>
          )}
        </div>

        {/* Navigation */}
        <nav className={`flex-1 p-3 space-y-1 ${sidebarCollapsed ? 'px-2' : ''}`}>
          {navItems.map((item) => (
            <NavItem key={item.path} item={item} />
          ))}
        </nav>

        {/* Bottom Actions */}
        <div className={`p-3 border-t border-border space-y-1 ${sidebarCollapsed ? 'px-2' : ''}`}>
          <Button
            variant="ghost"
            className={`w-full ${sidebarCollapsed ? 'justify-center px-0' : 'justify-start'}`}
            onClick={toggleLanguage}
            data-testid="language-toggle"
          >
            <Languages className="w-5 h-5" />
            {!sidebarCollapsed && (
              <span className="ml-3 text-sm">{language === 'en' ? 'हिंदी' : 'English'}</span>
            )}
          </Button>
          <Button
            variant="ghost"
            className={`w-full ${sidebarCollapsed ? 'justify-center px-0' : 'justify-start'}`}
            onClick={toggleTheme}
            data-testid="theme-toggle"
          >
            {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            {!sidebarCollapsed && (
              <span className="ml-3 text-sm">{isDarkMode ? 'Light' : 'Dark'}</span>
            )}
          </Button>
          <Button
            variant="ghost"
            className={`w-full ${sidebarCollapsed ? 'justify-center px-0' : 'justify-start'}`}
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            data-testid="sidebar-collapse-toggle"
          >
            {sidebarCollapsed ? (
              <ChevronRight className="w-5 h-5" />
            ) : (
              <>
                <ChevronLeft className="w-5 h-5" />
                <span className="ml-3 text-sm">Collapse</span>
              </>
            )}
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <main
        className={`
          min-h-screen pt-16 lg:pt-0 transition-all duration-300
          ${sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64'}
        `}
      >
        <div className="p-4 lg:p-8">
          {children}
        </div>
      </main>
    </div>
  );
};
