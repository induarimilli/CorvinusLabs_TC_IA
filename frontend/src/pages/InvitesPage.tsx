import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';

export default function InvitesPage() {
  const { orgId, token } = useAuth();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState('');
  const [labId, setLabId] = useState('');
  const [labRole, setLabRole] = useState('CONTRIBUTOR');
  const [inviteLink, setInviteLink] = useState('');
  const [error, setError] = useState('');

  const { data: labs } = useQuery({
    queryKey: ['labs', orgId],
    queryFn: () => api<{ id: string; name: string }[]>(`/organizations/${orgId}/labs`, { orgId, token }),
    enabled: !!orgId,
  });

  const { data: invitations } = useQuery({
    queryKey: ['invitations', orgId],
    queryFn: () => api<{ id: string; email: string; lab_role: string; status: string; invite_link: string | null }[]>(
      `/organizations/${orgId}/invitations`, { orgId, token }
    ),
    enabled: !!orgId,
  });

  const createMutation = useMutation({
    mutationFn: () => api<{ invite_link: string }>(`/organizations/${orgId}/invitations`, {
      method: 'POST',
      body: { email, lab_id: labId, lab_role: labRole },
      orgId, token,
    }),
    onSuccess: (data) => {
      setInviteLink(data.invite_link);
      setError('');
      queryClient.invalidateQueries({ queryKey: ['invitations'] });
    },
    onError: (e: Error) => setError(e.message),
  });

  return (
    <div>
      <div className="page-header"><h1>Invitations</h1></div>

      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 16 }}>Invite to Lab (Admin only)</h3>
        {error && <div className="error-banner">{error}</div>}
        <div className="form-row">
          <label>Email</label>
          <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="user@example.com" />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div className="form-row">
            <label>Lab</label>
            <select value={labId} onChange={e => setLabId(e.target.value)}>
              <option value="">Select lab</option>
              {labs?.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </div>
          <div className="form-row">
            <label>Role in lab</label>
            <select value={labRole} onChange={e => setLabRole(e.target.value)}>
              <option value="MANAGER">Manager</option>
              <option value="CONTRIBUTOR">Contributor</option>
            </select>
          </div>
        </div>
        <button
          onClick={() => createMutation.mutate()}
          disabled={!email || !labId || createMutation.isPending}
          style={{ marginTop: 8 }}
        >
          Create Invitation
        </button>
        {inviteLink && (
          <div style={{ marginTop: 16, padding: 12, background: 'var(--bg-elevated)', borderRadius: 'var(--radius)' }}>
            <div className="mono" style={{ marginBottom: 4 }}>Invite link:</div>
            <a href={inviteLink} target="_blank" rel="noreferrer">{inviteLink}</a>
          </div>
        )}
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 16 }}>Pending & Past Invitations</h3>
        <table>
          <thead>
            <tr><th>Email</th><th>Lab Role</th><th>Status</th><th>Link</th></tr>
          </thead>
          <tbody>
            {invitations?.map(inv => (
              <tr key={inv.id}>
                <td>{inv.email}</td>
                <td><span className={`badge badge-${inv.lab_role?.toLowerCase()}`}>{inv.lab_role}</span></td>
                <td className="mono">{inv.status}</td>
                <td>{inv.invite_link ? <a href={inv.invite_link} target="_blank" rel="noreferrer">Open</a> : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
