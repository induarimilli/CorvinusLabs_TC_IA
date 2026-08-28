import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

interface Task {
  id: string;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  assignee_id: string | null;
  version: number;
  lab_id: string;
}

interface LabMember {
  user_id: string;
  name: string;
  email: string;
  lab_role: string;
}

const COLUMNS = ['BACKLOG', 'TODO', 'IN_PROGRESS', 'BLOCKED', 'DONE'] as const;

const TRANSITIONS: Record<string, string[]> = {
  BACKLOG: ['TODO'],
  TODO: ['IN_PROGRESS', 'BACKLOG'],
  IN_PROGRESS: ['BLOCKED', 'DONE', 'TODO'],
  BLOCKED: ['IN_PROGRESS'],
  DONE: [],
};

const PRIORITIES = ['LOW', 'MEDIUM', 'HIGH', 'URGENT'];

function TaskCard({
  task, members, roleName, orgId, token, currentUserId, onUpdated,
}: {
  task: Task;
  members: LabMember[];
  roleName: string;
  orgId: string | null;
  token: string | null;
  currentUserId: string | undefined;
  onUpdated: () => void;
}) {
  const [error, setError] = useState('');
  const queryClient = useQueryClient();
  const isManager = roleName === 'Manager';
  const isContributor = roleName === 'Contributor';
  const isAdmin = roleName === 'Admin';
  const canManageTasks = isManager || isContributor;

  const updateMutation = useMutation({
    mutationFn: (body: object) =>
      api(`/tasks/${task.id}`, { method: 'PATCH', body, orgId, token }),
    onSuccess: () => { setError(''); onUpdated(); },
    onError: (e: Error) => setError(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: () => api(`/tasks/${task.id}`, { method: 'DELETE', orgId, token }),
    onSuccess: onUpdated,
  });

  const validNext = TRANSITIONS[task.status] || [];
  const assignee = members.find(m => m.user_id === task.assignee_id);

  const { data: comments } = useQuery({
    queryKey: ['task-comments', task.id],
    queryFn: () => api<{ id: string; content: string; author_id: string; created_at: string }[]>(
      `/tasks/${task.id}/comments`, { orgId, token }
    ),
    enabled: !!canManageTasks && !!orgId,
  });

  const [commentText, setCommentText] = useState('');
  const [fileName, setFileName] = useState('');
  const commentMutation = useMutation({
    mutationFn: () => api(`/tasks/${task.id}/comments`, { method: 'POST', body: { content: commentText }, orgId, token }),
    onSuccess: () => {
      setCommentText('');
      queryClient.invalidateQueries({ queryKey: ['task-comments', task.id] });
    },
  });

  const { data: attachments } = useQuery({
    queryKey: ['task-attachments', task.id],
    queryFn: () => api<{ id: string; file_name: string; file_url: string }[]>(
      `/tasks/${task.id}/attachments`, { orgId, token }
    ),
    enabled: !!(canManageTasks) && !!orgId,
  });

  const attachmentMutation = useMutation({
    mutationFn: () => api(`/tasks/${task.id}/attachments`, {
      method: 'POST', body: { file_name: fileName }, orgId, token,
    }),
    onSuccess: () => {
      setFileName('');
      queryClient.invalidateQueries({ queryKey: ['task-attachments', task.id] });
    },
  });

  return (
    <div className="task-card">
      <div style={{ fontWeight: 600, marginBottom: 4 }}>
        <Link to={`/tasks/${task.id}`} style={{ color: 'inherit' }}>{task.title}</Link>
      </div>
      {assignee && (
        <div className="mono" style={{ marginBottom: 6 }}>→ {assignee.name}</div>
      )}
      {!assignee && task.assignee_id === currentUserId && (
        <div className="mono" style={{ marginBottom: 6 }}>→ You</div>
      )}

      {canManageTasks && (
        <div className="form-row" style={{ marginTop: 8 }}>
          <label>Priority</label>
          <select
            value={task.priority}
            onChange={e => updateMutation.mutate({ priority: e.target.value, version: task.version })}
          >
            {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
      )}
      {!canManageTasks && (
        <span className={`badge badge-${task.priority === 'URGENT' ? 'failed' : 'contributor'}`} style={{ marginBottom: 6, display: 'inline-block' }}>
          {task.priority}
        </span>
      )}

      {canManageTasks && (
        <div className="form-row">
          <label>Assignee</label>
          <select
            value={task.assignee_id || ''}
            onChange={e => updateMutation.mutate({
              assignee_id: e.target.value || null,
              version: task.version,
            })}
          >
            <option value="">Unassigned</option>
            {members.map(m => (
              <option key={m.user_id} value={m.user_id}>{m.name} ({m.lab_role})</option>
            ))}
          </select>
        </div>
      )}

      {canManageTasks && validNext.length > 0 && (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 8 }}>
          {validNext.map(status => (
            <button
              key={status}
              className="sm secondary"
              onClick={() => updateMutation.mutate({ status, version: task.version })}
              disabled={updateMutation.isPending}
            >
              → {status.replace('_', ' ')}
            </button>
          ))}
        </div>
      )}

      {canManageTasks && (
        <button className="sm danger" style={{ marginTop: 8 }} onClick={() => deleteMutation.mutate()}>
          Delete
        </button>
      )}

      {canManageTasks && (
        <div style={{ marginTop: 10, borderTop: '1px solid var(--border)', paddingTop: 8 }}>
          {comments?.map(c => (
            <div key={c.id} style={{ fontSize: 12, marginBottom: 4, color: 'var(--text-secondary)' }}>{c.content}</div>
          ))}
          <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
            <input
              value={commentText}
              onChange={e => setCommentText(e.target.value)}
              placeholder="Add comment..."
              style={{ flex: 1, fontSize: 12 }}
            />
            <button className="sm secondary" disabled={!commentText || commentMutation.isPending} onClick={() => commentMutation.mutate()}>
              Post
            </button>
          </div>
          {attachments && attachments.length > 0 && (
            <div style={{ marginTop: 8 }}>
              {attachments.map(a => (
                <div key={a.id} className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>📎 {a.file_name}</div>
              ))}
            </div>
          )}
          <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
            <input
              value={fileName}
              onChange={e => setFileName(e.target.value)}
              placeholder="Attach file (name)..."
              style={{ flex: 1, fontSize: 12 }}
            />
            <button className="sm secondary" disabled={!fileName || attachmentMutation.isPending} onClick={() => attachmentMutation.mutate()}>
              Attach
            </button>
          </div>
        </div>
      )}

      {error && <div style={{ color: 'var(--danger)', fontSize: 12, marginTop: 6 }}>{error}</div>}
    </div>
  );
}

