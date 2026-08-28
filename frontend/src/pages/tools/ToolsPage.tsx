/**
 * App Launcher: Research Tools (lab catalog Launch/Request) + Google Workspace tab.
 * Managers of the active lab see Launch on all tools; contributors follow policies.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

interface Tool {
  id: string;
  name: string;
  description: string | null;
  type: string;
  status: string;
}

interface ToolAccess {
  id: string;
  tool_id: string;
  provisioning_status: string;
}

interface ToolCatalogItem {
  tool: Tool;
  access_mode: string;
  access: ToolAccess | null;
  can_launch: boolean;
  can_request: boolean;
}

interface GoogleWorkspace {
  id: string;
  lab_id: string;
  lab_name?: string;
  drive_url: string | null;
  calendar_id: string | null;
  chat_space_url: string | null;
  meet_url: string | null;
  provisioning_status: string;
}

interface ToolSession {
  tool_id: string;
  tool_name: string;
  tool_type: string;
  launch_url: string;
  status: string;
  session: Record<string, unknown>;
}

type WorkspaceApp = 'drive' | 'calendar' | 'chat' | 'meet';

function StatusBadge({ status }: { status: string }) {
  const cls = {
    ACTIVE: 'badge-active',
    FAILED: 'badge-failed',
    PROVISIONING: 'badge-provisioning',
    REQUESTED: 'badge-requested',
    PENDING_APPROVAL: 'badge-requested',
  }[status] || '';
  return <span className={`badge ${cls}`}>{status === 'PENDING_APPROVAL' ? 'PENDING' : status}</span>;
}

const WORKSPACE_APPS: { id: WorkspaceApp; label: string; icon: string; color: string }[] = [
  { id: 'drive', label: 'Drive', icon: '📁', color: '#4285f4' },
  { id: 'calendar', label: 'Calendar', icon: '📅', color: '#0f9d58' },
  { id: 'chat', label: 'Chat', icon: '💬', color: '#34a853' },
  { id: 'meet', label: 'Meet', icon: '🎥', color: '#ea4335' },
];

function WorkspaceAppPanel({
  app, orgId, labId, token, labName, ws, onClose,
}: {
  app: WorkspaceApp;
  orgId: string;
  labId: string;
  token: string | null;
  labName: string;
  ws: GoogleWorkspace;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const base = `/organizations/${orgId}/labs/${labId}/google-workspace`;

  const { data: driveFiles } = useQuery({
    queryKey: ['gw-drive', labId],
    queryFn: () => api<{ id: string; name: string; type: string; updated_at: string; url: string }[]>(`${base}/drive/files`, { orgId, labId, token }),
    enabled: app === 'drive',
  });

  const { data: events } = useQuery({
    queryKey: ['gw-calendar', labId],
    queryFn: () => api<{ id: string; title: string; start: string; attendees: number }[]>(`${base}/calendar/events`, { orgId, labId, token }),
    enabled: app === 'calendar',
  });

  const { data: messages } = useQuery({
    queryKey: ['gw-chat', labId],
    queryFn: () => api<{ id: string; author: string; content: string; created_at: string }[]>(`${base}/chat/messages`, { orgId, labId, token }),
    enabled: app === 'chat',
  });

  const [chatText, setChatText] = useState('');
  const chatMutation = useMutation({
    mutationFn: () => api(`${base}/chat/messages`, { method: 'POST', body: { content: chatText }, orgId, labId, token }),
    onSuccess: () => {
      setChatText('');
      queryClient.invalidateQueries({ queryKey: ['gw-chat', labId] });
    },
  });

  const meetMutation = useMutation({
    mutationFn: () => api<{ meet_url: string; join_code: string; status: string; participants: number }>(`${base}/meet/start`, { method: 'POST', orgId, labId, token }),
    onSuccess: (data) => window.open(data.meet_url, '_blank'),
  });

  return (
    <div className="card" style={{ marginTop: 16, borderColor: 'var(--accent)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3>{WORKSPACE_APPS.find(a => a.id === app)?.label} — {labName}</h3>
        <button className="sm secondary" onClick={onClose}>Close</button>
      </div>
      <p className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12 }}>
        API: {base}/{app === 'drive' ? 'drive/files' : app === 'calendar' ? 'calendar/events' : app === 'chat' ? 'chat/messages' : 'meet/start'}
      </p>

      {app === 'drive' && (
        <div>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>
            Shared drive: <a href={ws.drive_url || '#'} target="_blank" rel="noreferrer">{ws.drive_url}</a>
          </p>
          <table>
            <thead><tr><th>Name</th><th>Type</th><th>Modified</th></tr></thead>
            <tbody>
              {driveFiles?.map(f => (
                <tr key={f.id}>
                  <td>{f.type === 'folder' ? '📁' : '📄'} {f.name}</td>
                  <td className="mono">{f.type}</td>
                  <td className="mono" style={{ color: 'var(--text-muted)', fontSize: 11 }}>{f.updated_at.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {app === 'calendar' && (
        <div style={{ display: 'grid', gap: 8 }}>
          {events?.map(e => (
            <div key={e.id} style={{ padding: 12, background: 'var(--bg-elevated)', borderRadius: 'var(--radius)' }}>
              <div style={{ fontWeight: 600 }}>{e.title}</div>
              <div className="mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>{e.start} · {e.attendees} attendees</div>
            </div>
          ))}
        </div>
      )}

      {app === 'chat' && (
        <div>
          <div style={{ display: 'grid', gap: 8, marginBottom: 12 }}>
            {messages?.map(m => (
              <div key={m.id} style={{ padding: 8, background: 'var(--bg-elevated)', borderRadius: 'var(--radius)' }}>
                <div style={{ fontWeight: 600, fontSize: 12 }}>{m.author} <span className="mono" style={{ color: 'var(--text-muted)' }}>{m.created_at}</span></div>
                <div style={{ fontSize: 13 }}>{m.content}</div>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <input value={chatText} onChange={e => setChatText(e.target.value)} placeholder="Message the lab..." style={{ flex: 1 }} />
            <button className="sm" disabled={!chatText || chatMutation.isPending} onClick={() => chatMutation.mutate()}>Send</button>
          </div>
        </div>
      )}

      {app === 'meet' && (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>🎥</div>
          <p style={{ marginBottom: 8 }}>Instant meeting for <strong>{labName}</strong></p>
          <p className="mono" style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>{ws.meet_url}</p>
          <button onClick={() => meetMutation.mutate()} disabled={meetMutation.isPending}>Start Meeting (API)</button>
        </div>
      )}
    </div>
  );
}

function ToolSessionPanel({ session, onClose }: { session: ToolSession; onClose: () => void }) {
  const s = session.session;
  return (
    <div className="card" style={{ marginTop: 16, borderColor: 'var(--accent)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <h3>{session.tool_name} Session</h3>
        <button className="sm secondary" onClick={onClose}>Close</button>
      </div>
      <p className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12 }}>
        Connector: {session.tool_type} · API: GET /tools/{session.tool_id}/session
      </p>
      {session.tool_type === 'isaac_sim' && (
        <div style={{ display: 'grid', gap: 8 }}>
          <div><strong>Scene:</strong> <span className="mono">{String(s.scene)}</span></div>
          <div><strong>GPU:</strong> <span className="mono">{String(s.gpu)}</span></div>
          <div><strong>Robots:</strong> <span className="mono">{(s.robots as string[])?.join(', ')}</span></div>
          <div><strong>Status:</strong> <span className="badge badge-active">{String(s.status)}</span></div>
        </div>
      )}
      {session.tool_type === 'cvat' && (
        <div>
          <strong>Projects</strong>
          <table style={{ marginTop: 8 }}>
            <thead><tr><th>Project</th><th>Tasks</th><th>Done</th></tr></thead>
            <tbody>
              {(s.projects as { name: string; tasks: number; completed: number }[])?.map(p => (
                <tr key={p.name}><td>{p.name}</td><td className="mono">{p.tasks}</td><td className="mono">{p.completed}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {session.tool_type === 'protocol_tool' && (
        <div>
          <strong>Protocols</strong>
          {(s.protocols as { name: string; version: string }[])?.map(p => (
            <div key={p.name} style={{ padding: 8, background: 'var(--bg-elevated)', marginTop: 4, borderRadius: 'var(--radius)' }}>
              {p.name} <span className="mono">v{p.version}</span>
            </div>
          ))}
        </div>
      )}
      <button style={{ marginTop: 16 }} onClick={() => window.open(session.launch_url, '_blank')}>Open External Tool</button>
    </div>
  );
}

export default function ToolsPage() {
  const { orgId, labId, token } = useAuth();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<'tools' | 'google'>('tools');
  const [activeApp, setActiveApp] = useState<WorkspaceApp | null>(null);
  const [adminViewLab, setAdminViewLab] = useState('');
  const [activeSession, setActiveSession] = useState<ToolSession | null>(null);

  const { data: me } = useQuery({
    queryKey: ['me'],
    queryFn: () => api<{
      memberships: { organization_id: string; org_role: string }[];
      lab_memberships: { lab_id: string; organization_id: string; lab_role: string; lab_name: string }[];
    }>('/auth/me'),
  });

  const orgRole = me?.memberships.find(m => m.organization_id === orgId)?.org_role;
  const isAdmin = orgRole === 'ADMIN';
  const currentLabMembership = me?.lab_memberships.find(l => l.organization_id === orgId && l.lab_id === labId);
  const currentLabName = currentLabMembership?.lab_name;

  const isManager = currentLabMembership?.lab_role === 'MANAGER' ||
    (me?.lab_memberships.some(l => l.organization_id === orgId && l.lab_role === 'MANAGER') ?? false);

  const { data: catalog } = useQuery({
    queryKey: ['tools-catalog', orgId, labId],
    queryFn: () => api<ToolCatalogItem[]>(
      `/organizations/${orgId}/labs/${labId}/tools-catalog`,
      { orgId, labId, token }
    ),
    enabled: !!orgId && !!labId && tab === 'tools' && !isAdmin,
    refetchInterval: 3000,
  });

  const { data: googleWs } = useQuery({
    queryKey: ['google-workspace', orgId],
    queryFn: () => api<GoogleWorkspace[]>(`/organizations/${orgId}/google-workspace`, { orgId, token }),
    enabled: !!orgId && tab === 'google',
    refetchInterval: 2000,
  });

  const { data: labs } = useQuery({
    queryKey: ['labs', orgId],
    queryFn: () => api<{ id: string; name: string }[]>(`/organizations/${orgId}/labs`, { orgId, token }),
    enabled: !!orgId && isAdmin && tab === 'google',
  });

  const requestAccessMutation = useMutation({
    mutationFn: (toolId: string) => api(`/tools/${toolId}/access/request`, { method: 'POST', orgId, token }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tools-catalog'] }),
  });

  const sessionMutation = useMutation({
    mutationFn: (toolId: string) => api<ToolSession>(`/tools/${toolId}/session`, { orgId, token }),
    onSuccess: (data) => setActiveSession(data),
  });

  const viewLabId = isAdmin ? (adminViewLab || labs?.[0]?.id || '') : (labId || me?.lab_memberships.find(l => l.organization_id === orgId)?.lab_id || '');
  const labWorkspace = googleWs?.find(w => w.lab_id === viewLabId) || (isAdmin ? googleWs?.[0] : googleWs?.find(w => w.lab_id === labId));
  const displayLabName = labWorkspace?.lab_name || labs?.find(l => l.id === viewLabId)?.name || currentLabName || 'Your lab';

  const renderCatalogCard = (item: ToolCatalogItem) => {
    const { tool, access, access_mode, can_launch, can_request } = item;
    return (
      <div key={tool.id} className="card">
        <h4>{tool.name}</h4>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>{tool.description}</p>
        <span className="mono" style={{ fontSize: 11 }}>{tool.type}</span>
        {access_mode === 'AUTO_ONBOARD' && !isManager && (
          <div style={{ fontSize: 11, color: 'var(--accent)', marginTop: 4 }}>Lab starter tool</div>
        )}
        {access_mode === 'REQUEST' && !isManager && (
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Requires manager approval</div>
        )}
        <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {can_launch && (
            <button className="sm" onClick={() => sessionMutation.mutate(tool.id)} disabled={sessionMutation.isPending}>
              Launch
            </button>
          )}
          {can_request && (
            <button className="sm secondary" onClick={() => requestAccessMutation.mutate(tool.id)} disabled={requestAccessMutation.isPending}>
              Request Access
            </button>
          )}
          {access?.provisioning_status === 'PENDING_APPROVAL' && (
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Awaiting manager approval</span>
          )}
          {access && !can_launch && access.provisioning_status !== 'PENDING_APPROVAL' && access.provisioning_status !== 'ACTIVE' && (
            <StatusBadge status={access.provisioning_status} />
          )}
        </div>
      </div>
    );
  };

  return (
    <div>
      <div className="page-header"><h1>App Launcher</h1></div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {!isAdmin && (
          <button className={tab === 'tools' ? '' : 'secondary'} onClick={() => setTab('tools')}>Research Tools</button>
        )}
        <button className={tab === 'google' ? '' : 'secondary'} onClick={() => { setTab('google'); setActiveApp(null); }}>
          Google Workspace
        </button>
      </div>

      {tab === 'tools' && !isAdmin && (
        <>
          <div className="card" style={{ marginBottom: 24 }}>
            <h3>Research Tools — {currentLabName || 'Your lab'}</h3>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>
              {isManager
                ? 'As a manager, you can launch any tool registered in this organization.'
                : 'Starter tools are provisioned during onboarding. Other tools require a manager approval request.'}
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 16, marginTop: 12 }}>
              {catalog?.map(renderCatalogCard)}
            </div>
          </div>
          {activeSession && (
            <ToolSessionPanel session={activeSession} onClose={() => setActiveSession(null)} />
          )}
        </>
      )}

      {tab === 'tools' && isAdmin && (
        <div className="card">
          <p style={{ color: 'var(--text-muted)' }}>
            Research tools are granted per-user by lab Managers. Use the Google Workspace tab to view lab shared infrastructure,
            or provision workspaces from <a href="/admin/labs">Lab Management</a>.
          </p>
        </div>
      )}

      {tab === 'google' && (
        <div>
          <div className="card" style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <h3>Google Workspace — {displayLabName}</h3>
              {isAdmin && labs && labs.length > 0 && (
                <select value={adminViewLab || labs[0]?.id || ''} onChange={e => { setAdminViewLab(e.target.value); setActiveApp(null); }} style={{ width: 'auto', minWidth: 180 }}>
                  {labs.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
                </select>
              )}
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 16 }}>
              Shared lab infrastructure — Drive, Calendar, Chat, Meet. Managers and Contributors access via API once provisioned.
              {isAdmin && <> Provision from <a href="/admin/labs">Lab Management</a>.</>}
            </p>

            {!labWorkspace && (
              <p style={{ color: 'var(--text-muted)' }}>
                No Google Workspace provisioned for this lab yet.
                {isAdmin && ' Go to Lab Management → Provision Workspace.'}
              </p>
            )}

            {labWorkspace && labWorkspace.provisioning_status !== 'ACTIVE' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <StatusBadge status={labWorkspace.provisioning_status} />
                <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>Provisioning workspace via API hook… (~3 sec)</span>
              </div>
            )}

            {labWorkspace?.provisioning_status === 'ACTIVE' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginTop: 8 }}>
                {WORKSPACE_APPS.map(app => (
                  <button
                    key={app.id}
                    className="secondary"
                    style={{
                      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
                      padding: 24, borderColor: activeApp === app.id ? app.color : 'var(--border)',
                      background: activeApp === app.id ? `${app.color}15` : 'transparent',
                    }}
                    onClick={() => setActiveApp(activeApp === app.id ? null : app.id)}
                  >
                    <span style={{ fontSize: 32 }}>{app.icon}</span>
                    <span style={{ fontWeight: 600 }}>{app.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {activeApp && labWorkspace?.provisioning_status === 'ACTIVE' && viewLabId && (
            <WorkspaceAppPanel
              app={activeApp}
              orgId={orgId!}
              labId={viewLabId}
              token={token}
              labName={displayLabName}
              ws={labWorkspace}
              onClose={() => setActiveApp(null)}
            />
          )}

          {isAdmin && googleWs && googleWs.length > 0 && (
            <div className="card" style={{ marginTop: 16 }}>
              <h4 style={{ marginBottom: 12 }}>All Lab Workspaces</h4>
              <table>
                <thead><tr><th>Lab</th><th>Status</th><th>Drive</th><th>Calendar</th><th>Meet</th></tr></thead>
                <tbody>
                  {googleWs.map(ws => (
                    <tr key={ws.id}>
                      <td>{ws.lab_name}</td>
                      <td><StatusBadge status={ws.provisioning_status} /></td>
                      <td>{ws.drive_url && ws.provisioning_status === 'ACTIVE' ? '✓' : '—'}</td>
                      <td>{ws.calendar_id && ws.provisioning_status === 'ACTIVE' ? '✓' : '—'}</td>
                      <td>{ws.meet_url && ws.provisioning_status === 'ACTIVE' ? '✓' : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
