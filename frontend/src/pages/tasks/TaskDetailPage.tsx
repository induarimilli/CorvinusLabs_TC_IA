import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

interface Task {
  id: string;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  assignee_id: string | null;
  due_date: string | null;
  version: number;
  lab_id: string;
}

interface LabMember {
  user_id: string;
  name: string;
  lab_role: string;
}

const TRANSITIONS: Record<string, string[]> = {
  BACKLOG: ['TODO'],
  TODO: ['IN_PROGRESS', 'BACKLOG'],
  IN_PROGRESS: ['BLOCKED', 'DONE', 'TODO'],
  BLOCKED: ['IN_PROGRESS'],
  DONE: [],
};

const PRIORITIES = ['LOW', 'MEDIUM', 'HIGH', 'URGENT'];

export default function TaskDetailPage() {
  const { taskId } = useParams();
  const { orgId, token } = useAuth();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Partial<Task>>({});
  const [error, setError] = useState('');

  const { data: me } = useQuery({
    queryKey: ['me'],
    queryFn: () => api<{
      memberships: { organization_id: string; org_role: string }[];
      lab_memberships: { lab_id: string; organization_id: string; lab_role: string }[];
    }>('/auth/me'),
  });

  const { data: task, refetch } = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => api<Task>(`/tasks/${taskId}`, { orgId, token }),
    enabled: !!taskId && !!orgId,
  });

  const orgRole = me?.memberships.find(m => m.organization_id === orgId)?.org_role;
  const labRole = task ? me?.lab_memberships.find(l => l.lab_id === task.lab_id && l.organization_id === orgId)?.lab_role : undefined;
  const canEdit = orgRole !== 'ADMIN' && (labRole === 'MANAGER' || labRole === 'CONTRIBUTOR');

  const { data: members } = useQuery({
    queryKey: ['lab-members', orgId, task?.lab_id],
    queryFn: () => api<LabMember[]>(`/organizations/${orgId}/labs/${task!.lab_id}/members`, { orgId, token }),
    enabled: !!orgId && !!task?.lab_id,
  });

  const saveMutation = useMutation({
    mutationFn: (body: object) => api(`/tasks/${taskId}`, { method: 'PATCH', body, orgId, token }),
    onSuccess: () => {
      setEditing(false);
      setError('');
      refetch();
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
    onError: (e: Error) => setError(e.message),
  });

  const startEdit = () => {
    if (!task) return;
    setDraft({
      title: task.title,
      description: task.description || '',
      priority: task.priority,
      assignee_id: task.assignee_id,
      status: task.status,
    });
    setEditing(true);
  };

  const cancelEdit = () => {
    setEditing(false);
    setDraft({});
    setError('');
  };

  const save = () => {
    if (!task) return;
    saveMutation.mutate({
      title: draft.title,
      description: draft.description || null,
      priority: draft.priority,
      assignee_id: draft.assignee_id || null,
      status: draft.status,
      version: task.version,
    });
  };

  if (!task) return <div style={{ color: 'var(--text-muted)' }}>Loading task...</div>;

  const validNext = TRANSITIONS[task.status] || [];

  return (
    <div>
      <div className="page-header">
        <div>
          <Link to="/tasks" style={{ fontSize: 13, color: 'var(--text-muted)' }}>← Task Board</Link>
          <h1 style={{ marginTop: 8 }}>{editing ? 'Edit Task' : task.title}</h1>
        </div>
        {canEdit && !editing && (
          <button onClick={startEdit}>Edit</button>
        )}
        {editing && (
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="secondary" onClick={cancelEdit}>Cancel</button>
            <button onClick={save} disabled={saveMutation.isPending}>Save</button>
          </div>
        )}
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        {!editing ? (
          <div style={{ display: 'grid', gap: 16 }}>
            <div><label className="mono" style={{ color: 'var(--text-muted)' }}>Title</label><div>{task.title}</div></div>
            <div><label className="mono" style={{ color: 'var(--text-muted)' }}>Description</label><div>{task.description || '—'}</div></div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
              <div><label className="mono" style={{ color: 'var(--text-muted)' }}>Status</label><div><span className="badge badge-contributor">{task.status}</span></div></div>
              <div><label className="mono" style={{ color: 'var(--text-muted)' }}>Priority</label><div className="mono">{task.priority}</div></div>
              <div><label className="mono" style={{ color: 'var(--text-muted)' }}>Assignee</label><div>{members?.find(m => m.user_id === task.assignee_id)?.name || 'Unassigned'}</div></div>
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: 16 }}>
            <div className="form-row">
              <label>Title</label>
              <input value={draft.title || ''} onChange={e => setDraft(d => ({ ...d, title: e.target.value }))} />
            </div>
            <div className="form-row">
              <label>Description</label>
              <textarea value={draft.description || ''} onChange={e => setDraft(d => ({ ...d, description: e.target.value }))} rows={3} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
              <div className="form-row">
                <label>Priority</label>
                <select value={draft.priority || 'MEDIUM'} onChange={e => setDraft(d => ({ ...d, priority: e.target.value }))}>
                  {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div className="form-row">
                <label>Status</label>
                <select value={draft.status || task.status} onChange={e => setDraft(d => ({ ...d, status: e.target.value }))}>
                  {[task.status, ...validNext].filter((v, i, a) => a.indexOf(v) === i).map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div className="form-row">
                <label>Assignee</label>
                <select value={draft.assignee_id || ''} onChange={e => setDraft(d => ({ ...d, assignee_id: e.target.value || null }))}>
                  <option value="">Unassigned</option>
                  {members?.map(m => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}
                </select>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
