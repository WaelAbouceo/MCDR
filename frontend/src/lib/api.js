const API_BASE = '/api';

let token = localStorage.getItem('mcdr_token');
let onUnauthorized = null;

export function setToken(t) {
  token = t;
  if (t) localStorage.setItem('mcdr_token', t);
  else localStorage.removeItem('mcdr_token');
}

export function getToken() {
  return token;
}

export function setOnUnauthorized(fn) {
  onUnauthorized = fn;
}

async function request(method, path, { body, params } = {}) {
  const url = new URL(path.startsWith('http') ? path : `${API_BASE}${path}`, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v);
    });
  }

  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(url.toString(), {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    if (onUnauthorized) onUnauthorized();
    throw new Error('Session expired');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get: (path, params) => request('GET', path, { params }),
  post: (path, body) => request('POST', path, { body }),
  patch: (path, body) => request('PATCH', path, { body }),
  delete: (path) => request('DELETE', path),
};

export async function login(username, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Login failed');
  }

  const data = await res.json();
  setToken(data.access_token);
  return data;
}

export async function getMe() {
  return api.get('/users/me');
}

export const cases = {
  list: (params) => api.get('/cases', params),
  get: (id) => api.get(`/cases/${id}`),
  create: (body) => api.post('/cases', body),
  update: (id, body) => api.patch(`/cases/${id}`, body),
  addNote: (id, body) => api.post(`/cases/${id}/notes`, body),
  markFirstResponse: (id) => api.post(`/cases/${id}/first-response`),
};

export const cx = {
  callStats: () => api.get('/cx/calls/stats'),
  caseStats: () => api.get('/cx/cases/stats'),
  slaStats: () => api.get('/cx/sla/stats'),
  searchCases: (params) => api.get('/cx/cases/search', params),
  getCase: (id) => api.get(`/cx/cases/${id}`),
  getCaseByNumber: (num) => api.get(`/cx/cases/number/${num}`),
  investorCases: (id) => api.get(`/cx/cases/investor/${id}`),
  agentCases: (id, limit) => api.get(`/cx/cases/agent/${id}`, { limit }),
  agentCalls: (id, limit) => api.get(`/cx/calls/agent/${id}`, { limit }),
  investorCalls: (id) => api.get(`/cx/calls/investor/${id}`),
  slBreaches: (caseId) => api.get(`/cx/sla/breaches/${caseId}`),
  escalations: (caseId) => api.get(`/cx/escalations/${caseId}`),
  qaLeaderboard: () => api.get('/cx/qa/leaderboard'),
  agentQa: (id) => api.get(`/cx/qa/agent/${id}`),
  caseQa: (caseId) => api.get(`/cx/qa/case/${caseId}`),
  agentStats: (id) => api.get(`/cx/agents/${id}/stats`),
  agentPerformance: (id) => api.get(`/cx/agents/${id}/performance`),
};

export const registry = {
  investorProfile: (id) => api.get(`/registry/investors/${id}`),
  searchInvestors: (params) => api.get('/registry/investors', params),
  holdings: (id) => api.get(`/registry/investors/${id}/holdings`),
  portfolio: (id) => api.get(`/registry/investors/${id}/portfolio`),
  appUser: (id) => api.get(`/registry/investors/${id}/app-user`),
};

export const escalations = {
  create: (body) => api.post('/escalations', body),
  forCase: (caseId) => api.get(`/escalations/case/${caseId}`),
  rules: () => api.get('/escalations/rules'),
};

export const qa = {
  scorecards: () => api.get('/qa/scorecards'),
  createEvaluation: (body) => api.post('/qa/evaluations', body),
  listEvaluations: (params) => api.get('/qa/evaluations', params),
};

export const audit = {
  logs: (params) => api.get('/audit/logs', params),
  pageView: (page, referrer) => api.post('/audit/page-view', { page, referrer }).catch(() => {}),
};

export const reports = {
  dashboard: (days) => api.get('/reports/dashboard', { days }),
};

export const users = {
  list: () => api.get('/users'),
  roles: () => api.get('/users/roles'),
  update: (id, body) => api.patch(`/users/${id}`, body),
  create: (body) => api.post('/auth/register', body),
};

export const simulate = {
  incomingCall: (ani, queue, agentId) => {
    const params = new URLSearchParams();
    if (ani) params.set('ani', ani);
    if (queue) params.set('queue', queue);
    if (agentId) params.set('agent_id', agentId);
    return api.post(`/simulate/incoming-call?${params.toString()}`);
  },
  pollIncoming: () => api.get('/simulate/incoming'),
  acceptCall: () => api.post('/simulate/incoming/accept'),
  dismissCall: () => api.post('/simulate/incoming/dismiss'),
};
