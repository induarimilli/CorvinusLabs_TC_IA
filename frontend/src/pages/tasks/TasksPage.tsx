import { useState } from 'react';
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
  version: number;
  lab_id: string;
}

const COLUMNS = ['BACKLOG', 'TODO', 'IN_PROGRESS', 'BLOCKED', 'DONE'];

export default function TasksPage() {
  const { orgId, labId, token } = useAuth();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');
  const [selectedLab, setSelectedLab] = useState('');

  const { data: me } = useQuery({
    queryKey: ['me'],
    queryFn: () => api<{ memberships: { organization_id: string; role_name: string }[] }>('/auth/me'),
  });
  const roleName = me?.memberships.find(m => m.organization_id === orgId)?.role_name;

  const { data: labs } = useQuery({
    queryKey: ['labs', orgId],
    queryFn: () => api<{ id: string; name: string }[]>(`/organizations/${orgId}/labs`, { orgId, token }),
    enabled: !!orgId,
  });

  const { data: tasks, refetch } = useQuery({
    queryKey: ['tasks', orgId, labId],
    queryFn: () => {
      const params = labId ? `?lab_id=${labId}` : '';
      return api<Task[]>(`/organizations/${orgId}/tasks${params}`, { orgId, labId: labId || undefined, token });
    },
    enabled: !!orgId,
    refetchInterval: 5000,
  });

  const createMutation = useMutation({
    mutationFn: (body: object) => api(`/organizations/${orgId}/tasks`, { method: 'POST', body, orgId, token }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['tasks'] }); setShowForm(false); setTitle(''); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, ...body }: { id: string; status: string; version: number }) =>
      api(`/tasks/${id}`, { method: 'PATCH', body, orgId, token }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api(`/tasks/${id}`, { method: 'DELETE', orgId, token }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }),
  });

  const moveTask = (task: Task, newStatus: string) => {
    updateMutation.mutate({ id: task.id, status: newStatus, version: task.version });
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
        <h1>Tasks</h1>
        {roleName !== 'Contributor' && (
          <button onClick={() => setShowForm(!showForm)}>+ New Task</button>
        )}
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: 24 }}>
          <input placeholder="Task title" value={title} onChange={e => setTitle(e.target.value)} />
          <select value={selectedLab || labId || ''} onChange={e => setSelectedLab(e.target.value)} style={{ marginTop: 8 }}>
            {labs?.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
          </select>
          <button style={{ marginTop: 8 }} onClick={() => createMutation.mutate({
            title, lab_id: selectedLab || labId || labs?.[0]?.id, status: 'BACKLOG', priority: 'MEDIUM'
          })}>Create</button>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, overflowX: 'auto' }}>
        {COLUMNS.map(col => (
          <div key={col} style={{ background: '#e9ecef', borderRadius: 8, padding: 12, minHeight: 400 }}>
            <h4 style={{ marginBottom: 12, fontSize: 13, textTransform: 'uppercase', color: '#6c757d' }}>{col.replace('_', ' ')}</h4>
            {tasks?.filter(t => t.status === col).map(task => (
              <div key={task.id} className="card" style={{ marginBottom: 8, padding: 12 }}>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{task.title}</div>
                <div style={{ fontSize: 12, color: '#6c757d', marginTop: 4 }}>{task.priority}</div>
                <div style={{ marginTop: 8, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {COLUMNS.filter(c => c !== col).map(c => (
                    <button key={c} className="secondary" style={{ fontSize: 11, padding: '2px 6px' }}
                      onClick={() => moveTask(task, c)}>{c.split('_')[0]}</button>
                  ))}
                  {roleName !== 'Contributor' && (
                    <button className="danger" style={{ fontSize: 11, padding: '2px 6px' }}
                      onClick={() => deleteMutation.mutate(task.id)}>Del</button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
