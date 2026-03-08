import { useEffect, useRef, useState, useCallback } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { audit, simulate, cx } from '../lib/api';
import IncomingCall from './IncomingCall';
import {
  LayoutDashboard,
  FolderOpen,
  PhoneCall,
  PhoneOutgoing,
  Users,
  BarChart3,
  Shield,
  ClipboardCheck,
  LogOut,
  AlertTriangle,
  ScrollText,
  Search,
  UserCog,
  Settings,
  FileBarChart,
  BookOpen,
  Menu,
  X,
} from 'lucide-react';

const ROLE_NAV = {
  agent_t1: [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/cases', label: 'My Cases', icon: FolderOpen },
    { to: '/cases/new', label: 'New Case', icon: FolderOpen },
    { to: '/outbound', label: 'Outbound Queue', icon: PhoneOutgoing },
    { to: '/investor-search', label: 'Investor Lookup', icon: Search },
    { to: '/kb', label: 'Knowledge Base', icon: BookOpen },
  ],
  senior_agent: [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/cases', label: 'My Cases', icon: FolderOpen },
    { to: '/cases/new', label: 'New Case', icon: FolderOpen },
    { to: '/outbound', label: 'Outbound Queue', icon: PhoneOutgoing },
    { to: '/escalations', label: 'Escalations', icon: AlertTriangle },
    { to: '/sla', label: 'SLA Monitor', icon: Shield },
    { to: '/investor-search', label: 'Investor Lookup', icon: Search },
    { to: '/kb', label: 'Knowledge Base', icon: BookOpen },
  ],
  supervisor: [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/cases', label: 'All Cases', icon: FolderOpen },
    { to: '/outbound', label: 'Outbound Queue', icon: PhoneOutgoing },
    { to: '/escalations', label: 'Escalations', icon: AlertTriangle },
    { to: '/sla', label: 'SLA Monitor', icon: Shield },
    { to: '/reports', label: 'Reports', icon: FileBarChart },
    { to: '/team', label: 'Team', icon: Users },
    { to: '/simulate', label: 'Simulate Call', icon: PhoneCall },
    { to: '/investor-search', label: 'Investor Lookup', icon: Search },
  ],
  team_lead: [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/cases', label: 'All Cases', icon: FolderOpen },
    { to: '/cases/new', label: 'New Case', icon: FolderOpen },
    { to: '/outbound', label: 'Outbound Queue', icon: PhoneOutgoing },
    { to: '/escalations', label: 'Escalations', icon: AlertTriangle },
    { to: '/sla', label: 'SLA Monitor', icon: Shield },
    { to: '/reports', label: 'Reports', icon: FileBarChart },
    { to: '/team', label: 'Team', icon: Users },
    { to: '/investor-search', label: 'Investor Lookup', icon: Search },
    { to: '/kb', label: 'Knowledge Base', icon: BookOpen },
  ],
  qa_analyst: [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/cases', label: 'Cases', icon: FolderOpen },
    { to: '/qa', label: 'QA Evaluations', icon: ClipboardCheck },
    { to: '/leaderboard', label: 'Leaderboard', icon: BarChart3 },
  ],
  admin: [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/cases', label: 'All Cases', icon: FolderOpen },
    { to: '/outbound', label: 'Outbound Queue', icon: PhoneOutgoing },
    { to: '/escalations', label: 'Escalations', icon: AlertTriangle },
    { to: '/sla', label: 'SLA Monitor', icon: Shield },
    { to: '/reports', label: 'Reports', icon: FileBarChart },
    { to: '/team', label: 'Team', icon: Users },
    { to: '/qa', label: 'QA Evaluations', icon: ClipboardCheck },
    { to: '/leaderboard', label: 'Leaderboard', icon: BarChart3 },
    { to: '/investor-search', label: 'Investor Lookup', icon: Search },
    { separator: true, label: 'Administration' },
    { to: '/admin/users', label: 'User Management', icon: UserCog },
    { to: '/audit', label: 'Audit Trail', icon: ScrollText },
    { to: '/simulate', label: 'Simulate Call', icon: PhoneCall },
  ],
};

function getNavKey(role, tier) {
  if (role === 'agent') return 'agent_t1';
  return role;
}

function getRoleLabel(role, tier) {
  const labels = { agent: 'Agent', senior_agent: 'Senior Agent', team_lead: 'Team Lead', supervisor: 'Supervisor', qa_analyst: 'QA Analyst', admin: 'Administrator' };
  return labels[role] || role;
}

const ROLE_COLORS = {
  agent: 'bg-blue-100 text-blue-700',
  agent_t1: 'bg-blue-100 text-blue-700',
  senior_agent: 'bg-amber-100 text-amber-700',
  team_lead: 'bg-emerald-100 text-emerald-700',
  supervisor: 'bg-purple-100 text-purple-700',
  qa_analyst: 'bg-teal-100 text-teal-700',
  admin: 'bg-red-100 text-red-700',
};

const POLL_INTERVAL_MS = 3000;

