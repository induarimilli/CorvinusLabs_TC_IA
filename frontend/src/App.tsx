import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import TasksPage from './pages/tasks/TasksPage';
import TaskDetailPage from './pages/tasks/TaskDetailPage';
import ToolsPage from './pages/tools/ToolsPage';
import TeamPage from './pages/team/TeamPage';
import AdminMembersPage from './pages/admin/AdminMembersPage';
import AdminLabsPage from './pages/admin/AdminLabsPage';
import AdminToolsPage from './pages/admin/AdminToolsPage';
import AdminAuditPage from './pages/admin/AdminAuditPage';
import InviteAcceptPage from './pages/InviteAcceptPage';
import PlatformAnalyticsPage from './pages/platform/PlatformAnalyticsPage';
import AppShell from './components/layout/AppShell';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  return <AppShell>{children}</AppShell>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/invite/:token" element={<InviteAcceptPage />} />
      <Route path="/platform" element={<ProtectedRoute><PlatformAnalyticsPage /></ProtectedRoute>} />
      <Route path="/platform/orgs" element={<ProtectedRoute><PlatformAnalyticsPage /></ProtectedRoute>} />
      <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/tasks" element={<ProtectedRoute><TasksPage /></ProtectedRoute>} />
      <Route path="/tasks/:taskId" element={<ProtectedRoute><TaskDetailPage /></ProtectedRoute>} />
      <Route path="/tools" element={<ProtectedRoute><ToolsPage /></ProtectedRoute>} />
      <Route path="/team" element={<ProtectedRoute><TeamPage /></ProtectedRoute>} />
      <Route path="/admin/members" element={<ProtectedRoute><AdminMembersPage /></ProtectedRoute>} />
      <Route path="/admin/labs" element={<ProtectedRoute><AdminLabsPage /></ProtectedRoute>} />
      <Route path="/admin/tools" element={<ProtectedRoute><AdminToolsPage /></ProtectedRoute>} />
      <Route path="/admin/audit" element={<ProtectedRoute><AdminAuditPage /></ProtectedRoute>} />
      <Route path="/invites" element={<Navigate to="/admin/members" replace />} />
      <Route path="/admin/invites" element={<Navigate to="/admin/members" replace />} />
      <Route path="/admin/settings" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
