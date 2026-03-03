import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { cases, registry } from '../lib/api';
import { FolderPlus, PhoneCall, User } from 'lucide-react';

export default function CreateCase() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const prefillInvestorId = searchParams.get('investor_id') || '';
  const prefillCallId = searchParams.get('call_id') || '';

  const [form, setForm] = useState({
    subject: '',
    description: '',
    priority: 'medium',
    investor_id: prefillInvestorId,
    call_id: prefillCallId,
  });
  const [investorInfo, setInvestorInfo] = useState(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (prefillInvestorId) {
      registry.investorProfile(prefillInvestorId)
        .then(setInvestorInfo)
        .catch(() => {});
    }
  }, [prefillInvestorId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const body = { ...form };
      if (!body.investor_id) delete body.investor_id;
      else body.investor_id = parseInt(body.investor_id);
      if (!body.call_id) delete body.call_id;
      else body.call_id = parseInt(body.call_id);
      const created = await cases.create(body);
      navigate(`/cases/${created.case_id || created.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold flex items-center gap-2 mb-6">
        <FolderPlus size={24} /> Create New Case
      </h1>

      {/* Context banner from screen-pop */}
      {(investorInfo || prefillCallId) && (
        <div className="card p-4 mb-6 bg-indigo-50 border-indigo-200">
          <p className="text-xs font-semibold text-indigo-600 mb-2">Case linked from incoming call</p>
          <div className="flex gap-6 text-sm">
            {investorInfo && (
              <div className="flex items-center gap-2">
                <User size={16} className="text-indigo-500" />
                <span className="font-medium">{investorInfo.full_name}</span>
                <span className="text-slate-400 font-mono text-xs">{investorInfo.investor_code}</span>
              </div>
            )}
            {prefillCallId && (
              <div className="flex items-center gap-2">
                <PhoneCall size={16} className="text-indigo-500" />
                <span className="text-slate-500">Call #{prefillCallId}</span>
              </div>
            )}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="card p-6 space-y-5">
        <div>
          <label className="label">Subject *</label>
          <input
            type="text"
            value={form.subject}
            onChange={(e) => setForm({ ...form, subject: e.target.value })}
            className="input"
            placeholder="Brief summary of the issue"
            required
          />
        </div>

        <div>
          <label className="label">Description</label>
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="input h-32 resize-none"
            placeholder="Detailed description..."
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Priority</label>
            <select
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: e.target.value })}
              className="input"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          <div>
            <label className="label">Investor ID</label>
            <input
              type="text"
              value={form.investor_id}
              onChange={(e) => setForm({ ...form, investor_id: e.target.value })}
              className="input"
              placeholder="Optional"
            />
          </div>
        </div>

        {error && (
          <div className="text-sm text-red-600 bg-red-50 rounded-lg p-3">{error}</div>
        )}

        <div className="flex gap-3">
          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? 'Creating...' : 'Create Case'}
          </button>
          <button type="button" onClick={() => navigate(-1)} className="btn-secondary">
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
