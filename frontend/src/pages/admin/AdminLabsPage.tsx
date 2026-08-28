import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

interface Lab {
  id: string;
  name: string;
  description: string | null;
  archived: boolean;
}

interface GoogleWorkspace {
  id: string;
  lab_id: string;
  provisioning_status: string;
}

export default function AdminLabsPage() {
  const { orgId, token } = useAuth();
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [managerUserId, setManagerUserId] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [message, setMessage] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [showArchived, setShowArchived] = useState(false);

  const { data: labs } = useQuery({
    queryKey: ['labs', orgId, showArchived],
    queryFn: () => api<Lab[]>(
      `/organizations/${orgId}/labs${showArchived ? '?include_archived=true' : ''}`, { orgId, token }
    ),
    enabled: !!orgId,
  });

  const { data: workspaces } = useQuery({
    queryKey: ['google-workspace', orgId],
    queryFn: () => api<GoogleWorkspace[]>(`/organizations/${orgId}/google-workspace`, { orgId, token }),
    enabled: !!orgId,
    refetchInterval: 3000,
  });

  const { data: members } = useQuery({
    queryKey: ['roster', orgId],
    queryFn: () => api<{ user_id: string; name: string; org_role: string }[]>(
      `/organizations/${orgId}/members/roster`, { orgId, token }
    ),
    enabled: !!orgId,
  });

  const createMutation = useMutation({
    mutationFn: () => api(`/organizations/${orgId}/labs`, {
      method: 'POST',
      body: {
        name,
        description: description || null,
        manager_user_id: managerUserId || null,
        invite_manager_email: inviteEmail || null,
      },
      orgId, token,
    }),
    onSuccess: () => {
      setMessage(`Lab "${name}" created.${inviteEmail ? ' Invite link logged on server.' : ''}`);
      setName('');
      setDescription('');
      setManagerUserId('');
      setInviteEmail('');
      queryClient.invalidateQueries({ queryKey: ['labs'] });
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ labId, body }: { labId: string; body: object }) =>
      api(`/labs/${labId}`, { method: 'PATCH', body, orgId, token }),
    onSuccess: () => {
      setEditingId(null);
      queryClient.invalidateQueries({ queryKey: ['labs'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-labs'] });
    },
  });

  const provisionMutation = useMutation({
    mutationFn: (labId: string) =>
      api(`/organizations/${orgId}/labs/${labId}/google-workspace/provision`, { method: 'POST', orgId, token }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['google-workspace'] }),
  });

  const startEdit = (lab: Lab) => {
    setEditingId(lab.id);
    setEditName(lab.name);
    setEditDescription(lab.description || '');
  };

  const wsForLab = (labId: string) => workspaces?.find(w => w.lab_id === labId);

  const activeLabs = labs?.filter(l => !l.archived) || [];
  const archivedLabs = labs?.filter(l => l.archived) || [];

  return (
    <div>
      <div className="page-header"><h1>Lab Management</h1></div>

      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 16 }}>Create Lab</h3>
        <div className="form-row">
          <label>Lab Name</label>
          <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Perception Lab" />
        </div>
        <div className="form-row">
          <label>Description</label>
          <input value={description} onChange={e => setDescription(e.target.value)} />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div className="form-row">
            <label>Assign Existing Member as Manager</label>
            <select value={managerUserId} onChange={e => setManagerUserId(e.target.value)}>
              <option value="">None</option>
              {members?.filter(m => m.org_role === 'MEMBER').map(m => (
                <option key={m.user_id} value={m.user_id}>{m.name}</option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label>Or Invite New Manager by Email</label>
            <input
              type="email"
              value={inviteEmail}
              onChange={e => setInviteEmail(e.target.value)}
              placeholder="manager@example.com"
              disabled={!!managerUserId}
            />
          </div>
        </div>
        <button
          style={{ marginTop: 8 }}
          disabled={!name || createMutation.isPending}
          onClick={() => createMutation.mutate()}
        >
          Create Lab
        </button>
        {message && <p style={{ marginTop: 8, color: 'var(--accent)', fontSize: 13 }}>{message}</p>}
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3>Active Labs</h3>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-muted)' }}>
            <input type="checkbox" checked={showArchived} onChange={e => setShowArchived(e.target.checked)} />
            Show archived
          </label>
        </div>
        <table>
          <thead>
            <tr><th>Name</th><th>Description</th><th>Google Workspace</th><th>Actions</th></tr>
          </thead>
          <tbody>
            {activeLabs.map(l => {
              const ws = wsForLab(l.id);
              return (
                <tr key={l.id}>
                  <td>
                    {editingId === l.id ? (
                      <input value={editName} onChange={e => setEditName(e.target.value)} />
                    ) : l.name}
                  </td>
                  <td>
                    {editingId === l.id ? (
                      <input value={editDescription} onChange={e => setEditDescription(e.target.value)} />
                    ) : (l.description || '—')}
                  </td>
                  <td>
                    {ws ? (
                      <span className={`badge badge-${ws.provisioning_status === 'ACTIVE' ? 'active' : 'provisioning'}`}>
                        {ws.provisioning_status}
                      </span>
                    ) : (
                      <button
                        className="sm secondary"
                        onClick={() => provisionMutation.mutate(l.id)}
                        disabled={provisionMutation.isPending}
                      >
                        Provision Workspace
                      </button>
                    )}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {editingId === l.id ? (
                        <>
                          <button className="sm" onClick={() => updateMutation.mutate({
                            labId: l.id,
                            body: { name: editName, description: editDescription || null },
                          })}>Save</button>
                          <button className="sm secondary" onClick={() => setEditingId(null)}>Cancel</button>
                        </>
                      ) : (
                        <>
                          <button className="sm secondary" onClick={() => startEdit(l)}>Edit</button>
                          <button
                            className="sm secondary"
                            onClick={() => {
                              if (confirm(`Archive "${l.name}"? Members and tasks remain but the lab is hidden.`)) {
                                updateMutation.mutate({ labId: l.id, body: { archived: true } });
                              }
                            }}
                          >
                            Archive
                          </button>
                          <button
                            className="sm danger"
                            onClick={() => {
                              if (confirm(`Delete "${l.name}"? This archives the lab permanently.`)) {
                                updateMutation.mutate({ labId: l.id, body: { archived: true } });
                              }
                            }}
                          >
                            Delete
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {showArchived && archivedLabs.length > 0 && (
        <div className="card">
          <h3 style={{ marginBottom: 16 }}>Archived Labs</h3>
          <table>
            <thead><tr><th>Name</th><th>Description</th><th>Actions</th></tr></thead>
            <tbody>
              {archivedLabs.map(l => (
                <tr key={l.id}>
                  <td>{l.name}</td>
                  <td>{l.description || '—'}</td>
                  <td>
                    <button
                      className="sm secondary"
                      onClick={() => updateMutation.mutate({ labId: l.id, body: { archived: false } })}
                    >
                      Restore
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
