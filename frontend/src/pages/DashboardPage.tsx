import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';

interface DashboardStats {
  lab_count: number;
  member_count: number;
  open_tasks: number;
  tool_count: number;
  pending_invitations: number;
}

interface MeData {
  user: { name: string; email: string };
  memberships: { organization_id: string; role_name: string }[];
}

interface Task {
  id: string;
  title: string;
  status: string;
  assignee_id: string | null;
  due_date: string | null;
}

export default function DashboardPage() {
  const { orgId, labId, token, user } = useAuth();

  const { data: me } = useQuery({
    queryKey: ['me'],
    queryFn: () => api<MeData>('/auth/me'),
  });

  const membership = me?.memberships.find(m => m.organization_id === orgId);
  const roleName = membership?.role_name || '';

  const { data: stats } = useQuery({
    queryKey: ['dashboard', orgId],
    queryFn: () => api<DashboardStats>(`/organizations/${orgId}/dashboard`, { orgId, token }),
    enabled: !!orgId,
  });

  const { data: tasks } = useQuery({
    queryKey: ['tasks', orgId, labId],
    queryFn: () => {
      const params = labId ? `?lab_id=${labId}` : '';
      return api<Task[]>(`/organizations/${orgId}/tasks${params}`, { orgId, labId: labId || undefined, token });
    },
    enabled: !!orgId,
  });

  const myTasks = tasks?.filter(t => t.assignee_id === user?.id) || [];
  const overdue = myTasks.filter(t => t.due_date && new Date(t.due_date) < new Date() && t.status !== 'DONE');
  const dueToday = myTasks.filter(t => {
    if (!t.due_date) return false;
    const d = new Date(t.due_date);
    const today = new Date();
    return d.toDateString() === today.toDateString() && t.status !== 'DONE';
  });

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>Dashboard</h1>
      <div className="card" style={{ marginBottom: 24 }}>
        <h3>Profile</h3>
        <p><strong>{me?.user.name}</strong> ({me?.user.email})</p>
        <p>Role: <span className="badge badge-active">{roleName}</span></p>
      </div>

      {roleName === 'Admin' && stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 16, marginBottom: 24 }}>
          {[
            ['Labs', stats.lab_count],
            ['Members', stats.member_count],
            ['Open Tasks', stats.open_tasks],
            ['Tools', stats.tool_count],
            ['Pending Invites', stats.pending_invitations],
          ].map(([label, val]) => (
            <div key={label as string} className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700 }}>{val}</div>
              <div style={{ color: '#6c757d', fontSize: 13 }}>{label}</div>
            </div>
          ))}
        </div>
      )}

      {(roleName === 'Manager' || roleName === 'Contributor') && (
        <div className="card">
          <h3>{roleName === 'Contributor' ? 'My Work' : 'Lab Overview'}</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginTop: 12 }}>
            <div><strong>{myTasks.filter(t => t.status !== 'DONE').length}</strong> assigned</div>
            <div><strong>{dueToday.length}</strong> due today</div>
            <div><strong>{overdue.length}</strong> overdue</div>
          </div>
          <ul style={{ marginTop: 16, listStyle: 'none' }}>
            {myTasks.slice(0, 5).map(t => (
              <li key={t.id} style={{ padding: '8px 0', borderBottom: '1px solid #eee' }}>
                {t.title} <span className="badge">{t.status}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
