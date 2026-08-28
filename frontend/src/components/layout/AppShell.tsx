import { Link, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';
import OrgLabSwitcher from './OrgLabSwitcher';
import NotificationsPanel from './NotificationsPanel';

interface MeResponse {
  memberships: { organization_id: string; role_name: string }[];
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout, orgId } = useAuth();
  const location = useLocation();

  const { data: me } = useQuery({
    queryKey: ['me'],
    queryFn: () => api<MeResponse>('/auth/me'),
  });

  const currentMembership = me?.memberships.find(m => m.organization_id === orgId);
  const roleName = currentMembership?.role_name || '';

  const navItems = [
    { path: '/', label: 'Dashboard' },
    { path: '/tasks', label: 'Tasks' },
    { path: '/tools', label: 'Tools' },
    ...(roleName === 'Admin' || roleName === 'Manager' ? [{ path: '/team', label: 'Team' }] : []),
    ...(roleName === 'Admin' ? [
      { path: '/admin/members', label: 'Members' },
      { path: '/admin/labs', label: 'Labs' },
      { path: '/admin/tools', label: 'Tool Registry' },
      { path: '/admin/invites', label: 'Invitations' },
      { path: '/admin/audit', label: 'Audit Log' },
      { path: '/admin/settings', label: 'Settings' },
    ] : []),
  ];

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside style={{ width: 220, background: '#1a1a2e', color: 'white', padding: 20 }}>
        <h2 style={{ fontSize: 18, marginBottom: 24 }}>Corvinus Labs</h2>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {navItems.map(item => (
            <Link
              key={item.path}
              to={item.path}
              style={{
                color: location.pathname === item.path ? '#4361ee' : '#adb5bd',
                padding: '8px 12px',
                borderRadius: 6,
                background: location.pathname === item.path ? 'rgba(67,97,238,0.15)' : 'transparent',
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <header style={{
          background: 'white', padding: '12px 24px', borderBottom: '1px solid #dee2e6',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <OrgLabSwitcher />
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span>{user?.name} <span className="badge badge-active">{roleName}</span></span>
            <button className="secondary" onClick={logout}>Logout</button>
          </div>
        </header>
        <div style={{ padding: 24, flex: 1 }}>
          <NotificationsPanel />
          {children}
        </div>
      </main>
    </div>
  );
}
