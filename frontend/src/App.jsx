import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './lib/auth';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import CaseList from './pages/CaseList';
import CaseDetail from './pages/CaseDetail';
import CreateCase from './pages/CreateCase';
import Escalations from './pages/Escalations';
import SLAMonitor from './pages/SLAMonitor';
import Team from './pages/Team';
import QAEvaluations from './pages/QAEvaluations';
import Leaderboard from './pages/Leaderboard';
import AuditLogs from './pages/AuditLogs';
import UserManagement from './pages/UserManagement';
import SimulateCall from './pages/SimulateCall';
import InvestorSearch from './pages/InvestorSearch';
import Loader from './components/Loader';
import { ToastProvider } from './components/Toast';

function ProtectedRoute({ children, allowedRoles }) {
  const { user, loading } = useAuth();
  if (loading) return <Loader />;
  if (!user) return <Navigate to="/login" replace />;
  if (allowedRoles && !allowedRoles.includes(user.role_name)) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) return <Loader />;

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/dashboard" replace /> : <Login />} />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/cases" element={<CaseList />} />
        <Route path="/cases/new" element={
          <ProtectedRoute allowedRoles={['agent', 'admin', 'supervisor']}>
            <CreateCase />
          </ProtectedRoute>
        } />
        <Route path="/cases/:caseId" element={<CaseDetail />} />
        <Route path="/escalations" element={
          <ProtectedRoute allowedRoles={['supervisor', 'admin']}>
            <Escalations />
          </ProtectedRoute>
        } />
        <Route path="/sla" element={
          <ProtectedRoute allowedRoles={['supervisor', 'admin']}>
            <SLAMonitor />
          </ProtectedRoute>
        } />
        <Route path="/team" element={
          <ProtectedRoute allowedRoles={['supervisor', 'admin']}>
            <Team />
          </ProtectedRoute>
        } />
        <Route path="/qa" element={
          <ProtectedRoute allowedRoles={['qa_analyst', 'admin']}>
            <QAEvaluations />
          </ProtectedRoute>
        } />
        <Route path="/leaderboard" element={
          <ProtectedRoute allowedRoles={['qa_analyst', 'admin']}>
            <Leaderboard />
          </ProtectedRoute>
        } />
        <Route path="/audit" element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AuditLogs />
          </ProtectedRoute>
        } />
        <Route path="/admin/users" element={
          <ProtectedRoute allowedRoles={['admin']}>
            <UserManagement />
          </ProtectedRoute>
        } />
        <Route path="/simulate" element={
          <ProtectedRoute allowedRoles={['supervisor', 'admin']}>
            <SimulateCall />
          </ProtectedRoute>
        } />
        <Route path="/investor-search" element={
          <ProtectedRoute allowedRoles={['agent', 'supervisor', 'admin']}>
            <InvestorSearch />
          </ProtectedRoute>
        } />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <ToastProvider>
          <AppRoutes />
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
