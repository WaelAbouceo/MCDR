import { useEffect, useRef, useState, useCallback } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { audit, simulate } from '../lib/api';
import IncomingCall from './IncomingCall';
import {
  LayoutDashboard,
  FolderOpen,
  PhoneCall,
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
} from 'lucide-react';

const ROLE_NAV = {
  agent: [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/cases', label: 'My Cases', icon: FolderOpen },
    { to: '/cases/new', label: 'New Case', icon: FolderOpen },
    { to: '/investor-search', label: 'Investor Lookup', icon: Search },
  ],
  supervisor: [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/cases', label: 'All Cases', icon: FolderOpen },
    { to: '/escalations', label: 'Escalations', icon: AlertTriangle },
    { to: '/sla', label: 'SLA Monitor', icon: Shield },
    { to: '/team', label: 'Team', icon: Users },
    { to: '/simulate', label: 'Simulate Call', icon: PhoneCall },
    { to: '/investor-search', label: 'Investor Lookup', icon: Search },
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
    { to: '/escalations', label: 'Escalations', icon: AlertTriangle },
    { to: '/sla', label: 'SLA Monitor', icon: Shield },
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

const ROLE_LABELS = {
  agent: 'Agent',
  supervisor: 'Supervisor',
  qa_analyst: 'QA Analyst',
  admin: 'Administrator',
};

const ROLE_COLORS = {
  agent: 'bg-blue-100 text-blue-700',
  supervisor: 'bg-purple-100 text-purple-700',
  qa_analyst: 'bg-teal-100 text-teal-700',
  admin: 'bg-red-100 text-red-700',
};

const POLL_INTERVAL_MS = 3000;

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const prevPath = useRef(null);
  const role = user?.role_name || 'agent';
  const navItems = ROLE_NAV[role] || ROLE_NAV.agent;
  const [incomingCall, setIncomingCall] = useState(null);

  useEffect(() => {
    if (user && location.pathname !== prevPath.current) {
      audit.pageView(location.pathname, prevPath.current);
      prevPath.current = location.pathname;
    }
  }, [location.pathname, user]);

  const pollForCalls = useCallback(async () => {
    if (!user || role !== 'agent') return;
    try {
      const res = await simulate.pollIncoming();
      if (res?.has_call && res.call) {
        setIncomingCall(res.call);
      }
    } catch {
      // silently ignore poll failures
    }
  }, [user, role]);

  useEffect(() => {
    if (role !== 'agent') return;
    const interval = setInterval(pollForCalls, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [role, pollForCalls]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen">
      <aside className="w-64 bg-slate-900 text-white flex flex-col shrink-0">
        <div className="p-5 border-b border-slate-700">
          <h1 className="text-lg font-bold tracking-tight">MCDR Case Manager</h1>
          <p className="text-slate-400 text-xs mt-1">GoChat247 CX Platform</p>
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
            <div className="w-9 h-9 rounded-full bg-indigo-600 flex items-center justify-center text-sm font-bold">
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{user?.full_name}</p>
              <span className={`badge text-[10px] ${ROLE_COLORS[role]}`}>
                {ROLE_LABELS[role]}
              </span>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors w-full"
          >
            <LogOut size={16} />
            Sign Out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
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