export default function TasksPage() {
  const { orgId, labId, token, user } = useAuth();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');
  const [priority, setPriority] = useState('MEDIUM');
  const [assigneeId, setAssigneeId] = useState('');
  const [selectedLab, setSelectedLab] = useState('');

  const [adminLabId, setAdminLabId] = useState('');

  const { data: me } = useQuery({
    queryKey: ['me'],
    queryFn: () => api<{
      memberships: { organization_id: string; org_role: string }[];
      lab_memberships: { lab_id: string; organization_id: string; lab_role: string }[];
    }>('/auth/me'),
  });
  const orgRole = me?.memberships.find(m => m.organization_id === orgId)?.org_role || '';
  const isAdmin = orgRole === 'ADMIN';
  const currentLabRole = me?.lab_memberships.find(l => l.organization_id === orgId && l.lab_id === (labId || adminLabId))?.lab_role;
  const roleName = isAdmin ? 'Admin' : currentLabRole === 'MANAGER' ? 'Manager' : currentLabRole === 'CONTRIBUTOR' ? 'Contributor' : 'Member';
  const canManageTasks = !isAdmin && (roleName === 'Manager' || roleName === 'Contributor');

  const { data: labs } = useQuery({
    queryKey: ['labs', orgId],
    queryFn: () => api<{ id: string; name: string }[]>(`/organizations/${orgId}/labs`, { orgId, token }),
    enabled: !!orgId,
  });

  const viewLabId = isAdmin ? (adminLabId || labs?.[0]?.id || '') : (labId || selectedLab || labs?.[0]?.id || '');

  const { data: tasks, refetch } = useQuery({
    queryKey: ['tasks', orgId, viewLabId, isAdmin],
    queryFn: () => {
      const params = viewLabId ? `?lab_id=${viewLabId}` : '';
      return api<Task[]>(`/organizations/${orgId}/tasks${params}`, { orgId, labId: viewLabId || undefined, token });
    },
    enabled: !!orgId,
    refetchInterval: 5000,
  });

  const { data: members } = useQuery({
    queryKey: ['lab-members', orgId, viewLabId],
    queryFn: () => api<LabMember[]>(`/organizations/${orgId}/labs/${viewLabId}/members`, { orgId, token }),
    enabled: !!orgId && !!viewLabId && canManageTasks,
  });

  const createMutation = useMutation({
    mutationFn: (body: object) => api(`/organizations/${orgId}/tasks`, { method: 'POST', body, orgId, token }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setShowForm(false);
      setTitle('');
      setAssigneeId('');
    },
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['tasks'] });

  return (
    <div>
      <div className="page-header">
        <h1>Task Board</h1>
        {canManageTasks && (
          <button onClick={() => setShowForm(!showForm)}>{showForm ? 'Cancel' : '+ New Task'}</button>
        )}
      </div>

      {isAdmin && (
        <>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 16 }}>
            Read-only view — switch labs to inspect each board. Task changes are made by lab Managers and Contributors.
          </p>
          {labs && (
            <div className="card" style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
              <label className="mono" style={{ color: 'var(--text-muted)' }}>Lab</label>
              <select value={adminLabId || labs[0]?.id || ''} onChange={e => setAdminLabId(e.target.value)} style={{ width: 'auto', minWidth: 200 }}>
                {labs.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </div>
          )}
        </>
      )}

      {showForm && canManageTasks && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="form-row">
            <label>Title</label>
            <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Task title" />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            <div className="form-row">
              <label>Lab</label>
              <select value={selectedLab || labId || ''} onChange={e => setSelectedLab(e.target.value)}>
                {labs?.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </div>
            <div className="form-row">
              <label>Priority</label>
              <select value={priority} onChange={e => setPriority(e.target.value)}>
                {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div className="form-row">
              <label>Assignee</label>
              <select value={assigneeId} onChange={e => setAssigneeId(e.target.value)}>
                <option value="">Unassigned</option>
                {members?.map(m => (
                  <option key={m.user_id} value={m.user_id}>{m.name}</option>
                ))}
              </select>
            </div>
          </div>
          <button
            style={{ marginTop: 8 }}
            disabled={!title || createMutation.isPending}
            onClick={() => createMutation.mutate({
              title,
              lab_id: viewLabId,
              priority,
              assignee_id: assigneeId || null,
              status: 'BACKLOG',
            })}
          >
            Create Task
          </button>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, overflowX: 'auto' }}>
        {COLUMNS.map(col => (
          <div key={col} className="kanban-col">
            <div className="kanban-col-header">{col.replace('_', ' ')}</div>
            {tasks?.filter(t => t.status === col).map(task => (
              <TaskCard
                key={task.id}
                task={task}
                members={members || []}
                roleName={roleName}
                orgId={orgId}
                token={token}
                currentUserId={user?.id}
                onUpdated={invalidate}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
