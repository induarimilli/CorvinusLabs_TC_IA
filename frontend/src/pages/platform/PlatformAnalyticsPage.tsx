import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

interface Analytics {
  active_organizations: number;
  total_users: number;
  total_tasks: number;
  open_tasks: number;
  total_tools: number;
  tool_provisioning_success_rate: number;
  tool_access_active: number;
  tool_access_failed: number;
  organizations: { id: string; name: string; slug: string; member_count: number; task_count: number }[];
}

export default function PlatformAnalyticsPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [orgName, setOrgName] = useState('');
  const [message, setMessage] = useState('');

  const { data: analytics } = useQuery({
    queryKey: ['platform-analytics'],
    queryFn: () => api<Analytics>('/platform/analytics', { token }),
  });

  const createMutation = useMutation({
    mutationFn: (name: string) =>
      api<{ name: string }>('/platform/organizations', { method: 'POST', body: { name }, token }),
    onSuccess: (org) => {
      setMessage(`Created organization: ${org.name}`);
      setOrgName('');
      queryClient.invalidateQueries({ queryKey: ['platform-analytics'] });
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const deactivateMutation = useMutation({
    mutationFn: (orgId: string) =>
      api(`/platform/organizations/${orgId}/deactivate`, { method: 'PATCH', token }),
    onSuccess: () => {
      setMessage('Organization deactivated');
      queryClient.invalidateQueries({ queryKey: ['platform-analytics'] });
    },
    onError: (e: Error) => setMessage(e.message),
  });

  return (
    <div>
      <div className="page-header">
        <h1>Platform Analytics</h1>
      </div>

      {analytics && (
        <div className="stat-grid" style={{ marginBottom: 32 }}>
          {[
            ['Active Orgs', analytics.active_organizations],
            ['Total Users', analytics.total_users],
            ['Open Tasks', analytics.open_tasks],
            ['Total Tasks', analytics.total_tasks],
            ['Tools', analytics.total_tools],
            ['Provision Success', `${analytics.tool_provisioning_success_rate}%`],
          ].map(([label, val]) => (
            <div key={label as string} className="stat-card">
              <div className="stat-value">{val}</div>
              <div className="stat-label">{label}</div>
            </div>
          ))}
        </div>
      )}

      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 16 }}>Create Organization</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            value={orgName}
            onChange={e => setOrgName(e.target.value)}
            placeholder="Organization name"
            style={{ flex: 1 }}
          />
          <button
            onClick={() => createMutation.mutate(orgName)}
            disabled={!orgName || createMutation.isPending}
          >
            Create
          </button>
        </div>
        {message && <p style={{ marginTop: 8, color: 'var(--accent)', fontSize: 13 }}>{message}</p>}
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 16 }}>All Organizations</h3>
        <table>
          <thead>
            <tr>
              <th>Organization</th>
              <th>Slug</th>
              <th>Members</th>
              <th>Tasks</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {analytics?.organizations.map(org => (
              <tr key={org.id}>
                <td>{org.name}</td>
                <td className="mono">{org.slug}</td>
                <td className="mono">{org.member_count}</td>
                <td className="mono">{org.task_count}</td>
                <td>
                  <button className="sm danger" onClick={() => deactivateMutation.mutate(org.id)} disabled={deactivateMutation.isPending}>
                    Deactivate
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
