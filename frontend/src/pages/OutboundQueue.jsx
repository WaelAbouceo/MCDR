import { useEffect, useState } from 'react';
import { useAuth } from '../lib/auth';
import { outbound } from '../lib/api';
import { StatusBadge, PriorityBadge } from '../components/StatusBadge';
import StatCard from '../components/StatCard';
import { useToast } from '../components/Toast';
import Loader from '../components/Loader';
import { format } from 'date-fns';
import {
  PhoneOutgoing,
  Plus,
  CheckCircle,
  Clock,
  AlertTriangle,
  Filter,
  User,
  X,
} from 'lucide-react';

const TASK_TYPE_LABELS = {
  broken_signup: 'Broken Sign-up',
  inactive_user: 'Inactive User',
  transaction_verification: 'Transaction Verification',
  qa_callback: 'QA Callback',
};

const TASK_TYPE_COLORS = {
  broken_signup: 'bg-amber-100 text-amber-700',
  inactive_user: 'bg-blue-100 text-blue-700',
  transaction_verification: 'bg-purple-100 text-purple-700',
  qa_callback: 'bg-teal-100 text-teal-700',
};

export default function OutboundQueue() {
  const { user } = useAuth();
  const toast = useToast();
  const [tasks, setTasks] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ status: '', task_type: '' });
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newTask, setNewTask] = useState({
    task_type: 'broken_signup',
    investor_id: '',
    priority: 'medium',
    notes: '',
  });
  const [selectedTask, setSelectedTask] = useState(null);
  const [outcome, setOutcome] = useState('');

  async function loadData() {
    setLoading(true);
    try {
      const params = {};
      if (filter.status) params.status = filter.status;
      if (filter.task_type) params.task_type = filter.task_type;
      const [taskList, taskStats] = await Promise.all([
        outbound.list(params),
        outbound.stats(),
      ]);
      setTasks(taskList);
      setStats(taskStats);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadData(); }, [filter.status, filter.task_type]);

  async function handleCreate(e) {
    e.preventDefault();
    setCreating(true);
    try {
      const body = { ...newTask };
      if (!body.investor_id) delete body.investor_id;
      else body.investor_id = parseInt(body.investor_id);
      await outbound.create(body);
      toast('Outbound task created', 'success');
      setShowCreate(false);
      setNewTask({ task_type: 'broken_signup', investor_id: '', priority: 'medium', notes: '' });
      loadData();
    } catch (err) {
      toast(err.message || 'Failed to create task', 'error');
    } finally {
      setCreating(false);
    }
  }

  async function handlePickUp(task) {
    try {
      await outbound.update(task.task_id, { status: 'in_progress' });
      toast('Task picked up', 'success');
      loadData();
    } catch (err) {
      toast(err.message, 'error');
    }
  }

  async function handleComplete(task) {
    if (!outcome.trim()) {
      toast('Please enter an outcome', 'warning');
      return;
    }
    try {
      await outbound.update(task.task_id, { status: 'completed', outcome });
      toast('Task completed', 'success');
      setSelectedTask(null);
      setOutcome('');
      loadData();
    } catch (err) {
      toast(err.message, 'error');
    }
  }

  async function handleFail(task) {
    try {
      await outbound.update(task.task_id, {
        status: 'failed',
        outcome: outcome || 'No answer / unreachable',
      });
      toast('Task marked as failed', 'success');
      setSelectedTask(null);
      setOutcome('');
      loadData();
    } catch (err) {
      toast(err.message, 'error');
    }
  }

  if (loading) return <Loader />;

  const s = stats || {};
  const byStatus = s.by_status || {};
  const byType = s.by_type || {};

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <PhoneOutgoing size={24} /> Outbound Queue
        </h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="btn-primary text-sm flex items-center gap-2"
        >
          {showCreate ? <X size={14} /> : <Plus size={14} />}
          {showCreate ? 'Cancel' : 'New Task'}
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Pending" value={byStatus.pending || 0} icon={Clock} color="blue" />
        <StatCard label="In Progress" value={byStatus.in_progress || 0} icon={PhoneOutgoing} color="amber" />
        <StatCard label="Completed Today" value={s.completed_today || 0} icon={CheckCircle} color="green" />
        <StatCard label="Failed" value={byStatus.failed || 0} icon={AlertTriangle} color="red" />
      </div>

      {/* Create Form */}
      {showCreate && (
        <form onSubmit={handleCreate} className="card p-5 space-y-4 border-2 border-indigo-200">
          <h3 className="text-sm font-semibold text-slate-600">Create Outbound Task</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Task Type *</label>
              <select
                value={newTask.task_type}
                onChange={(e) => setNewTask({ ...newTask, task_type: e.target.value })}
                className="input"
              >
                {Object.entries(TASK_TYPE_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Priority</label>
              <select
                value={newTask.priority}
                onChange={(e) => setNewTask({ ...newTask, priority: e.target.value })}
                className="input"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
          </div>
          <div>
            <label className="label">Investor ID (optional)</label>
            <input
              type="text"
              value={newTask.investor_id}
              onChange={(e) => setNewTask({ ...newTask, investor_id: e.target.value })}
              className="input"
              placeholder="e.g. 42"
            />
          </div>
          <div>
            <label className="label">Notes</label>
            <textarea
              value={newTask.notes}
              onChange={(e) => setNewTask({ ...newTask, notes: e.target.value })}
              className="input h-20 resize-none"
              placeholder="Context for the outbound call..."
            />
          </div>
          <button type="submit" disabled={creating} className="btn-primary text-sm">
            {creating ? 'Creating...' : 'Create Task'}
          </button>
        </form>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Filter size={16} className="text-slate-400" />
        <select
          value={filter.status}
          onChange={(e) => setFilter({ ...filter, status: e.target.value })}
          className="input py-1.5 w-auto text-sm"
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
        <select
          value={filter.task_type}
          onChange={(e) => setFilter({ ...filter, task_type: e.target.value })}
          className="input py-1.5 w-auto text-sm"
        >
          <option value="">All Types</option>
          {Object.entries(TASK_TYPE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <span className="text-xs text-slate-400">{tasks.length} tasks</span>
      </div>

      {/* Task List */}
      <div className="space-y-3">
        {tasks.length === 0 ? (
          <div className="card p-8 text-center text-slate-400">
            <PhoneOutgoing size={32} className="mx-auto mb-2 opacity-40" />
            <p>No outbound tasks match your filters</p>
          </div>
        ) : (
          tasks.map((t) => (
            <div
              key={t.task_id}
              className={`card p-4 hover:shadow-md transition-shadow cursor-pointer ${
                selectedTask?.task_id === t.task_id ? 'ring-2 ring-indigo-300' : ''
              }`}
              onClick={() => setSelectedTask(selectedTask?.task_id === t.task_id ? null : t)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center">
                    <PhoneOutgoing size={18} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`badge text-xs ${TASK_TYPE_COLORS[t.task_type] || ''}`}>
                        {TASK_TYPE_LABELS[t.task_type] || t.task_type}
                      </span>
                      <PriorityBadge priority={t.priority} />
                      <StatusBadge status={t.status} />
                    </div>
                    <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                      {t.investor_name && (
                        <span className="flex items-center gap-1">
                          <User size={10} /> {t.investor_name}
                          {t.investor_code && <span className="text-slate-400">({t.investor_code})</span>}
                        </span>
                      )}
                      {t.agent_name && <span>· Agent: {t.agent_name}</span>}
                      {t.scheduled_at && (
                        <span>· Scheduled: {format(new Date(t.scheduled_at), 'MMM d, HH:mm')}</span>
                      )}
                    </div>
                  </div>
                </div>
                <span className="font-mono text-xs text-slate-400">#{t.task_id}</span>
              </div>

              {t.notes && (
                <p className="text-sm text-slate-600 mt-2 pl-13">{t.notes}</p>
              )}

              {/* Expanded Actions */}
              {selectedTask?.task_id === t.task_id && (
                <div className="mt-4 pt-4 border-t border-slate-100 space-y-3" onClick={(e) => e.stopPropagation()}>
                  {t.status === 'pending' && (
                    <button
                      onClick={() => handlePickUp(t)}
                      className="btn-primary text-sm flex items-center gap-2"
                    >
                      <PhoneOutgoing size={14} /> Pick Up & Start Call
                    </button>
                  )}
                  {t.status === 'in_progress' && (
                    <>
                      <textarea
                        value={outcome}
                        onChange={(e) => setOutcome(e.target.value)}
                        placeholder="Call outcome / notes..."
                        className="input h-20 resize-none text-sm"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleComplete(t)}
                          className="btn-primary text-sm flex-1 flex items-center justify-center gap-2"
                        >
                          <CheckCircle size={14} /> Complete
                        </button>
                        <button
                          onClick={() => handleFail(t)}
                          className="btn-danger text-sm flex-1 flex items-center justify-center gap-2"
                        >
                          <AlertTriangle size={14} /> Failed / No Answer
                        </button>
                      </div>
                    </>
                  )}
                  {t.outcome && (
                    <div className="bg-slate-50 rounded-lg p-3 text-sm">
                      <span className="text-xs font-semibold text-slate-500">Outcome:</span>
                      <p className="text-slate-700 mt-1">{t.outcome}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