const PRESENCE_OPTIONS = [
  { value: 'available', label: 'Available', color: 'bg-green-500' },
  { value: 'on_break', label: 'On Break', color: 'bg-yellow-500' },
  { value: 'acw', label: 'After-Call Work', color: 'bg-blue-500' },
  { value: 'in_call', label: 'In Call', color: 'bg-orange-500' },
  { value: 'training', label: 'Training', color: 'bg-purple-500' },
  { value: 'offline', label: 'Offline', color: 'bg-slate-500' },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const prevPath = useRef(null);
  const role = user?.role_name || 'agent';
  const tier = user?.tier || 'tier1';
  const navKey = getNavKey(role, tier);
  const navItems = ROLE_NAV[navKey] || ROLE_NAV.agent_t1;
  const [incomingCall, setIncomingCall] = useState(null);
  const [presence, setPresence] = useState('offline');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const showPresence = ['agent', 'senior_agent', 'team_lead', 'supervisor'].includes(role);

  useEffect(() => {
    if (user && location.pathname !== prevPath.current) {
      audit.pageView(location.pathname, prevPath.current);
      prevPath.current = location.pathname;
    }
  }, [location.pathname, user]);

  useEffect(() => {
    if (!user || !showPresence) return;
    cx.getPresence(user.id).then(p => setPresence(p?.status || 'offline')).catch(() => {});
    if (presence === 'offline') {
      cx.setPresence(user.id, 'available').then(() => setPresence('available')).catch(() => {});
    }
  }, [user]);  // eslint-disable-line react-hooks/exhaustive-deps

  const handlePresenceChange = async (newStatus) => {
    try {
      await cx.setPresence(user.id, newStatus);
      setPresence(newStatus);
    } catch { /* ignore */ }
  };

  const pollForCalls = useCallback(async () => {
    if (!user || (role !== 'agent' && role !== 'senior_agent')) return;
    try {
      const res = await simulate.pollIncoming();
      if (res?.has_call && res.call) {
        setIncomingCall(res.call);
      }
    } catch {
      // silently ignore poll failures
    }
  }, [user, role]);

  const isAgent = role === 'agent' || role === 'senior_agent';
  useEffect(() => {
    if (!isAgent) return;
    const interval = setInterval(pollForCalls, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [isAgent, pollForCalls]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen">
      {/* Mobile top bar */}
      <header className="fixed top-0 left-0 right-0 h-14 bg-slate-900 text-white flex items-center justify-between px-4 z-30 md:hidden shrink-0">
        <div className="flex items-center gap-2">
          <img src="/mcdr-logo.svg" alt="MCDR" className="w-8 h-8 shrink-0" />
          <span className="text-base font-bold tracking-tight">MCDR CX</span>
        </div>
        <button
          type="button"
          onClick={() => setSidebarOpen(true)}
          className="p-2 rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
          aria-label="Open menu"
        >
          <Menu size={24} />
        </button>
      </header>

      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <button
          type="button"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 bg-black/50 z-20 md:hidden"
          aria-label="Close menu"
        />
      )}

      <aside
        className={`flex flex-col w-64 max-w-[85vw] bg-slate-900 text-white shrink-0 z-30 transition-transform duration-200 ease-out ${
          sidebarOpen ? 'fixed inset-y-0 left-0 top-0 bottom-0' : 'hidden'
        } md:flex md:relative md:inset-auto md:max-w-none md:z-auto`}
      >
        <div className="p-5 border-b border-slate-700 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/mcdr-logo.svg" alt="MCDR" className="w-10 h-10 shrink-0" />
            <div>
              <h1 className="text-lg font-bold tracking-tight leading-tight">MCDR CX</h1>
              <p className="text-slate-400 text-[10px] mt-0.5">GoChat247 — منصة خدمة العملاء</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setSidebarOpen(false)}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 md:hidden"
            aria-label="Close menu"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
          {navItems.map((item, idx) =>
            item.separator ? (
              <div key={item.label} className="pt-4 pb-1 px-3">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  {item.label}
                </span>
                <div className="border-b border-slate-700 mt-1" />
              </div>
            ) : (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/dashboard'}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-600 text-white'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`
                }
              >
                <item.icon size={18} />
                {item.label}
              </NavLink>
            )
          )}
        </nav>

        <div className="p-4 border-t border-slate-700">
          <div className="flex items-center gap-3 mb-3">
            <div className="relative">
              <div className="w-9 h-9 rounded-full bg-indigo-600 flex items-center justify-center text-sm font-bold">
                {user?.full_name?.charAt(0) || 'U'}
              </div>
              {showPresence && (
                <span className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-slate-900 ${
                  PRESENCE_OPTIONS.find(p => p.value === presence)?.color || 'bg-slate-500'
                }`} />
              )}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{user?.full_name}</p>
              <span className={`badge text-[10px] ${ROLE_COLORS[navKey] || ROLE_COLORS[role]}`}>
                {getRoleLabel(role, tier)}
              </span>
            </div>
          </div>
          {showPresence && (
            <select
              value={presence}
              onChange={(e) => handlePresenceChange(e.target.value)}
              className="w-full mb-3 px-2 py-1.5 text-xs rounded-md bg-slate-800 text-slate-300 border border-slate-600 focus:outline-none focus:border-indigo-500"
            >
              {PRESENCE_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          )}
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors w-full"
          >
            <LogOut size={16} />
            Sign Out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto pt-14 md:pt-0 min-w-0">
        <Outlet />
      </main>

      {incomingCall && (
        <IncomingCall
          callData={incomingCall}
          onClose={() => setIncomingCall(null)}
        />
      )}
    </div>
  );
}
