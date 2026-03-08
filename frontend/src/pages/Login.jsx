import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { setToken } from '../lib/api';
import { useAuth } from '../lib/auth';
const DEMO_USERS = [
  { username: 'agent11', password: 'agent123', label: 'T1 Agent — وكيل', role: 'agent' },
  { username: 'agent1', password: 'agent123', label: 'T2 Senior — وكيل أول', role: 'agent_t2' },
  { username: 'tl1', password: 'lead123', label: 'Team Lead — قائد فريق', role: 'team_lead' },
  { username: 'supervisor1', password: 'super123', label: 'Supervisor — مشرف', role: 'supervisor' },
  { username: 'qa1', password: 'qa1234', label: 'QA — جودة', role: 'qa_analyst' },
  { username: 'admin1', password: 'admin123', label: 'Admin — مدير', role: 'admin' },
];

const ROLE_COLORS = {
  agent: 'border-blue-200 bg-blue-50 hover:border-blue-400',
  agent_t2: 'border-amber-200 bg-amber-50 hover:border-amber-400',
  team_lead: 'border-emerald-200 bg-emerald-50 hover:border-emerald-400',
  supervisor: 'border-purple-200 bg-purple-50 hover:border-purple-400',
  qa_analyst: 'border-teal-200 bg-teal-50 hover:border-teal-400',
  admin: 'border-red-200 bg-red-50 hover:border-red-400',
};

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { setUser } = useAuth();
  const navigate = useNavigate();

  // Clear stale token on mount
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useState(() => { sessionStorage.removeItem('mcdr_token'); setToken(null); });

  const doLogin = async (u, p) => {
    setError('');
    setLoading(true);
    try {
      const loginRes = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: u, password: p }),
      });
      if (!loginRes.ok) {
        const err = await loginRes.json().catch(() => ({}));
        throw new Error(err.detail || 'Invalid credentials');
      }
      const { access_token } = await loginRes.json();
      setToken(access_token);

      const meRes = await fetch('/api/users/me', {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      if (!meRes.ok) throw new Error('Failed to load profile');
      const me = await meRes.json();
      me.role_name = me.role?.name || 'agent';
      setUser(me);
      navigate('/dashboard');
    } catch (e) {
      setError(e.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    doLogin(username, password);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <img src="/mcdr-logo.svg" alt="MCDR" className="w-20 h-20 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-white">MCDR CX Platform</h1>
          <p className="text-indigo-300 mt-2">GoChat247 — منصة خدمة العملاء</p>
        </div>

        <div className="card p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="input"
                placeholder="Enter username"
                required
              />
            </div>
            <div>
              <label className="label">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                placeholder="Enter password"
                required
              />
            </div>
            {error && (
              <div className="text-sm text-red-600 bg-red-50 rounded-lg p-3">{error}</div>
            )}
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-slate-200">
            <p className="text-xs text-slate-500 mb-3 text-center">Quick login as demo user</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {DEMO_USERS.map((u) => (
                <button
                  key={u.username}
                  onClick={() => doLogin(u.username, u.password)}
                  disabled={loading}
                  className={`text-left p-3 rounded-lg border-2 transition-colors text-sm ${ROLE_COLORS[u.role]}`}
                >
                  <span className="font-medium block text-slate-800">{u.label}</span>
                  <span className="text-slate-500 text-xs">{u.username}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
