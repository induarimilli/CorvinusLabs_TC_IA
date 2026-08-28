import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

interface RosterEntry {
  membership_id: string;
  user_id: string;
  name: string;
  email: string;
  org_role: string;
  status: string;
  labs: { lab_id: string; lab_name: string; lab_role: string }[];
}

interface LabMember {
  membership_id: string;
  user_id: string;
  name: string;
  email: string;
  lab_role: string;
}

export default function AdminMembersPage() {
  const { orgId, token } = useAuth();
  const queryClient = useQueryClient();
  const [selectedLab, setSelectedLab] = useState('');
  const [addUserId, setAddUserId] = useState('');
  const [addLabRole, setAddLabRole] = useState('CONTRIBUTOR');
  const [section, setSection] = useState<'roster' | 'labs' | 'invites'>('roster');

  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteLabId, setInviteLabId] = useState('');
  const [inviteLabRole, setInviteLabRole] = useState('CONTRIBUTOR');
  const [inviteLink, setInviteLink] = useState('');
  const [inviteError, setInviteError] = useState('');

  const { data: roster } = useQuery({
    queryKey: ['roster', orgId],
    queryFn: () => api<RosterEntry[]>(`/organizations/${orgId}/members/roster`, { orgId, token }),
    enabled: !!orgId,
  });

  const { data: labs } = useQuery({
    queryKey: ['labs', orgId],
    queryFn: () => api<{ id: string; name: string }[]>(`/organizations/${orgId}/labs`, { orgId, token }),
    enabled: !!orgId,
  });

  const activeLab = selectedLab || labs?.[0]?.id || '';

  const { data: labMembers } = useQuery({
    queryKey: ['lab-members', orgId, activeLab],
    queryFn: () => api<LabMember[]>(`/organizations/${orgId}/labs/${activeLab}/members`, { orgId, token }),
    enabled: !!orgId && !!activeLab,
  });

  const { data: invitations } = useQuery({
    queryKey: ['invitations', orgId],
    queryFn: () => api<{ id: string; email: string; lab_role: string; status: string; invite_link: string | null }[]>(
      `/organizations/${orgId}/invitations`, { orgId, token }
    ),
    enabled: !!orgId && section === 'invites',
  });

  const orgRoleMutation = useMutation({
    mutationFn: ({ id, org_role }: { id: string; org_role: string }) =>
      api(`/organizations/${orgId}/members/${id}`, { method: 'PATCH', body: { org_role }, orgId, token }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['roster'] }),
  });

  const addLabMemberMutation = useMutation({
    mutationFn: () => api(`/organizations/${orgId}/labs/${activeLab}/members`, {
      method: 'POST', body: { user_id: addUserId, lab_role: addLabRole }, orgId, token,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lab-members'] });
      queryClient.invalidateQueries({ queryKey: ['roster'] });
      setAddUserId('');
    },
  });

  const updateLabRoleMutation = useMutation({
    mutationFn: ({ membershipId, lab_role }: { membershipId: string; lab_role: string }) =>
      api(`/organizations/${orgId}/labs/${activeLab}/members/${membershipId}`, {
        method: 'PATCH', body: { lab_role }, orgId, token,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lab-members'] });
      queryClient.invalidateQueries({ queryKey: ['roster'] });
    },
  });

  const inviteMutation = useMutation({
    mutationFn: () => api<{ invite_link: string }>(`/organizations/${orgId}/invitations`, {
      method: 'POST',
      body: { email: inviteEmail, lab_id: inviteLabId, lab_role: inviteLabRole },
      orgId, token,
    }),
    onSuccess: (data) => {
      setInviteLink(data.invite_link);
      setInviteError('');
      queryClient.invalidateQueries({ queryKey: ['invitations'] });
    },
    onError: (e: Error) => setInviteError(e.message),
  });

  const membersOnly = roster?.filter(r => r.org_role === 'MEMBER') || [];

  return (
    <div>
      <div className="page-header"><h1>Members</h1></div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        <button className={section === 'roster' ? '' : 'secondary'} onClick={() => setSection('roster')}>Org Roster</button>
        <button className={section === 'labs' ? '' : 'secondary'} onClick={() => setSection('labs')}>Per-Lab</button>
        <button className={section === 'invites' ? '' : 'secondary'} onClick={() => setSection('invites')}>Invitations</button>
      </div>

      {section === 'roster' && (
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Organization Roster</h3>
          <table>
            <thead>
              <tr><th>Name</th><th>Email</th><th>Org Role</th><th>Labs</th><th>Status</th></tr>
            </thead>
            <tbody>
              {roster?.map(r => (
                <tr key={r.user_id}>
                  <td>{r.name}</td>
                  <td className="mono">{r.email}</td>
                  <td>
                    <select
                      value={r.org_role}
                      onChange={e => orgRoleMutation.mutate({ id: r.membership_id, org_role: e.target.value })}
                      disabled={r.org_role === 'ADMIN' && r.email === 'marcus@corvinus.dev'}
                    >
                      <option value="ADMIN">Admin</option>
                      <option value="MEMBER">Member</option>
                    </select>
                  </td>
                  <td className="mono" style={{ fontSize: 12 }}>
                    {r.labs.map(l => `${l.lab_name} (${l.lab_role})`).join(', ') || '—'}
                  </td>
                  <td>{r.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {section === 'labs' && (
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Per-Lab Breakdown</h3>
          <div className="form-row" style={{ maxWidth: 320, marginBottom: 16 }}>
            <label>Lab</label>
            <select value={activeLab} onChange={e => setSelectedLab(e.target.value)}>
              {labs?.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </div>

          <table style={{ marginBottom: 24 }}>
            <thead>
              <tr><th>Name</th><th>Email</th><th>Lab Role</th></tr>
            </thead>
            <tbody>
              {labMembers?.map(m => (
                <tr key={m.membership_id}>
                  <td>{m.name}</td>
                  <td className="mono">{m.email}</td>
                  <td>
                    <select
                      value={m.lab_role}
                      onChange={e => updateLabRoleMutation.mutate({ membershipId: m.membership_id, lab_role: e.target.value })}
                    >
                      <option value="MANAGER">Manager</option>
                      <option value="CONTRIBUTOR">Contributor</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <h4 style={{ marginBottom: 8 }}>Add Existing Member to Lab</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 12, alignItems: 'end' }}>
            <div className="form-row">
              <label>Member</label>
              <select value={addUserId} onChange={e => setAddUserId(e.target.value)}>
                <option value="">Select member</option>
                {membersOnly.map(m => (
                  <option key={m.user_id} value={m.user_id}>{m.name}</option>
                ))}
              </select>
            </div>
            <div className="form-row">
              <label>Role in this lab</label>
              <select value={addLabRole} onChange={e => setAddLabRole(e.target.value)}>
                <option value="MANAGER">Manager</option>
                <option value="CONTRIBUTOR">Contributor</option>
              </select>
            </div>
            <button onClick={() => addLabMemberMutation.mutate()} disabled={!addUserId || addLabMemberMutation.isPending}>
              Add to Lab
            </button>
          </div>
        </div>
      )}

      {section === 'invites' && (
        <>
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 style={{ marginBottom: 16 }}>Invite to Lab</h3>
            {inviteError && <div className="error-banner">{inviteError}</div>}
            <div className="form-row">
              <label>Email</label>
              <input type="email" value={inviteEmail} onChange={e => setInviteEmail(e.target.value)} placeholder="user@example.com" />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-row">
                <label>Lab</label>
                <select value={inviteLabId} onChange={e => setInviteLabId(e.target.value)}>
                  <option value="">Select lab</option>
                  {labs?.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
                </select>
              </div>
              <div className="form-row">
                <label>Role in lab</label>
                <select value={inviteLabRole} onChange={e => setInviteLabRole(e.target.value)}>
                  <option value="MANAGER">Manager</option>
                  <option value="CONTRIBUTOR">Contributor</option>
                </select>
              </div>
            </div>
            <button
              onClick={() => inviteMutation.mutate()}
              disabled={!inviteEmail || !inviteLabId || inviteMutation.isPending}
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
        </>
      )}
    </div>
  );
}
