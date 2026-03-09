import { useEffect, useState } from 'react';
import { cxReports } from '../lib/api';
import StatCard from '../components/StatCard';
import Loader from '../components/Loader';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts';
import { jsPDF } from 'jspdf';
import {
  BarChart3,
  Target,
  AlertTriangle,
  TrendingUp,
  Shield,
  CheckCircle,
  Clock,
  Download,
  Calendar,
  RotateCcw,
  Tag,
  FileDown,
} from 'lucide-react';

export default function Reports() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);

  useEffect(() => {
    setLoading(true);
    cxReports.overview(days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [days]);

  if (loading) return <Loader />;

  const d = data || {};
  const kpis = d.kpis || {};
  const volume = d.case_volume || [];
  const compliance = d.sla_compliance || [];
  const agents = d.agent_performance || [];
  const categories = d.category_breakdown || [];
  const resolutions = d.resolution_breakdown || [];

  const totalCases = volume.reduce((s, r) => s + (r.total || 0), 0);
  const totalResolved = volume.reduce((s, r) => s + (r.resolved || 0), 0);
  const totalEscalated = volume.reduce((s, r) => s + (r.escalated || 0), 0);

  const handleExport = () => {
    let csv = 'Metric,Value\n';
    csv += `Period (days),${days}\n`;
    csv += `Total Cases,${totalCases}\n`;
    csv += `Resolved,${totalResolved}\n`;
    csv += `Escalated,${totalEscalated}\n`;
    csv += `FCR %,${kpis.fcr_pct}\n`;
    csv += `AHT (min),${kpis.avg_handling_time_min}\n`;
    csv += `Escalation Rate %,${kpis.escalation_rate_pct}\n`;
    csv += `Verification Pass Rate %,${kpis.verification_pass_rate}\n\n`;

    csv += '\nDate,Total,Active,Resolved,Escalated\n';
    volume.forEach(r => {
      csv += `${r.day},${r.total},${r.active},${r.resolved},${r.escalated}\n`;
    });

    csv += '\nAgent,Cases,Avg Resolution (min),QA Score\n';
    agents.forEach(a => {
      csv += `${a.agent_name},${a.cases_handled},${a.avg_resolution_min || '—'},${a.avg_qa_score || '—'}\n`;
    });

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mcdr-report-${days}d-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportPdf = () => {
    const doc = new jsPDF();
    doc.setFontSize(18);
    doc.text('MCDR Operations Report', 14, 20);
    doc.setFontSize(11);
    doc.text(`Period: Last ${days} days | Generated: ${new Date().toISOString().slice(0, 10)}`, 14, 28);
    let y = 38;
    doc.setFontSize(12);
    doc.text('KPIs', 14, y);
    y += 8;
    doc.setFontSize(10);
    doc.text(`Total Cases: ${totalCases}  |  Resolved: ${totalResolved}  |  Escalated: ${totalEscalated}`, 14, y);
    y += 6;
    doc.text(`FCR: ${kpis.fcr_pct}%  |  AHT (min): ${kpis.avg_handling_time_min ?? '—'}  |  Escalation Rate: ${kpis.escalation_rate_pct}%`, 14, y);
    y += 10;
    doc.setFontSize(12);
    doc.text('Case Volume by Date', 14, y);
    y += 6;
    doc.setFontSize(9);
    volume.slice(0, 14).forEach((r) => {
      doc.text(`${r.day}: Total ${r.total}, Resolved ${r.resolved}, Escalated ${r.escalated}`, 14, y);
      y += 5;
    });
    y += 8;
    doc.setFontSize(12);
    doc.text('SLA Compliance', 14, y);
    y += 6;
    doc.setFontSize(9);
    compliance.forEach((c) => {
      doc.text(`${c.policy_name}: ${c.compliance_pct}% (${c.total_cases} cases)`, 14, y);
      y += 5;
    });
    if (y > 270) doc.addPage();
    doc.save(`mcdr-report-${days}d-${new Date().toISOString().slice(0, 10)}.pdf`);
  };

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <BarChart3 size={24} /> Operations Report
        </h1>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-sm">
            <Calendar size={16} className="text-slate-400" />
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="input py-1.5 w-auto"
            >
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </div>
          <button onClick={handleExport} className="btn-secondary text-sm flex items-center gap-2">
            <Download size={14} /> Export CSV
          </button>
          <button onClick={handleExportPdf} className="btn-secondary text-sm flex items-center gap-2">
            <FileDown size={14} /> Export PDF
          </button>
        </div>
      </div>

      {/* Charts */}
      {volume.length > 0 && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-600 mb-4">Case Volume Over Time</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={volume}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} stroke="#64748b" />
                <YAxis tick={{ fontSize: 11 }} stroke="#64748b" />
                <Tooltip />
                <Line type="monotone" dataKey="total" stroke="#4f46e5" strokeWidth={2} name="Total" dot={{ r: 3 }} />
                <Line type="monotone" dataKey="resolved" stroke="#22c55e" strokeWidth={1.5} name="Resolved" dot={{ r: 2 }} />
                <Line type="monotone" dataKey="escalated" stroke="#f59e0b" strokeWidth={1.5} name="Escalated" dot={{ r: 2 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
      {compliance.length > 0 && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-600 mb-4 flex items-center gap-2">
            <Shield size={16} /> SLA Compliance (Bar)
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={compliance} margin={{ top: 5, right: 20, left: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="policy_name" tick={{ fontSize: 10 }} stroke="#64748b" />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} stroke="#64748b" />
                <Tooltip />
                <Bar dataKey="compliance_pct" fill="#4f46e5" name="Compliance %" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-4">
        <StatCard label="Total Cases" value={totalCases} icon={BarChart3} color="indigo" />
        <StatCard label="FCR %" value={`${kpis.fcr_pct}%`} icon={Target} color="green" />
        <StatCard label="AHT (min)" value={kpis.avg_handling_time_min || '—'} icon={Clock} color="blue" />
        <StatCard label="Escalation Rate" value={`${kpis.escalation_rate_pct}%`} icon={TrendingUp} color="amber" />
        <StatCard label="Reopen Rate" value={`${kpis.reopen_rate_pct ?? 0}%`} icon={RotateCcw} color="red" />
        <StatCard label="Verification %" value={`${kpis.verification_pass_rate}%`} icon={Shield} color="purple" />
        <StatCard
          label="Verifications"
          value={kpis.verification_total}
          icon={CheckCircle}
          color="teal"
          sub={`${kpis.verification_pass_rate}% pass`}
        />
      </div>

      {/* Case Volume */}
      {volume.length > 0 && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-600 mb-4">
            Case Volume — Last {days} Days
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left px-4 py-3 font-medium text-slate-600">Date</th>
                  <th className="text-right px-4 py-3 font-medium text-slate-600">Total</th>
                  <th className="text-right px-4 py-3 font-medium text-slate-600">Active</th>
                  <th className="text-right px-4 py-3 font-medium text-slate-600">Resolved</th>
                  <th className="text-right px-4 py-3 font-medium text-slate-600">Escalated</th>
                  <th className="px-4 py-3 font-medium text-slate-600">Distribution</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {volume.map((r) => {
                  const max = Math.max(...volume.map(v => v.total || 1));
                  const pct = ((r.total || 0) / max) * 100;
                  return (
                    <tr key={r.day} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-mono text-xs">{r.day}</td>
                      <td className="px-4 py-3 text-right font-bold">{r.total}</td>
                      <td className="px-4 py-3 text-right text-blue-600">{r.active}</td>
                      <td className="px-4 py-3 text-right text-green-600">{r.resolved}</td>
                      <td className="px-4 py-3 text-right text-amber-600">{r.escalated}</td>
                      <td className="px-4 py-3">
                        <div className="w-full bg-slate-100 rounded-full h-2.5">
                          <div
                            className="h-2.5 rounded-full bg-indigo-500 transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* SLA Compliance */}
        {compliance.length > 0 && (
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-slate-600 mb-4 flex items-center gap-2">
              <Shield size={16} /> SLA Compliance by Policy
            </h3>
            <div className="space-y-4">
              {compliance.map((c) => (
                <div key={c.policy_name}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium">{c.policy_name}</span>
                    <span className={`text-sm font-bold ${
                      c.compliance_pct >= 90 ? 'text-green-600' :
                      c.compliance_pct >= 70 ? 'text-amber-600' : 'text-red-600'
                    }`}>
                      {c.compliance_pct}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-3">
                    <div
                      className={`h-3 rounded-full transition-all ${
                        c.compliance_pct >= 90 ? 'bg-green-500' :
                        c.compliance_pct >= 70 ? 'bg-amber-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${Math.min(c.compliance_pct, 100)}%` }}
                    />
                  </div>
                  <div className="flex gap-4 mt-1 text-xs text-slate-400">
                    <span>{c.total_cases} cases</span>
                    <span className="text-amber-500">{c.frt_breached} FRT breaches</span>
                    <span className="text-red-500">{c.rt_breached} RT breaches</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Category Breakdown */}
        {categories.length > 0 && (
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-slate-600 mb-4 flex items-center gap-2">
              <AlertTriangle size={16} /> Case Volume by Category
            </h3>
            <div className="space-y-3">
              {categories.map((c) => {
                const max = categories[0]?.cnt || 1;
                const pct = (c.cnt / max) * 100;
                const resPct = c.cnt > 0 ? Math.round((c.resolved / c.cnt) * 100) : 0;
                return (
                  <div key={c.category}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">{c.category}</span>
                      <div className="flex items-center gap-3 text-xs text-slate-500">
                        <span>{c.cnt} cases</span>
                        <span className="text-green-600">{resPct}% resolved</span>
                      </div>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-2.5">
                      <div
                        className="h-2.5 rounded-full bg-indigo-400 transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Resolution Code Breakdown */}
        {resolutions.length > 0 && (
          <div className="card p-5 lg:col-span-2">
            <h3 className="text-sm font-semibold text-slate-600 mb-4 flex items-center gap-2">
              <Tag size={16} /> Resolution Codes
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {resolutions.map((r) => {
                const max = resolutions[0]?.cnt || 1;
                const pct = Math.round((r.cnt / max) * 100);
                return (
                  <div key={r.resolution_code} className="bg-slate-50 rounded-lg p-3">
                    <p className="text-xs text-slate-500 capitalize">{r.resolution_code.replace(/_/g, ' ')}</p>
                    <p className="text-lg font-bold text-slate-800">{r.cnt}</p>
                    <div className="w-full bg-slate-200 rounded-full h-1.5 mt-1">
                      <div className="h-1.5 rounded-full bg-indigo-400" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Agent Performance Table */}
      {agents.length > 0 && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-600 mb-4 flex items-center gap-2">
            <TrendingUp size={16} /> Agent Performance
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left px-4 py-3 font-medium text-slate-600">#</th>
                  <th className="text-left px-4 py-3 font-medium text-slate-600">Agent</th>
                  <th className="text-right px-4 py-3 font-medium text-slate-600">Cases</th>
                  <th className="text-right px-4 py-3 font-medium text-slate-600">Avg Resolution (min)</th>
                  <th className="text-right px-4 py-3 font-medium text-slate-600">QA Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {agents.map((a, i) => (
                  <tr key={a.agent_id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-slate-400">{i + 1}</td>
                    <td className="px-4 py-3 font-medium">{a.agent_name}</td>
                    <td className="px-4 py-3 text-right font-bold">{a.cases_handled}</td>
                    <td className="px-4 py-3 text-right">
                      {a.avg_resolution_min != null ? (
                        <span className={a.avg_resolution_min > 60 ? 'text-red-600' : 'text-green-600'}>
                          {a.avg_resolution_min}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {a.avg_qa_score != null ? (
                        <span className={`font-bold ${
                          a.avg_qa_score >= 80 ? 'text-green-600' :
                          a.avg_qa_score >= 60 ? 'text-amber-600' : 'text-red-600'
                        }`}>
                          {a.avg_qa_score}
                        </span>
                      ) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
