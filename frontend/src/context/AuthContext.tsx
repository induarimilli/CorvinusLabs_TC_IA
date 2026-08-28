import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { api } from '../api/client';

interface User {
  id: string;
  name: string;
  email: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  orgId: string | null;
  labId: string | null;
  login: (userId: string, organizationId?: string, labId?: string) => Promise<void>;
  logout: () => void;
  setOrgId: (id: string) => void;
  setLabId: (id: string | null) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const stored = localStorage.getItem('user');
    return stored ? JSON.parse(stored) : null;
  });
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  const [orgId, setOrgIdState] = useState<string | null>(() => localStorage.getItem('orgId'));
  const [labId, setLabIdState] = useState<string | null>(() => localStorage.getItem('labId'));

  const login = useCallback(async (userId: string, organizationId?: string, labId?: string) => {
    const res = await api<{
      access_token: string;
      user: User;
      default_organization_id: string;
      default_lab_id: string | null;
    }>('/auth/demo-login', {
      method: 'POST',
      body: { user_id: userId, organization_id: organizationId || undefined },
    });
    localStorage.setItem('token', res.access_token);
    localStorage.setItem('user', JSON.stringify(res.user));
    localStorage.setItem('orgId', organizationId || res.default_organization_id);
    const resolvedLabId = labId || res.default_lab_id;
    if (resolvedLabId) localStorage.setItem('labId', resolvedLabId);
    else localStorage.removeItem('labId');
    setToken(res.access_token);
    setUser(res.user);
    setOrgIdState(organizationId || res.default_organization_id);
    setLabIdState(resolvedLabId);
  }, []);

  const logout = useCallback(() => {
    localStorage.clear();
    setToken(null);
    setUser(null);
    setOrgIdState(null);
    setLabIdState(null);
  }, []);

  const setOrgId = useCallback((id: string) => {
    localStorage.setItem('orgId', id);
    setOrgIdState(id);
    localStorage.removeItem('labId');
    setLabIdState(null);
  }, []);

  const setLabId = useCallback((id: string | null) => {
    if (id) localStorage.setItem('labId', id);
    else localStorage.removeItem('labId');
    setLabIdState(id);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, orgId, labId, login, logout, setOrgId, setLabId }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
