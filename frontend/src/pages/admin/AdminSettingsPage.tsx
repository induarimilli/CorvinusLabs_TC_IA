import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

export default function AdminSettingsPage() {
  const { orgId, token } = useAuth();
  const queryClient = useQueryClient();

  const { data: settings } = useQuery({
    queryKey: ['settings', orgId],
    queryFn: () => api<{ timezone: string; date_format: string; time_format: string }>(
      `/organizations/${orgId}/settings`, { orgId, token }
    ),
    enabled: !!orgId,
  });

  const [timezone, setTimezone] = useState('');
  const [dateFormat, setDateFormat] = useState('');

  useState(() => {
    if (settings) {
      setTimezone(settings.timezone);
      setDateFormat(settings.date_format);
    }
  });

  const updateMutation = useMutation({
    mutationFn: () => api(`/organizations/${orgId}/settings`, {
      method: 'PATCH', body: { timezone: timezone || settings?.timezone, date_format: dateFormat || settings?.date_format }, orgId, token,
    }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['settings'] }),
  });

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>Organization Settings</h1>
      <div className="card">
        <div style={{ marginBottom: 12 }}>
          <label>Timezone</label>
          <input defaultValue={settings?.timezone} onChange={e => setTimezone(e.target.value)} />
        </div>
        <div style={{ marginBottom: 12 }}>
          <label>Date Format</label>
          <input defaultValue={settings?.date_format} onChange={e => setDateFormat(e.target.value)} />
        </div>
        <div style={{ marginBottom: 12 }}>
          <label>Time Format</label>
          <input defaultValue={settings?.time_format} disabled />
        </div>
        <button onClick={() => updateMutation.mutate()}>Save Settings</button>
      </div>
    </div>
  );
}
