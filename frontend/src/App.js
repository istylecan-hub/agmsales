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
import AdvanceManagement from "./pages/AdvanceManagement";

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
            <Route path="/advance" element={<AdvanceManagement />} />
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
