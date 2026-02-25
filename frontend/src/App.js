import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import { AppProvider } from "./context/AppContext";
import { Layout } from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import EmployeeMaster from "./pages/EmployeeMaster";
import AttendanceUpload from "./pages/AttendanceUpload";
import SalaryConfiguration from "./pages/SalaryConfiguration";
import SalaryReport from "./pages/SalaryReport";
import InvoiceExtractor from "./pages/InvoiceExtractor";

// OrderHub Pages
import OrderHubDashboard from './pages/orderhub/Dashboard';
import OrderHubUpload from './pages/orderhub/Upload';
import OrderHubReports from './pages/orderhub/Reports';
import OrderHubMasterSKUs from './pages/orderhub/MasterSKUs';
import OrderHubUnmappedSKUs from './pages/orderhub/UnmappedSKUs';

function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/employees" element={<EmployeeMaster />} />
            <Route path="/attendance" element={<AttendanceUpload />} />
            <Route path="/configuration" element={<SalaryConfiguration />} />
            <Route path="/reports" element={<SalaryReport />} />
            <Route path="/invoice-extractor" element={<InvoiceExtractor />} />
            {/* OrderHub Routes */}
            <Route path="/orderhub" element={<OrderHubDashboard />} />
            <Route path="/orderhub/upload" element={<OrderHubUpload />} />
            <Route path="/orderhub/reports" element={<OrderHubReports />} />
            <Route path="/orderhub/master-skus" element={<OrderHubMasterSKUs />} />
            <Route path="/orderhub/unmapped" element={<OrderHubUnmappedSKUs />} />
          </Routes>
        </Layout>
        <Toaster 
          position="top-right" 
          richColors 
          closeButton
          toastOptions={{
            style: {
              fontFamily: 'Inter, sans-serif',
            },
          }}
        />
      </BrowserRouter>
    </AppProvider>
  );
}

export default App;
