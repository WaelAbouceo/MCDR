import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { cx, registry, cases as casesApi, escalations } from '../lib/api';
import { StatusBadge, PriorityBadge } from '../components/StatusBadge';
import { useToast } from '../components/Toast';
import Loader from '../components/Loader';
import { formatDistanceToNow, format } from 'date-fns';
import {
  ArrowLeft,
  User,
  Send,
  AlertTriangle,
  FileText,
  Clock,
  MessageSquare,
  History,
  Briefcase,
  PhoneCall,
} from 'lucide-react';

export default function CaseDetail() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const toast = useToast();
  const role = user?.role_name;
  const [caseData, setCaseData] = useState(null);
  const [investor, setInvestor] = useState(null);
  const [notes, setNotes] = useState([]);
  const [history, setHistory] = useState([]);
  const [escalationList, setEscalationList] = useState([]);
  const [qaEvals, setQaEvals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [noteText, setNoteText] = useState('');
  const [noteInternal, setNoteInternal] = useState(false);
  const [sending, setSending] = useState(false);
  const [tab, setTab] = useState('notes');
  const [statusUpdate, setStatusUpdate] = useState('');

  useEffect(() => {
    loadCase();
  }, [caseId]);

  async function loadCase() {
    setLoading(true);
    try {
      const c = await cx.getCase(caseId);
      setCaseData(c);

      const [cNotes, cHistory, cEsc, cQa] = await Promise.all([
        cx.getCase(caseId).then(d => d?.notes).catch(() => []),
        cx.getCase(caseId).then(d => d?.history).catch(() => []),
        cx.escalations(caseId).catch(() => []),
        cx.caseQa(caseId).catch(() => []),
      ]);

      setNotes(c?.notes || cNotes || []);
      setHistory(c?.history || cHistory || []);
      setEscalationList(cEsc || []);
      setQaEvals(cQa || []);

      if (c?.investor_id) {
        const inv = await registry.investorProfile(c.investor_id).catch(() => null);
        setInvestor(inv);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleAddNote(e) {
    e.preventDefault();
    if (!noteText.trim()) return;
    setSending(true);
    try {
      await casesApi.addNote(caseId, { content: noteText, is_internal: noteInternal });
      setNoteText('');
      toast(noteInternal ? 'Internal note added' : 'Note added', 'success');
      await loadCase();
    } catch (err) {
      toast(err.message || 'Failed to add note', 'error');
    } finally {
      setSending(false);
    }
  }

  async function handleStatusChange() {
    if (!statusUpdate) return;
    try {
      await casesApi.update(caseId, { status: statusUpdate });
      toast(`Status changed to ${statusUpdate.replace(/_/g, ' ')}`, 'success');
      setStatusUpdate('');
      await loadCase();
    } catch (err) {
      toast(err.message || 'Failed to update status', 'error');
    }
  }

  const [escalateReason, setEscalateReason] = useState('');
  const [showEscalateForm, setShowEscalateForm] = useState(false);

  async function handleEscalate() {
    if (!escalateReason.trim()) {
      toast('Please provide a reason for escalation', 'warning');
      return;
    }
    try {
      await escalations.create({ case_id: caseId, reason: escalateReason });
      toast('Case escalated successfully', 'success');
      setEscalateReason('');
      setShowEscalateForm(false);
      await loadCase();
    } catch (err) {
      toast(err.message || 'Failed to escalate', 'error');
    }
  }

  if (loading) return <Loader />;
  if (!caseData) {
    return (
      <div className="p-6">
        <button onClick={() => navigate(-1)} className="btn-secondary mb-4">
          <ArrowLeft size={16} className="mr-1 inline" /> Back
        </button>
        <p className="text-slate-500">Case not found.</p>
      </div>
    );
  }

  const c = caseData;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="btn-secondary text-sm py-1.5 px-3">
          <ArrowLeft size={16} />
        </button>
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <span className="font-mono text-indigo-600">{c.case_number || `#${caseId}`}</span>
            {c.subject}
          </h1>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <StatusBadge status={c.status} />
            <PriorityBadge priority={c.priority} />
            {c.investor_name && (
              <span className="text-xs text-slate-500">
                <User size={12} className="inline -mt-0.5 mr-0.5" />
                {c.investor_name}
                {c.investor_code && <span className="text-slate-400 ml-1">({c.investor_code})</span>}
              </span>
            )}
            {c.agent_name && (
              <span className="text-xs text-slate-500">
                · Agent: {c.agent_name}
              </span>
            )}
            {c.created_at && (
              <span className="text-xs text-slate-400">
                · Opened {formatDistanceToNow(new Date(c.created_at), { addSuffix: true })}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-4">
          {/* Description */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-slate-600 mb-2 flex items-center gap-2">
              <FileText size={16} /> Description
            </h3>
            <p className="text-sm text-slate-700 whitespace-pre-wrap">
              {c.description || 'No description provided.'}
            </p>
          </div>

          {/* Tabs */}
          <div className="card">
            <div className="flex border-b border-slate-200">
              {[
                { key: 'notes', label: 'Notes', icon: MessageSquare, count: notes.length },
                { key: 'history', label: 'History', icon: History, count: history.length },
                { key: 'escalations', label: 'Escalations', icon: AlertTriangle, count: escalationList.length },
                ...(role === 'qa_analyst' || role === 'admin'
                  ? [{ key: 'qa', label: 'QA', icon: Briefcase, count: qaEvals.length }]
                  : []),
              ].map(({ key, label, icon: Icon, count }) => (
                <button
                  key={key}
                  onClick={() => setTab(key)}
                  className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                    tab === key
                      ? 'border-indigo-600 text-indigo-600'
                      : 'border-transparent text-slate-500 hover:text-slate-700'
                  }`}
                >
                  <Icon size={16} />
                  {label}
                  {count > 0 && (
                    <span className="bg-slate-100 text-slate-600 text-xs px-1.5 py-0.5 rounded-full">
                      {count}
                    </span>
                  )}
                </button>
              ))}
            </div>

            <div className="p-5">
              {tab === 'notes' && (
                <div className="space-y-4">
                  {(role === 'agent' || role === 'admin' || role === 'supervisor') && (
                    <form onSubmit={handleAddNote} className="flex gap-2">
                      <input
                        value={noteText}
                        onChange={(e) => setNoteText(e.target.value)}
                        placeholder="Add a note..."
                        className="input flex-1"
                      />
                      <label className="flex items-center gap-1 text-xs text-slate-500 whitespace-nowrap">
                        <input
                          type="checkbox"
                          checked={noteInternal}
                          onChange={(e) => setNoteInternal(e.target.checked)}
                        />
                        Internal
                      </label>
                      <button type="submit" disabled={sending} className="btn-primary text-sm py-2 px-3">
                        <Send size={14} />
                      </button>
                    </form>
                  )}

                  {notes.length === 0 ? (
                    <p className="text-sm text-slate-400 text-center py-4">No notes yet</p>
                  ) : (
                    notes.map((n, i) => (
                      <div key={i} className={`p-3 rounded-lg text-sm ${n.is_internal ? 'bg-yellow-50 border border-yellow-200' : 'bg-slate-50'}`}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-slate-700">
                            {n.author_name || n.author_id || 'System'}
                          </span>
                          <div className="flex items-center gap-2">
                            {n.is_internal && <span className="badge bg-yellow-100 text-yellow-700">Internal</span>}
                            <span className="text-xs text-slate-400">
                              {n.created_at ? format(new Date(n.created_at), 'MMM d, HH:mm') : ''}
                            </span>
                          </div>
                        </div>
                        <p className="text-slate-600">{n.content}</p>
                      </div>
                    ))
                  )}
                </div>
              )}

              {tab === 'history' && (
                <div className="space-y-2">
                  {history.length === 0 ? (
                    <p className="text-sm text-slate-400 text-center py-4">No history</p>
                  ) : (
                    history.map((h, i) => (
                      <div key={i} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg text-sm">
                        <Clock size={14} className="text-slate-400 mt-0.5 shrink-0" />
                        <div>
                          <p className="text-slate-700">
                            <span className="font-medium">{h.field_changed}</span> changed
                            {h.old_value && <> from <span className="font-mono text-xs bg-red-50 px-1 rounded">{h.old_value}</span></>}
                            {h.new_value && <> to <span className="font-mono text-xs bg-green-50 px-1 rounded">{h.new_value}</span></>}
                          </p>
                          <p className="text-xs text-slate-400 mt-0.5">
                            {h.changed_at ? format(new Date(h.changed_at), 'MMM d, HH:mm') : ''}
                            {h.changed_by && ` by ${h.changed_by}`}
                          </p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {tab === 'escalations' && (
                <div className="space-y-2">
                  {escalationList.length === 0 ? (
                    <p className="text-sm text-slate-400 text-center py-4">No escalations</p>
                  ) : (
                    escalationList.map((e, i) => (
                      <div key={i} className="p-3 bg-red-50 rounded-lg text-sm border border-red-200">
                        <p className="text-slate-700 font-medium">{e.reason || 'Escalated'}</p>
                        <p className="text-xs text-slate-500 mt-1">
                          {e.from_tier} → {e.to_tier}
                          {e.from_agent_name && ` | From: ${e.from_agent_name}`}
                          {e.to_agent_name && ` → ${e.to_agent_name}`}
                          {e.escalated_at && ` | ${format(new Date(e.escalated_at), 'MMM d, HH:mm')}`}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              )}

              {tab === 'qa' && (
                <div className="space-y-2">
                  {qaEvals.length === 0 ? (
                    <p className="text-sm text-slate-400 text-center py-4">No QA evaluations</p>
                  ) : (
                    qaEvals.map((q, i) => (
                      <div key={i} className="p-3 bg-teal-50 rounded-lg text-sm border border-teal-200">
                        <div className="flex justify-between items-center">
                          <span className="font-medium">Score: {q.total_score}</span>
                          <span className="text-xs text-slate-400">
                            {q.evaluated_at ? format(new Date(q.evaluated_at), 'MMM d, HH:mm') : ''}
                          </span>
                        </div>
                        {q.feedback && <p className="text-slate-600 mt-1">{q.feedback}</p>}
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Actions */}
          {(role === 'agent' || role === 'supervisor' || role === 'admin') && (
            <div className="card p-5 space-y-3">
              <h3 className="text-sm font-semibold text-slate-600">Actions</h3>
              <div className="flex gap-2">
                <select
                  value={statusUpdate}
                  onChange={(e) => setStatusUpdate(e.target.value)}
                  className="input flex-1"
                >
                  <option value="">Change Status</option>
                  <option value="in_progress">In Progress</option>
                  <option value="pending_customer">Pending Customer</option>
                  <option value="resolved">Resolved</option>
                  <option value="closed">Closed</option>
                </select>
                <button onClick={handleStatusChange} disabled={!statusUpdate} className="btn-primary text-sm">
                  Update
                </button>
              </div>
              {(role === 'agent' || role === 'supervisor' || role === 'admin') && c.status !== 'escalated' && (
                showEscalateForm ? (
                  <div className="space-y-2">
                    <textarea
                      value={escalateReason}
                      onChange={(e) => setEscalateReason(e.target.value)}
                      placeholder="Reason for escalation (required)..."
                      className="input h-20 resize-none text-sm"
                    />
                    <div className="flex gap-2">
                      <button onClick={handleEscalate} className="btn-danger flex-1 text-sm flex items-center justify-center gap-1">
                        <AlertTriangle size={14} /> Escalate
                      </button>
                      <button onClick={() => setShowEscalateForm(false)} className="btn-secondary text-sm">
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <button onClick={() => setShowEscalateForm(true)} className="btn-danger w-full text-sm flex items-center justify-center gap-2">
                    <AlertTriangle size={14} /> Escalate
                  </button>
                )
              )}
            </div>
          )}

          {/* Case Details */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-slate-600 mb-3">Case Details</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-500">Case ID</dt>
                <dd className="font-mono text-xs">{c.case_id || c.id}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Category</dt>
                <dd>{c.category || '—'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Agent</dt>
                <dd>{c.agent_name || c.agent_id || '—'}</dd>
              </div>
              {c.resolved_at && (
                <div className="flex justify-between">
                  <dt className="text-slate-500">Resolved</dt>
                  <dd className="text-xs">{format(new Date(c.resolved_at), 'MMM d, HH:mm')}</dd>
                </div>
              )}
              {c.sla_status && (
                <div className="flex justify-between">
                  <dt className="text-slate-500">SLA</dt>
                  <dd><StatusBadge status={c.sla_status} /></dd>
                </div>
              )}
            </dl>
          </div>

          {/* Linked Call */}
          {c.call && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
                <PhoneCall size={16} /> Originating Call
              </h3>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-slate-500">Call ID</dt>
                  <dd className="font-mono text-xs">{c.call.call_id}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">ANI (Caller)</dt>
                  <dd className="font-mono text-xs">{c.call.ani}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Queue</dt>
                  <dd>{c.call.queue}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Status</dt>
                  <dd><StatusBadge status={c.call.status} /></dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Duration</dt>
                  <dd>{c.call.duration_seconds ? `${Math.round(c.call.duration_seconds / 60)}m ${c.call.duration_seconds % 60}s` : '—'}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Wait Time</dt>
                  <dd>{c.call.wait_seconds ? `${c.call.wait_seconds}s` : '—'}</dd>
                </div>
                {c.call.call_start && (
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Started</dt>
                    <dd className="text-xs">{format(new Date(c.call.call_start), 'MMM d, HH:mm')}</dd>
                  </div>
                )}
                {c.call.recording_url && (
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Recording</dt>
                    <dd>
                      <a
                        href={c.call.recording_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-indigo-600 hover:text-indigo-800 underline"
                      >
                        Play Recording
                      </a>
                    </dd>
                  </div>
                )}
              </dl>
            </div>
          )}

          {/* Investor info */}
          {investor && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
                <User size={16} /> Investor
              </h3>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-slate-500">Name</dt>
                  <dd className="font-medium">{investor.full_name}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Code</dt>
                  <dd className="font-mono text-xs">{investor.investor_code}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Type</dt>
                  <dd>{investor.investor_type}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Status</dt>
                  <dd><StatusBadge status={investor.account_status} /></dd>
                </div>
                {investor.portfolio && (
                  <>
                    <div className="flex justify-between">
                      <dt className="text-slate-500">Positions</dt>
                      <dd>{investor.portfolio.positions}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-slate-500">Portfolio Value</dt>
                      <dd className="font-medium">
                        {investor.portfolio.total_value?.toLocaleString('en-US', { style: 'currency', currency: 'SAR' })}
                      </dd>
                    </div>
                  </>
                )}
              </dl>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
