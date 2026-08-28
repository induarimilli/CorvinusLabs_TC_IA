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
  user_id: string;
  access_level: string;
  provisioning_status: string;
  failure_reason: string | null;
}

interface MyTool {
  tool: Tool;
  access: ToolAccess;
}

function StatusBadge({ status }: { status: string }) {
  const cls = {
    ACTIVE: 'badge-active',
    FAILED: 'badge-failed',
    PROVISIONING: 'badge-provisioning',
    REQUESTED: 'badge-requested',
    REVOKED: 'badge-failed',
  }[status] || '';
  return <span className={`badge ${cls}`}>{status}</span>;
}

export default function ToolsPage() {
  const { orgId, token, user } = useAuth();
  const queryClient = useQueryClient();

  const { data: me } = useQuery({
    queryKey: ['me'],
    queryFn: () => api<{ memberships: { organization_id: string; role_name: string }[] }>('/auth/me'),
  });
  const roleName = me?.memberships.find(m => m.organization_id === orgId)?.role_name;

  const { data: tools } = useQuery({
    queryKey: ['tools', orgId],
    queryFn: () => api<Tool[]>(`/organizations/${orgId}/tools`, { orgId, token }),
    enabled: !!orgId,
  });

  const { data: myTools, refetch: refetchMyTools } = useQuery({
    queryKey: ['my-tools', orgId],
    queryFn: () => api<MyTool[]>(`/organizations/${orgId}/my-tools`, { orgId, token }),
    enabled: !!orgId,
    refetchInterval: 3000,
  });

  const requestMutation = useMutation({
    mutationFn: (toolId: string) => api(`/tools/${toolId}/access/request`, { method: 'POST', orgId, token }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['my-tools'] }); },
  });

  const launchMutation = useMutation({
    mutationFn: (toolId: string) => api<{ launch_url: string }>(`/tools/${toolId}/launch`, { method: 'POST', orgId, token }),
    onSuccess: (data) => window.open(data.launch_url, '_blank'),
  });

  const myToolIds = new Set(myTools?.map(mt => mt.tool.id));

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>App Launcher</h1>

      {myTools && myTools.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3>My Tools</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 16, marginTop: 12 }}>
            {myTools.map(({ tool, access }) => (
              <div key={tool.id} className="card" style={{ border: '1px solid #dee2e6' }}>
                <h4>{tool.name}</h4>
                <p style={{ fontSize: 13, color: '#6c757d' }}>{tool.description}</p>
                <StatusBadge status={access.provisioning_status} />
                {access.failure_reason && <p style={{ fontSize: 12, color: '#e63946' }}>{access.failure_reason}</p>}
                {access.provisioning_status === 'ACTIVE' && (
                  <button style={{ marginTop: 8 }} onClick={() => launchMutation.mutate(tool.id)}>Launch</button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <h3>Available Tools</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 16, marginTop: 12 }}>
          {tools?.map(tool => {
            const myAccess = myTools?.find(mt => mt.tool.id === tool.id);
            return (
              <div key={tool.id} className="card" style={{ border: '1px solid #dee2e6' }}>
                <h4>{tool.name}</h4>
                <p style={{ fontSize: 13, color: '#6c757d' }}>{tool.description}</p>
                <span style={{ fontSize: 12, color: '#6c757d' }}>{tool.type}</span>
                {myAccess ? (
                  <div style={{ marginTop: 8 }}>
                    <StatusBadge status={myAccess.access.provisioning_status} />
                    {myAccess.access.provisioning_status === 'ACTIVE' && (
                      <button style={{ marginLeft: 8 }} onClick={() => launchMutation.mutate(tool.id)}>Launch</button>
                    )}
                  </div>
                ) : (
                  <button className="secondary" style={{ marginTop: 8 }}
                    onClick={() => requestMutation.mutate(tool.id)}>Request Access</button>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
