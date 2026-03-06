import { useEffect, useState } from 'react';
import { useAuth } from '../lib/auth';
import { cx, users, audit } from '../lib/api';
import StatCard from '../components/StatCard';
import CaseTable from '../components/CaseTable';
import Loader from '../components/Loader';
import { useNavigate } from 'react-router-dom';
import {
  FolderOpen,
  PhoneCall,
  AlertTriangle,
  CheckCircle,
  Clock,
  BarChart3,
  TrendingUp,
  Users,
  ShieldCheck,
  Activity,
  UserCog,
  ScrollText,
} from 'lucide-react';

function countBy(arr, key) {
  return arr.reduce((acc, item) => {
    const val = item[key] || 'unknown';
    acc[val] = (acc[val] || 0) + 1;
    return acc;
  }, {});
}

export default function Dashboard() {
  const { user } = useAuth();
  const role = user?.role_name;
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [recentCases, setRecentCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [adminData, setAdminData] = useState(null);
  const [myPerf, setMyPerf] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const isAgentRole = role === 'agent' || role === 'senior_agent';
        if (isAgentRole) {
          const hasPerfAccess = role === 'senior_agent';
          const [agentStats, agentCases, perf, qaData] = await Promise.all([
            cx.agentStats(user.id).catch(() => null),
            cx.agentCases(user.id, 10).catch(() => []),
            hasPerfAccess ? cx.agentPerformance(user.id).catch(() => null) : Promise.resolve(null),
            cx.agentQa(user.id).catch(() => null),
          ]);
          setRecentCases(agentCases);
          setStats({
            cases: agentStats || { total_cases: agentCases.length, by_status: countBy(agentCases, 'status') },
            calls: { total_calls: agentStats?.total_calls ?? 0 },
            sla: null,
          });
          setMyPerf({ performance: perf, qa: qaData });
        } else {
          const [caseStats, callStats, slaStats] = await Promise.all([
            cx.caseStats().catch(() => null),
            cx.callStats().catch(() => null),
            cx.slaStats().catch(() => null),
          ]);
          setStats({ cases: caseStats, calls: callStats, sla: slaStats });
          const result = await cx.searchCases({ limit: 10 }).catch(() => ({ items: [] }));
          setRecentCases(result.items || result || []);
        }

        if (role === 'admin') {
          const [userList, recentAudit] = await Promise.all([
            users.list().catch(() => []),
            audit.logs({ limit: 8 }).catch(() => []),
          ]);
          const byRole = countBy(userList, 'role');
          const activeCount = userList.filter(u => u.is_active).length;
          setAdminData({
            totalUsers: userList.length,
            activeUsers: activeCount,
            inactiveUsers: userList.length - activeCount,
            byRole: countBy(userList.map(u => ({ role: u.role?.name || 'unknown' })), 'role'),
            recentAudit,
          });
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [role, user?.id]);

  if (loading) return <Loader />;

  const caseS = stats?.cases || {};
  const callS = stats?.calls || {};
  const slaS = stats?.sla || {};
  const byStatus = caseS.by_status || {};
  const totalBreaches = (slaS.by_type_and_policy || []).reduce((s, r) => s + (r.cnt || 0), 0);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold">
          {(role === 'agent' || role === 'senior_agent') ? 'My Dashboard' : role === 'admin' ? 'Admin Dashboard' : 'Operations Dashboard'}
        </h1>
        <p className="text-slate-500 mt-1">
          Welcome back, {user?.full_name}
        </p>
      </div>

      {/* Operations Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label={(role === 'agent' || role === 'senior_agent') ? 'My Cases' : 'Total Cases'}
          value={caseS.total_cases ?? '—'}
          icon={FolderOpen}
          color="indigo"
        />
        <StatCard
          label="Open"
          value={(byStatus.open || 0) + (byStatus.in_progress || 0)}
          icon={Clock}
          color="blue"
          sub={`${byStatus.open || 0} new · ${byStatus.in_progress || 0} in progress`}
        />
        <StatCard
          label={(role === 'agent' || role === 'senior_agent') ? 'My Calls' : 'Total Calls'}
          value={callS.total_calls ?? '—'}
          icon={PhoneCall}
          color="green"
        />
        {(role === 'agent' || role === 'senior_agent') ? (
          <StatCard
            label="Resolved"
            value={(byStatus.resolved || 0) + (byStatus.closed || 0)}
            icon={CheckCircle}
            color="green"
            sub={byStatus.escalated ? `${byStatus.escalated} escalated` : undefined}
          />
        ) : (
          <StatCard
            label="SLA Breaches"
            value={totalBreaches || '—'}
            icon={AlertTriangle}
            color="red"
          />
        )}
      </div>

      {/* My Performance — Agent self-view */}
      {(role === 'agent' || role === 'senior_agent') && myPerf && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <BarChart3 size={18} className="text-indigo-600" /> My Performance
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {myPerf.qa?.avg_score != null && (
              <div className="card p-4 text-center">
                <div className={`text-2xl font-bold ${
                  myPerf.qa.avg_score >= 80 ? 'text-green-600' :
                  myPerf.qa.avg_score >= 60 ? 'text-yellow-600' : 'text-red-600'
                }`}>
                  {myPerf.qa.avg_score?.toFixed(1)}
                </div>
                <div className="text-xs text-slate-500 mt-1">QA Score (avg)</div>
              </div>
            )}
            {myPerf.qa?.total_evaluations != null && (
              <div className="card p-4 text-center">
                <div className="text-2xl font-bold text-slate-700">{myPerf.qa.total_evaluations}</div>
                <div className="text-xs text-slate-500 mt-1">QA Reviews</div>
              </div>
            )}
            {myPerf.performance?.avg_resolution_minutes != null && (
              <div className="card p-4 text-center">
                <div className="text-2xl font-bold text-slate-700">
                  {Math.round(myPerf.performance.avg_resolution_minutes)}m
                </div>
                <div className="text-xs text-slate-500 mt-1">Avg Resolution</div>
              </div>
            )}
            {myPerf.performance?.sla_compliance_pct != null && (
              <div className="card p-4 text-center">
                <div className={`text-2xl font-bold ${
                  myPerf.performance.sla_compliance_pct >= 90 ? 'text-green-600' :
                  myPerf.performance.sla_compliance_pct >= 70 ? 'text-yellow-600' : 'text-red-600'
                }`}>
                  {myPerf.performance.sla_compliance_pct?.toFixed(0)}%
                </div>
                <div className="text-xs text-slate-500 mt-1">SLA Compliance</div>
              </div>
            )}
          </div>
        </div>
      )}

      {(role === 'supervisor' || role === 'admin') && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard
            label="Resolved"
            value={byStatus.resolved ?? '—'}
            icon={CheckCircle}
            color="green"
          />
          <StatCard
            label="Escalated"
            value={byStatus.escalated ?? '—'}
            icon={TrendingUp}
            color="yellow"
          />
          <StatCard
            label="Avg Call Duration (min)"
            value={callS.avg_duration_seconds ? Math.round(callS.avg_duration_seconds / 60) : '—'}
            icon={BarChart3}
            color="purple"
          />
        </div>
      )}

      {/* Admin System Panel */}
      {role === 'admin' && adminData && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <ShieldCheck size={20} className="text-indigo-600" /> System Administration
          </h2>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <button onClick={() => navigate('/admin/users')} className="card p-4 text-center hover:ring-2 hover:ring-indigo-300 transition-all cursor-pointer">
              <Users size={20} className="mx-auto mb-1 text-indigo-500" />
              <div className="text-2xl font-bold text-slate-800">{adminData.totalUsers}</div>
              <div className="text-xs text-slate-500">Total Users</div>
            </button>
            <button onClick={() => navigate('/admin/users')} className="card p-4 text-center hover:ring-2 hover:ring-green-300 transition-all cursor-pointer">
              <ShieldCheck size={20} className="mx-auto mb-1 text-green-500" />
              <div className="text-2xl font-bold text-green-600">{adminData.activeUsers}</div>
              <div className="text-xs text-slate-500">Active</div>
            </button>
            {Object.entries(adminData.byRole).sort().map(([roleName, count]) => (
              <div key={roleName} className="card p-4 text-center">
                <UserCog size={20} className="mx-auto mb-1 text-slate-400" />
                <div className="text-2xl font-bold text-slate-700">{count}</div>
                <div className="text-xs text-slate-500 capitalize">{roleName.replace('_', ' ')}s</div>
              </div>
            ))}
          </div>

          {/* Recent Audit Activity */}
          <div className="card overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-b">
              <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                <Activity size={16} className="text-indigo-500" /> Recent System Activity
              </h3>
              <button
                onClick={() => navigate('/audit')}
                className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1"
              >
                <ScrollText size={12} /> View All
              </button>
            </div>
            <div className="divide-y divide-slate-100">
              {adminData.recentAudit.map((log) => {
                const parsed = {};
                (log.detail || '').split(' | ').forEach(p => {
                  const eq = p.indexOf('=');
                  if (eq > 0) parsed[p.slice(0, eq)] = p.slice(eq + 1);
                });
                const ts = log.timestamp ? new Date(log.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) : '';
                return (
                  <div key={log.id} className="flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-slate-50">
                    <span className="text-xs text-slate-400 font-mono w-16 shrink-0">{ts}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${
                      log.action === 'POST' ? 'bg-green-50 text-green-700 border-green-200' :
                      log.action === 'PATCH' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                      log.action === 'page_view' ? 'bg-purple-50 text-purple-700 border-purple-200' :
                      'bg-blue-50 text-blue-700 border-blue-200'
                    }`}>{log.action}</span>
                    <span className="text-slate-600 font-mono text-xs truncate flex-1">{log.resource}</span>
                    <span className="text-xs text-slate-400">{parsed.user || `#${log.user_id || '—'}`}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      <div>
        <h2 className="text-lg font-semibold mb-3">
          {(role === 'agent' || role === 'senior_agent') ? 'My Recent Cases' : 'Recent Cases'}
        </h2>
        <CaseTable cases={recentCases} showAgent={role !== 'agent' && role !== 'senior_agent'} />
      </div>
    </div>
  );
}
