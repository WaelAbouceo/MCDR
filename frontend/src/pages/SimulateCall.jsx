import { useState, useEffect } from 'react';
import { simulate, users } from '../lib/api';
import { StatusBadge } from '../components/StatusBadge';
import { PhoneCall, User, Briefcase, AlertTriangle, CheckCircle, Radio, Clock } from 'lucide-react';

export default function SimulateCall() {
  const [ani, setAni] = useState('');
  const [queue, setQueue] = useState('general');
  const [targetAgent, setTargetAgent] = useState('');
  const [agentList, setAgentList] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    users.list().then(list => {
      const agents = (list || []).filter(u => u.role?.name === 'agent' || u.role_name === 'agent');
      setAgentList(agents);
    }).catch(() => {});
  }, []);

  const handleSimulate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await simulate.incomingCall(ani || '', queue, targetAgent || undefined);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const r = result;
  const sp = r?.screen_pop;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold flex items-center gap-2">
        <PhoneCall size={24} /> Simulate Incoming Call
      </h1>
      <p className="text-slate-500 text-sm -mt-4">
        Mimics a Cisco CTI call arriving at the contact center. Enter an ANI or leave blank for a random caller.
      </p>

      <div className="card p-6">
        <form onSubmit={handleSimulate} className="flex gap-3 items-end flex-wrap">
          <div className="flex-1 min-w-[200px]">
            <label className="label">Caller ANI (Phone Number)</label>
            <input
              type="text"
              value={ani}
              onChange={(e) => setAni(e.target.value)}
              className="input"
              placeholder="Leave blank for random caller"
            />
          </div>
          <div>
            <label className="label">Queue</label>
            <select value={queue} onChange={(e) => setQueue(e.target.value)} className="input">
              <option value="general">General</option>
              <option value="trading">Trading</option>
              <option value="billing">Billing</option>
              <option value="technical">Technical</option>
              <option value="priority">Priority / VIP</option>
              <option value="retention">Retention</option>
            </select>
          </div>
          <div>
            <label className="label">Route to Agent</label>
            <select value={targetAgent} onChange={(e) => setTargetAgent(e.target.value)} className="input">
              <option value="">Auto (random)</option>
              {agentList.map(a => (
                <option key={a.id} value={a.id}>{a.full_name} (id:{a.id})</option>
              ))}
            </select>
          </div>
          <button type="submit" disabled={loading} className="btn-primary whitespace-nowrap">
            {loading ? 'Simulating...' : 'Simulate Call'}
          </button>
        </form>
      </div>

      {error && (
        <div className="text-sm text-red-600 bg-red-50 rounded-lg p-4">{error}</div>
      )}

      {r && (
        <div className="space-y-4">
          {/* CTI Event Chain */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
              <Radio size={16} /> CTI Event Chain
            </h3>
            <div className="flex gap-2 flex-wrap items-center">
              {(r.events || []).map((evt, i) => (
                <div key={i} className="flex items-center gap-1">
                  <div className="text-center">
                    <span className="badge bg-indigo-100 text-indigo-700 text-xs">{evt.event}</span>
                    <p className="text-[10px] text-slate-400 mt-0.5">{evt.source}</p>
                  </div>
                  {i < (r.events?.length || 0) - 1 && <span className="text-slate-300 text-lg">→</span>}
                </div>
              ))}
            </div>
          </div>

          {/* ANI Resolution */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
              <PhoneCall size={16} /> ANI Resolution
            </h3>
            <dl className="flex gap-6 text-sm">
              <div>
                <dt className="text-slate-500">ANI</dt>
                <dd className="font-mono">{r.ani_resolution?.ani}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Matched</dt>
                <dd className={r.ani_resolution?.matched ? 'text-green-600 font-medium' : 'text-red-500 font-medium'}>
                  {r.ani_resolution?.matched ? 'Yes — Investor identified' : 'No — Unknown caller'}
                </dd>
              </div>
              {r.ani_resolution?.investor_id && (
                <div>
                  <dt className="text-slate-500">Investor ID</dt>
                  <dd className="font-mono">{r.ani_resolution.investor_id}</dd>
                </div>
              )}
            </dl>
          </div>

          {/* Screen Pop */}
          {sp && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Customer Info */}
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
                  <User size={16} /> Customer Identification
                </h3>
                {sp.investor ? (
                  <dl className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-slate-500">Name</dt>
                      <dd className="font-medium">{sp.investor.full_name}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-slate-500">Code</dt>
                      <dd className="font-mono text-xs">{sp.investor.investor_code}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-slate-500">Type</dt>
                      <dd>{sp.investor.investor_type}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-slate-500">Status</dt>
                      <dd><StatusBadge status={sp.investor.account_status} /></dd>
                    </div>
                  </dl>
                ) : (
                  <p className="text-sm text-slate-400">Unidentified caller</p>
                )}
              </div>

              {/* Portfolio */}
              {sp.portfolio_summary && sp.portfolio_summary.positions > 0 && (
                <div className="card p-5">
                  <h3 className="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
                    <Briefcase size={16} /> Portfolio
                  </h3>
                  <dl className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-slate-500">Positions</dt>
                      <dd>{sp.portfolio_summary.positions}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-slate-500">Total Shares</dt>
                      <dd>{sp.portfolio_summary.total_shares?.toLocaleString()}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-slate-500">Total Value</dt>
                      <dd className="font-bold text-green-600">
                        {sp.portfolio_summary.total_value?.toLocaleString('en-US', { style: 'currency', currency: 'SAR' })}
                      </dd>
                    </div>
                  </dl>
                </div>
              )}
            </div>
          )}

          {/* App User */}
          {sp?.app_user && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
                <User size={16} /> Mobile App User
              </h3>
              <dl className="flex gap-6 flex-wrap text-sm">
                <div>
                  <dt className="text-slate-500">Mobile</dt>
                  <dd className="font-mono">{sp.app_user.mobile}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Email</dt>
                  <dd>{sp.app_user.email}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Status</dt>
                  <dd><StatusBadge status={sp.app_user.status} /></dd>
                </div>
                <div>
                  <dt className="text-slate-500">OTP Verified</dt>
                  <dd>{sp.app_user.otp_verified ? 'Yes' : 'No'}</dd>
                </div>
                {sp.app_user.last_login && (
                  <div>
                    <dt className="text-slate-500">Last Login</dt>
                    <dd className="text-xs">{sp.app_user.last_login}</dd>
                  </div>
                )}
              </dl>
            </div>
          )}

          {/* Risk Flags */}
          {sp?.risk_flags && sp.risk_flags.length > 0 && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
                <AlertTriangle size={16} /> Risk Flags
              </h3>
              <div className="flex gap-2 flex-wrap">
                {sp.risk_flags.map((flag, i) => (
                  <span key={i} className="badge bg-red-100 text-red-700">{flag.replace(/_/g, ' ')}</span>
                ))}
              </div>
            </div>
          )}

          {/* Open Cases */}
          {sp?.open_cases && sp.open_cases.length > 0 && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
                <AlertTriangle size={16} className="text-amber-500" /> Open Cases ({sp.open_cases.length})
              </h3>
              <div className="space-y-2">
                {sp.open_cases.map((c, i) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-amber-50 rounded-lg text-sm">
                    <div>
                      <span className="font-mono text-xs text-indigo-600 mr-2">{c.case_number}</span>
                      <span>{c.subject}</span>
                      <span className="text-xs text-slate-400 ml-2">({c.category})</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={c.priority} />
                      <StatusBadge status={c.status} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recent Cases */}
          {sp?.recent_cases && sp.recent_cases.length > 0 && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
                <Clock size={16} /> Recent Case History
              </h3>
              <div className="space-y-2">
                {sp.recent_cases.map((c, i) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg text-sm">
                    <div>
                      <span className="font-mono text-xs text-indigo-600 mr-2">{c.case_number}</span>
                      <span>{c.subject}</span>
                      <span className="text-xs text-slate-400 ml-2">({c.category})</span>
                    </div>
                    <StatusBadge status={c.status} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Call Assignment */}
          {sp?.agent && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
                <CheckCircle size={16} className="text-green-500" /> Call Assignment
              </h3>
              <dl className="flex gap-6 flex-wrap text-sm">
                <div>
                  <dt className="text-slate-500">Agent</dt>
                  <dd className="font-medium">{sp.agent.name}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Tier</dt>
                  <dd>{sp.agent.tier}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Queue</dt>
                  <dd className="font-mono">{sp.queue}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Call ID</dt>
                  <dd className="font-mono">{sp.call_id}</dd>
                </div>
              </dl>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
