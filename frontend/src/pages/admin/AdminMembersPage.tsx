/** Admin Members: org roster, invites, and inline Manage Labs (role changes). */
import { Fragment, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

interface LabAssignment {
  membership_id: string;
  lab_id: string;
  lab_name: string;
  lab_role: string;
}

interface RosterEntry {
  membership_id: string;
  user_id: string;
  name: string;
  email: string;
  org_role: string;
  status: string;
  labs: LabAssignment[];
}

export default function AdminMembersPage() {
  const { orgId, token } = useAuth();
  const queryClient = useQueryClient();
  const [section, setSection] = useState<'roster' | 'invites'>('roster');
  const [expandedUser, setExpandedUser] = useState<string | null>(null);
  const [addLabByUser, setAddLabByUser] = useState<Record<string, { labId: string; role: string }>>({});

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
    mutationFn: ({ userId, labId, labRole }: { userId: string; labId: string; labRole: string }) =>
      api(`/organizations/${orgId}/labs/${labId}/members`, {
        method: 'POST', body: { user_id: userId, lab_role: labRole }, orgId, token,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['roster'] }),
  });

  const updateLabRoleMutation = useMutation({
    mutationFn: ({ labId, membershipId, lab_role }: { labId: string; membershipId: string; lab_role: string }) =>
      api(`/organizations/${orgId}/labs/${labId}/members/${membershipId}`, {
        method: 'PATCH', body: { lab_role }, orgId, token,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['roster'] }),
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

  const labsNotAssigned = (member: RosterEntry) =>
    labs?.filter(l => !member.labs.some(ml => ml.lab_id === l.id)) || [];

  return (
    <div>
      <div className="page-header"><h1>Members</h1></div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        <button className={section === 'roster' ? '' : 'secondary'} onClick={() => setSection('roster')}>Org Roster</button>
        <button className={section === 'invites' ? '' : 'secondary'} onClick={() => setSection('invites')}>Invitations</button>
      </div>

      {section === 'roster' && (
        <div className="card">
          <h3 style={{ marginBottom: 8 }}>Organization Roster</h3>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
            Set org-level role and manage each member&apos;s lab assignments. A member can hold different roles in different labs.
          </p>
          <table>
            <thead>
              <tr><th>Name</th><th>Email</th><th>Org Role</th><th>Lab Assignments</th><th></th></tr>
            </thead>
            <tbody>
              {roster?.map(r => (
                <Fragment key={r.user_id}>
                  <tr>
                    <td>{r.name}</td>
                    <td className="mono">{r.email}</td>
                    <td>
                      <select
                        value={r.org_role}
                        onChange={e => orgRoleMutation.mutate({ id: r.membership_id, org_role: e.target.value })}
                        disabled={r.email === 'marcus@corvinus.dev' && r.org_role === 'ADMIN'}
                      >
                        <option value="ADMIN">Admin</option>
                        <option value="MEMBER">Member</option>
                      </select>
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {r.labs.map(l => (
                          <span key={l.lab_id} className={`badge badge-${l.lab_role === 'MANAGER' ? 'manager' : 'contributor'}`}>
                            {l.lab_name}: {l.lab_role}
                          </span>
                        ))}
                        {!r.labs.length && <span style={{ color: 'var(--text-muted)' }}>No labs</span>}
                      </div>
                    </td>
                    <td>
                      <button className="sm secondary" onClick={() => setExpandedUser(expandedUser === r.user_id ? null : r.user_id)}>
                        {expandedUser === r.user_id ? 'Close' : 'Manage Labs'}
                      </button>
                    </td>
                  </tr>
                  {expandedUser === r.user_id && (
                    <tr>
                      <td colSpan={5} style={{ background: 'var(--bg-elevated)', padding: 16 }}>
                        <div style={{ marginBottom: 16 }}>
                          <strong>Current lab roles</strong>
                          {r.labs.length === 0 && <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Not assigned to any lab yet.</p>}
                          {r.labs.map(l => (
                            <div key={l.membership_id} style={{ display: 'flex', gap: 12, alignItems: 'center', marginTop: 8 }}>
                              <span style={{ minWidth: 140 }}>{l.lab_name}</span>
                              <select
                                value={l.lab_role}
                                onChange={e => updateLabRoleMutation.mutate({
                                  labId: l.lab_id, membershipId: l.membership_id, lab_role: e.target.value,
                                })}
                              >
                                <option value="MANAGER">Manager</option>
                                <option value="CONTRIBUTOR">Contributor</option>
                              </select>
                            </div>
                          ))}
                        </div>
                        {r.org_role === 'MEMBER' && labsNotAssigned(r).length > 0 && (
                          <div>
                            <strong>Add to lab</strong>
                            <div style={{ display: 'flex', gap: 8, marginTop: 8, alignItems: 'end' }}>
                              <div className="form-row" style={{ flex: 1 }}>
                                <label>Lab</label>
                                <select
                                  value={addLabByUser[r.user_id]?.labId || ''}
                                  onChange={e => setAddLabByUser(prev => ({
                                    ...prev, [r.user_id]: { ...prev[r.user_id], labId: e.target.value, role: prev[r.user_id]?.role || 'CONTRIBUTOR' },
                                  }))}
                                >
                                  <option value="">Select lab</option>
                                  {labsNotAssigned(r).map(l => (
                                    <option key={l.id} value={l.id}>{l.name}</option>
                                  ))}
                                </select>
                              </div>
                              <div className="form-row" style={{ width: 160 }}>
                                <label>Role</label>
                                <select
                                  value={addLabByUser[r.user_id]?.role || 'CONTRIBUTOR'}
                                  onChange={e => setAddLabByUser(prev => ({
                                    ...prev, [r.user_id]: { ...prev[r.user_id], role: e.target.value, labId: prev[r.user_id]?.labId || '' },
                                  }))}
                                >
                                  <option value="MANAGER">Manager</option>
                                  <option value="CONTRIBUTOR">Contributor</option>
                                </select>
                              </div>
                              <button
                                className="sm"
                                disabled={!addLabByUser[r.user_id]?.labId || addLabMemberMutation.isPending}
                                onClick={() => {
                                  const sel = addLabByUser[r.user_id];
                                  if (!sel?.labId) return;
                                  addLabMemberMutation.mutate({ userId: r.user_id, labId: sel.labId, labRole: sel.role || 'CONTRIBUTOR' });
                                }}
                              >
                                Add
                              </button>
                            </div>
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
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
