import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { simulate } from '../lib/api';
import { StatusBadge } from './StatusBadge';
import {
  PhoneCall,
  PhoneOff,
  User,
  AlertTriangle,
  Clock,
  ChevronDown,
  ChevronUp,
  Maximize2,
  Minimize2,
  FolderPlus,
  FolderOpen,
  Timer,
} from 'lucide-react';

export default function IncomingCall({ callData, onClose }) {
  const navigate = useNavigate();
  const [phase, setPhase] = useState('ringing');     // ringing | connected
  const [view, setView] = useState('expanded');       // expanded | minimized
  const [showHistory, setShowHistory] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  const sp = callData?.screen_pop;

  useEffect(() => {
    if (phase !== 'connected') return;
    const t = setInterval(() => setElapsed(s => s + 1), 1000);
    return () => clearInterval(t);
  }, [phase]);

  if (!sp) return null;

  const inv = sp.investor;
  const port = sp.portfolio_summary;
  const flags = sp.risk_flags || [];
  const openCases = sp.open_cases || [];
  const recentCases = sp.recent_cases || [];
  const callerName = inv?.full_name || 'Unknown Caller';
  const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
  const secs = String(elapsed % 60).padStart(2, '0');

  const handleAccept = async () => {
    await simulate.acceptCall().catch(() => {});
    setPhase('connected');
  };

  const handleDecline = async () => {
    await simulate.dismissCall().catch(() => {});
    onClose();
  };

  const handleEndCall = () => {
    onClose();
  };

  const handleCreateCase = () => {
    setView('minimized');
    const params = new URLSearchParams();
    if (callData.ani_resolution?.investor_id) params.set('investor_id', callData.ani_resolution.investor_id);
    if (sp.call_id) params.set('call_id', sp.call_id);
    navigate(`/cases/new?${params.toString()}`);
  };

  const handleViewCases = () => {
    setView('minimized');
    navigate('/cases');
  };

  // ─── Minimized bar (persistent top strip while agent works) ───
  if (phase === 'connected' && view === 'minimized') {
    return (
      <div className="fixed top-0 left-64 right-0 z-50 bg-indigo-700 text-white px-4 py-2 flex items-center justify-between shadow-lg">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <PhoneCall size={16} className="animate-pulse" />
            <span className="font-semibold">{callerName}</span>
          </div>
          <span className="text-indigo-200 text-sm font-mono">{sp.ani}</span>
          {inv && (
            <span className="text-indigo-200 text-xs">{inv.investor_code} · {inv.investor_type}</span>
          )}
          {flags.length > 0 && (
            <div className="flex gap-1">
              {flags.slice(0, 2).map((f, i) => (
                <span key={i} className="bg-red-500/30 text-red-100 text-[10px] px-1.5 py-0.5 rounded">
                  {f.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          )}
          {openCases.length > 0 && (
            <span className="text-amber-300 text-xs">
              <AlertTriangle size={12} className="inline -mt-0.5 mr-0.5" />
              {openCases.length} open case{openCases.length > 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-indigo-200 text-sm font-mono flex items-center gap-1">
            <Timer size={14} /> {mins}:{secs}
          </span>
          <button
            onClick={() => setView('expanded')}
            className="bg-white/20 hover:bg-white/30 px-3 py-1 rounded text-sm flex items-center gap-1 transition-colors"
          >
            <Maximize2 size={14} /> Details
          </button>
          <button
            onClick={handleEndCall}
            className="bg-red-500/80 hover:bg-red-500 px-3 py-1 rounded text-sm flex items-center gap-1 transition-colors"
          >
            <PhoneOff size={14} /> End
          </button>
        </div>
      </div>
    );
  }

  // ─── Full expanded modal ──────────────────────────────────────
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-6 px-4">
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm"
        onClick={phase === 'connected' ? () => setView('minimized') : undefined}
      />

      <div className={`relative w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden transition-all duration-300 ${
        phase === 'ringing' ? 'animate-pulse-border ring-4 ring-green-400/60' : ''
      }`}>
        {/* Header */}
        <div className={`px-6 py-4 text-white ${phase === 'ringing' ? 'bg-green-600' : 'bg-indigo-700'}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                phase === 'ringing' ? 'bg-green-500 animate-bounce' : 'bg-indigo-600'
              }`}>
                <PhoneCall size={24} />
              </div>
              <div>
                <p className="text-sm opacity-80">
                  {phase === 'ringing' ? 'Incoming Call' : `Connected · ${mins}:${secs}`}
                </p>
                <p className="text-xl font-bold">{sp.ani}</p>
                <p className="text-xs opacity-70">Queue: {sp.queue}</p>
              </div>
            </div>
            {phase === 'ringing' && (
              <div className="flex gap-2">
                <button
                  onClick={handleAccept}
                  className="w-14 h-14 rounded-full bg-white/20 hover:bg-white/30 flex items-center justify-center transition-colors"
                  title="Accept"
                >
                  <PhoneCall size={24} />
                </button>
                <button
                  onClick={handleDecline}
                  className="w-14 h-14 rounded-full bg-red-500/80 hover:bg-red-500 flex items-center justify-center transition-colors"
                  title="Decline"
                >
                  <PhoneOff size={24} />
                </button>
              </div>
            )}
            {phase === 'connected' && (
              <div className="flex gap-2">
                <button
                  onClick={() => setView('minimized')}
                  className="bg-white/20 hover:bg-white/30 px-3 py-1.5 rounded-lg text-sm flex items-center gap-1 transition-colors"
                >
                  <Minimize2 size={14} /> Minimize
                </button>
                <button
                  onClick={handleEndCall}
                  className="bg-red-500/80 hover:bg-red-500 px-3 py-1.5 rounded-lg text-sm flex items-center gap-1 transition-colors"
                >
                  <PhoneOff size={14} /> End
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Body */}
        <div className="bg-white max-h-[70vh] overflow-y-auto">
          {/* Investor identity */}
          <div className="px-6 py-4 border-b border-slate-100">
            {inv ? (
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-lg shrink-0">
                  {inv.full_name?.charAt(0)}
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-lg">{inv.full_name}</p>
                  <div className="flex items-center gap-2 mt-0.5 text-sm text-slate-500">
                    <span className="font-mono text-xs">{inv.investor_code}</span>
                    <span>·</span>
                    <span>{inv.investor_type}</span>
                    <span>·</span>
                    <StatusBadge status={inv.account_status} />
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-3 text-slate-400">
                <User size={24} />
                <p>Unknown caller — not in MCDR registry</p>
              </div>
            )}
          </div>

          {/* Risk Flags */}
          {flags.length > 0 && (
            <div className="px-6 py-3 bg-red-50 border-b border-red-100 flex items-center gap-2 flex-wrap">
              <AlertTriangle size={16} className="text-red-500 shrink-0" />
              {flags.map((f, i) => (
                <span key={i} className="badge bg-red-100 text-red-700 text-xs">{f.replace(/_/g, ' ')}</span>
              ))}
            </div>
          )}

          {/* Portfolio */}
          {port && port.positions > 0 && (
            <div className="px-6 py-3 border-b border-slate-100">
              <div className="flex gap-6 text-sm">
                <div>
                  <p className="text-slate-400 text-xs">Positions</p>
                  <p className="font-semibold">{port.positions}</p>
                </div>
                <div>
                  <p className="text-slate-400 text-xs">Shares</p>
                  <p className="font-semibold">{port.total_shares?.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-slate-400 text-xs">Portfolio Value</p>
                  <p className="font-bold text-green-600">
                    {port.total_value?.toLocaleString('en-US', { style: 'currency', currency: 'SAR' })}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Open Cases */}
          {openCases.length > 0 && (
            <div className="px-6 py-3 border-b border-slate-100">
              <p className="text-xs font-semibold text-amber-600 mb-2 flex items-center gap-1">
                <AlertTriangle size={12} /> {openCases.length} Open Case{openCases.length > 1 ? 's' : ''}
              </p>
              <div className="space-y-1.5">
                {openCases.map((c, i) => (
                  <div
                    key={i}
                    onClick={() => { setView('minimized'); navigate(`/cases/${c.case_id}`); }}
                    className="flex items-center justify-between text-sm bg-amber-50 hover:bg-amber-100 rounded-lg px-3 py-2 cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="font-mono text-xs text-indigo-600 shrink-0">{c.case_number}</span>
                      <span className="truncate">{c.subject}</span>
                    </div>
                    <StatusBadge status={c.status} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recent History */}
          {recentCases.length > 0 && (
            <div className="px-6 py-3 border-b border-slate-100">
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="text-xs font-semibold text-slate-500 flex items-center gap-1 w-full"
              >
                <Clock size={12} /> Recent History ({recentCases.length})
                {showHistory ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
              {showHistory && (
                <div className="mt-2 space-y-1.5">
                  {recentCases.map((c, i) => (
                    <div
                      key={i}
                      onClick={() => { setView('minimized'); navigate(`/cases/${c.case_id}`); }}
                      className="flex items-center justify-between text-sm bg-slate-50 hover:bg-slate-100 rounded-lg px-3 py-2 cursor-pointer transition-colors"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="font-mono text-xs text-indigo-600 shrink-0">{c.case_number}</span>
                        <span className="truncate">{c.subject}</span>
                      </div>
                      <StatusBadge status={c.status} />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Actions */}
          {phase === 'connected' && (
            <div className="px-6 py-4 flex gap-2">
              <button onClick={handleCreateCase} className="btn-primary text-sm flex-1 flex items-center justify-center gap-2">
                <FolderPlus size={16} /> Create Case
              </button>
              {openCases.length > 0 && (
                <button onClick={handleViewCases} className="btn-secondary text-sm flex-1 flex items-center justify-center gap-2">
                  <FolderOpen size={16} /> View Cases
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
