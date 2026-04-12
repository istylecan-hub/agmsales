import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import { AppProvider } from "./context/AppContext";
import { AuthProvider } from "./context/AuthContext";
import { Layout } from "./components/Layout";
import PrivateRoute from "./components/PrivateRoute";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import EmployeeMaster from "./pages/EmployeeMaster";
import AttendanceUpload from "./pages/AttendanceUpload";
import SalaryConfiguration from "./pages/SalaryConfiguration";
import SalaryReport from "./pages/SalaryReport";
import AdvanceManagement from "./pages/AdvanceManagement";

function App() {
  return (
    <AuthProvider>
      <AppProvider>
        <BrowserRouter>
          <Routes>
            {/* Public route - Login */}
            <Route path="/login" element={<Login />} />
            
            {/* Protected routes */}
            <Route path="/" element={
              <PrivateRoute>
                <Layout><Dashboard /></Layout>
              </PrivateRoute>
            } />
            <Route path="/employees" element={
              <PrivateRoute>
                <Layout><EmployeeMaster /></Layout>
              </PrivateRoute>
            } />
            <Route path="/attendance" element={
              <PrivateRoute>
                <Layout><AttendanceUpload /></Layout>
              </PrivateRoute>
            } />
            <Route path="/configuration" element={
              <PrivateRoute>
                <Layout><SalaryConfiguration /></Layout>
              </PrivateRoute>
            } />
            <Route path="/reports" element={
              <PrivateRoute>
                <Layout><SalaryReport /></Layout>
              </PrivateRoute>
            } />
            <Route path="/advance" element={
              <PrivateRoute>
                <Layout><AdvanceManagement /></Layout>
              </PrivateRoute>
            } />
          </Routes>
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
    </AuthProvider>
  );
}

export default App;
