import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

export default function TeamPage() {
  const { orgId, token } = useAuth();
  const queryClient = useQueryClient();
  const [grantToolId, setGrantToolId] = useState('');
  const [grantUserId, setGrantUserId] = useState('');

  const { data: members } = useQuery({
    queryKey: ['members-details', orgId],
    queryFn: () => api<{ membership: { id: string; role_name: string; status: string }; user: { id: string; name: string; email: string } }[]>(
      `/organizations/${orgId}/members/details`, { orgId, token }
    ),
    enabled: !!orgId,
  });

  const { data: tools } = useQuery({
    queryKey: ['tools', orgId],
    queryFn: () => api<{ id: string; name: string }[]>(`/organizations/${orgId}/tools`, { orgId, token }),
    enabled: !!orgId,
  });

  const { data: accessList, refetch: refetchAccess } = useQuery({
    queryKey: ['tool-access', orgId],
    queryFn: () => api<{ access: { id: string; tool_id: string; user_id: string; provisioning_status: string }; tool_name: string; user_name: string }[]>(
      `/organizations/${orgId}/tool-access`, { orgId, token }
    ),
    enabled: !!orgId,
    refetchInterval: 3000,
  });

  const grantMutation = useMutation({
    mutationFn: () => api(`/tools/${grantToolId}/access`, {
      method: 'POST', body: { user_id: grantUserId, access_level: 'view' }, orgId, token,
    }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['tool-access'] }); setGrantToolId(''); setGrantUserId(''); },
  });

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>Team</h1>

      <div className="card" style={{ marginBottom: 24 }}>
        <h3>Members</h3>
        <table style={{ width: '100%', marginTop: 12, borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>
              <th style={{ padding: 8 }}>Name</th>
              <th style={{ padding: 8 }}>Email</th>
              <th style={{ padding: 8 }}>Role</th>
              <th style={{ padding: 8 }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {members?.map(({ user, membership }) => (
              <tr key={membership.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: 8 }}>{user.name}</td>
                <td style={{ padding: 8 }}>{user.email}</td>
                <td style={{ padding: 8 }}><span className="badge badge-active">{membership.role_name}</span></td>
                <td style={{ padding: 8 }}>{membership.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <h3>Grant Tool Access</h3>
        <div style={{ display: 'flex', gap: 12, marginTop: 12 }}>
          <select value={grantUserId} onChange={e => setGrantUserId(e.target.value)}>
            <option value="">Select member</option>
            {members?.map(({ user }) => <option key={user.id} value={user.id}>{user.name}</option>)}
          </select>
          <select value={grantToolId} onChange={e => setGrantToolId(e.target.value)}>
            <option value="">Select tool</option>
            {tools?.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
          <button onClick={() => grantMutation.mutate()} disabled={!grantToolId || !grantUserId}>Grant</button>
        </div>
      </div>

      <div className="card">
        <h3>Tool Access</h3>
        <table style={{ width: '100%', marginTop: 12, borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>
              <th style={{ padding: 8 }}>User</th>
              <th style={{ padding: 8 }}>Tool</th>
              <th style={{ padding: 8 }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {accessList?.map(({ access, tool_name, user_name }) => (
              <tr key={access.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: 8 }}>{user_name}</td>
                <td style={{ padding: 8 }}>{tool_name}</td>
                <td style={{ padding: 8 }}>
                  <span className={`badge badge-${access.provisioning_status === 'ACTIVE' ? 'active' : access.provisioning_status === 'FAILED' ? 'failed' : 'provisioning'}`}>
                    {access.provisioning_status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
