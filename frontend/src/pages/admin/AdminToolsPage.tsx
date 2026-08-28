import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

const CATEGORIES = [
  { value: 'annotation', label: 'Annotation & Labeling', hint: 'CV datasets, bounding boxes, segmentation' },
  { value: 'simulation', label: 'Simulation & Robotics', hint: 'Physics sims, digital twins, Isaac environments' },
  { value: 'protocol', label: 'Protocol Execution', hint: 'Wet-lab SOPs, experiment tracking' },
  { value: 'data_pipeline', label: 'Data Pipeline', hint: 'ETL, batch processing, dataset transforms' },
];

export default function AdminToolsPage() {
  const { orgId, token } = useAuth();
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [category, setCategory] = useState('annotation');
  const [description, setDescription] = useState('');
  const [serviceUrl, setServiceUrl] = useState('');

  const { data: tools } = useQuery({
    queryKey: ['tools', orgId],
    queryFn: () => api<{ id: string; name: string; type: string; status: string; description: string | null }[]>(
      `/organizations/${orgId}/tools`, { orgId, token }
    ),
    enabled: !!orgId,
  });

  const createMutation = useMutation({
    mutationFn: () => api(`/organizations/${orgId}/tools`, {
      method: 'POST',
      body: {
        name,
        category,
        description: description || `${name} integration`,
        service_url: serviceUrl || null,
      },
      orgId, token,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tools'] });
      setName('');
      setDescription('');
      setServiceUrl('');
    },
  });

  const selectedCategory = CATEGORIES.find(c => c.value === category);

  return (
    <div>
      <div className="page-header"><h1>Tool Registry</h1></div>

      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 16 }}>Register New Tool</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 16 }}>
          Register a research tool for your organization. The platform handles provisioning and launch automatically.
        </p>
        <div className="form-row">
          <label>Tool Name</label>
          <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. CVAT Production" />
        </div>
        <div className="form-row">
          <label>Description</label>
          <input value={description} onChange={e => setDescription(e.target.value)} placeholder="What this tool is used for" />
        </div>
        <div className="form-row">
          <label>Tool Category</label>
          <select value={category} onChange={e => setCategory(e.target.value)}>
            {CATEGORIES.map(c => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
          {selectedCategory && (
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{selectedCategory.hint}</p>
          )}
        </div>
        <div className="form-row">
          <label>Service URL</label>
          <input
            value={serviceUrl}
            onChange={e => setServiceUrl(e.target.value)}
            placeholder="https://tools.your-org.example.com/cvat"
          />
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
            Where the tool is hosted. Used for launch redirects and health checks.
          </p>
        </div>
        <button style={{ marginTop: 8 }} disabled={!name || createMutation.isPending} onClick={() => createMutation.mutate()}>
          Register Tool
        </button>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 16 }}>Registered Tools</h3>
        <table>
          <thead>
            <tr><th>Name</th><th>Category</th><th>Status</th><th>Description</th></tr>
          </thead>
          <tbody>
            {tools?.map(t => (
              <tr key={t.id}>
                <td>{t.name}</td>
                <td className="mono">{t.type}</td>
                <td><span className="badge badge-active">{t.status}</span></td>
                <td>{t.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
