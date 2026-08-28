/** Role-aware home: Admin stats, Manager pending tool approvals, Contributor summary. */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';

interface DashboardStats {
  lab_count: number;
  member_count: number;
  open_tasks: number;
  tool_count: number;
  pending_invitations: number;
  manager_count: number;
  contributor_count: number;
  admin_count: number;
  tasks_by_status: Record<string, number>;
  active_google_workspaces: number;
  labs_without_workspace: number;
}

interface LabSummary {
  lab_id: string;
  lab_name: string;
  member_count: number;
  open_tasks: number;
  has_google_workspace: boolean;
  workspace_status: string | null;
}

interface Task {
  id: string;
  title: string;
  status: string;
  assignee_id: string | null;
  priority: string;
}

interface PendingToolAccess {
  access: { id: string };
  tool_name: string;
  user_name: string;
  user_email: string;
}

function effectiveRole(orgRole: string, labId: string | null, labMemberships: { lab_id: string; organization_id: string; lab_role: string }[], orgId: string | null): string {
  if (orgRole === 'ADMIN') return 'Admin';
  const lm = labMemberships.find(l => l.organization_id === orgId && l.lab_id === labId);
  if (lm?.lab_role === 'MANAGER') return 'Manager';
  if (lm?.lab_role === 'CONTRIBUTOR') return 'Contributor';
  const anyInOrg = labMemberships.find(l => l.organization_id === orgId);
  if (anyInOrg?.lab_role === 'MANAGER') return 'Manager';
  if (anyInOrg?.lab_role === 'CONTRIBUTOR') return 'Contributor';
  return 'Member';
}

export default function DashboardPage() {
  const { orgId, labId, token, user } = useAuth();
  const queryClient = useQueryClient();

  const { data: me } = useQuery({
    queryKey: ['me'],
    queryFn: () => api<{
      memberships: { organization_id: string; org_role: string }[];
      lab_memberships: { lab_id: string; organization_id: string; lab_role: string }[];
      user: { name: string; email: string };
    }>('/auth/me'),
  });

  const orgMembership = me?.memberships.find(m => m.organization_id === orgId);
  const orgRole = orgMembership?.org_role || '';
  const roleName = effectiveRole(orgRole, labId, me?.lab_memberships || [], orgId);

  const { data: stats } = useQuery({
    queryKey: ['dashboard', orgId],
    queryFn: () => api<DashboardStats>(`/organizations/${orgId}/dashboard`, { orgId, token }),
    enabled: !!orgId && roleName === 'Admin',
  });

  const { data: labSummaries } = useQuery({
    queryKey: ['dashboard-labs', orgId],
    queryFn: () => api<LabSummary[]>(`/organizations/${orgId}/dashboard/labs`, { orgId, token }),
    enabled: !!orgId && roleName === 'Admin',
  });

  const { data: tasks } = useQuery({
    queryKey: ['tasks', orgId, labId],
    queryFn: () => {
      const params = labId ? `?lab_id=${labId}` : '';
      return api<Task[]>(`/organizations/${orgId}/tasks${params}`, { orgId, labId: labId || undefined, token });
    },
    enabled: !!orgId && roleName !== 'Admin',
  });

  const myTasks = tasks?.filter(t => t.assignee_id === user?.id) || [];
  const openInLab = tasks?.filter(t => t.status !== 'DONE') || [];

  const { data: pendingToolAccess } = useQuery({
    queryKey: ['tool-access-pending', orgId],
    queryFn: () => api<PendingToolAccess[]>(`/organizations/${orgId}/tool-access/pending`, { orgId, token }),
    enabled: !!orgId && roleName === 'Manager',
    refetchInterval: 5000,
  });

  const approveMutation = useMutation({
    mutationFn: (accessId: string) =>
      api(`/tool-access/${accessId}/approve`, { method: 'POST', orgId, token }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tool-access-pending'] });
      queryClient.invalidateQueries({ queryKey: ['tool-access'] });
    },
  });

  const denyMutation = useMutation({
    mutationFn: (accessId: string) =>
      api(`/tool-access/${accessId}/deny`, { method: 'POST', orgId, token }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tool-access-pending'] }),
  });

  const statusOrder = ['BACKLOG', 'TODO', 'IN_PROGRESS', 'BLOCKED', 'DONE'];

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: 16 }}>{me?.user.name}</div>
            <div className="mono">{me?.user.email}</div>
          </div>
          {roleName && <span className={`badge badge-${roleName.toLowerCase()}`}>{roleName}</span>}
        </div>
      </div>

      {roleName === 'Admin' && stats && (
        <>
          <div className="stat-grid" style={{ marginBottom: 24 }}>
            {[
              ['Labs', stats.lab_count],
              ['Members', stats.member_count],
              ['Open Tasks', stats.open_tasks],
              ['Tools', stats.tool_count],
              ['Pending Invites', stats.pending_invitations],
              ['Google Workspaces', stats.active_google_workspaces],
            ].map(([label, val]) => (
              <div key={label as string} className="stat-card">
                <div className="stat-value">{val}</div>
                <div className="stat-label">{label}</div>
              </div>
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
            <div className="card">
              <h3 style={{ marginBottom: 12 }}>Role Breakdown</h3>
              <div style={{ display: 'grid', gap: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Admins</span><span className="mono">{stats.admin_count}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Lab Managers</span><span className="mono">{stats.manager_count}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Contributors</span><span className="mono">{stats.contributor_count}</span>
                </div>
              </div>
            </div>

            <div className="card">
              <h3 style={{ marginBottom: 12 }}>Tasks by Status</h3>
              <div style={{ display: 'grid', gap: 8 }}>
                {statusOrder.map(status => (
                  <div key={status} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="mono" style={{ fontSize: 12 }}>{status.replace('_', ' ')}</span>
                    <div style={{ flex: 1, margin: '0 12px', height: 6, background: 'var(--bg-elevated)', borderRadius: 3 }}>
                      <div style={{
                        height: '100%',
                        width: `${Math.min(100, ((stats.tasks_by_status[status] || 0) / Math.max(1, Object.values(stats.tasks_by_status).reduce((a, b) => a + b, 0))) * 100)}%`,
                        background: 'var(--accent)',
                        borderRadius: 3,
                      }} />
                    </div>
                    <span className="mono">{stats.tasks_by_status[status] || 0}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {stats.labs_without_workspace > 0 && (
            <div className="card" style={{ marginBottom: 24, borderColor: 'var(--warning)' }}>
              <strong>{stats.labs_without_workspace} lab(s)</strong> without Google Workspace.{' '}
              <Link to="/admin/labs">Provision from Lab Management →</Link>
            </div>
          )}

          <div className="card">
            <h3 style={{ marginBottom: 12 }}>Lab Analytics</h3>
            <table>
              <thead>
                <tr><th>Lab</th><th>Members</th><th>Open Tasks</th><th>Google Workspace</th></tr>
              </thead>
              <tbody>
                {labSummaries?.map(l => (
                  <tr key={l.lab_id}>
                    <td>{l.lab_name}</td>
                    <td className="mono">{l.member_count}</td>
                    <td className="mono">{l.open_tasks}</td>
                    <td>
                      {l.has_google_workspace ? (
                        <span className={`badge badge-${l.workspace_status === 'ACTIVE' ? 'active' : 'provisioning'}`}>
                          {l.workspace_status}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>Not provisioned</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {roleName === 'Manager' && (
        <>
          {pendingToolAccess && pendingToolAccess.length > 0 && (
            <div className="card" style={{ marginBottom: 24, borderColor: 'var(--accent)' }}>
              <h3 style={{ marginBottom: 12 }}>Tool Access Requests</h3>
              <table>
                <thead>
                  <tr><th>Member</th><th>Tool</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {pendingToolAccess.map(req => (
                    <tr key={req.access.id}>
                      <td>{req.user_name} <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>{req.user_email}</span></td>
                      <td>{req.tool_name}</td>
                      <td>
                        <div style={{ display: 'flex', gap: 8 }}>
                          <button className="sm" onClick={() => approveMutation.mutate(req.access.id)} disabled={approveMutation.isPending}>
                            Approve
                          </button>
                          <button className="sm secondary" onClick={() => denyMutation.mutate(req.access.id)} disabled={denyMutation.isPending}>
                            Deny
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 style={{ marginBottom: 12 }}>Lab Overview</h3>
            <div className="stat-grid">
              <div className="stat-card">
                <div className="stat-value">{openInLab.length}</div>
                <div className="stat-label">Open Tasks</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{tasks?.filter(t => t.status === 'IN_PROGRESS').length || 0}</div>
                <div className="stat-label">In Progress</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{tasks?.filter(t => t.status === 'BLOCKED').length || 0}</div>
                <div className="stat-label">Blocked</div>
              </div>
            </div>
          </div>
        </>
      )}

      {(roleName === 'Manager' || roleName === 'Contributor') && (
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>{roleName === 'Contributor' ? 'My Work' : 'Recent Tasks'}</h3>
          <table>
            <thead>
              <tr><th>Task</th><th>Status</th><th>Priority</th></tr>
            </thead>
            <tbody>
              {(roleName === 'Contributor' ? myTasks : tasks?.slice(0, 8) || []).map(t => (
                <tr key={t.id}>
                  <td><Link to={`/tasks/${t.id}`}>{t.title}</Link></td>
                  <td><span className={`badge badge-${t.status === 'DONE' ? 'active' : 'contributor'}`}>{t.status}</span></td>
                  <td className="mono">{t.priority}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
