import { useState, useEffect } from 'react';
import { verification } from '../lib/api';
import { useToast } from './Toast';
import {
  Shield,
  CheckCircle,
  XCircle,
  Loader2,
  User,
  CreditCard,
  Phone,
  Activity,
  Lock,
} from 'lucide-react';

const STEP_CONFIG = {
  full_name: { label: 'Full Name', prompt: 'Ask the caller to state their full name', icon: User },
  national_id: { label: 'National ID', prompt: 'Ask for the last 4 digits of their National ID', icon: CreditCard },
  mobile_number: { label: 'Mobile Number', prompt: 'Confirm the registered mobile number', icon: Phone },
  account_status: { label: 'Account Status', prompt: 'Confirm account activity details', icon: Activity },
};

const STATUS_STYLES = {
  passed: 'bg-green-100 text-green-700 border-green-300',
  failed: 'bg-red-100 text-red-700 border-red-300',
  in_progress: 'bg-blue-100 text-blue-700 border-blue-300',
  pending: 'bg-slate-100 text-slate-500 border-slate-200',
};

export default function VerificationWizard({
  investorId,
  callId,
  caseId,
  onComplete,
  compact = false,
}) {
  const toast = useToast();
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stepping, setStepping] = useState(null);

  useEffect(() => {
    if (caseId) {
      verification.forCase(caseId).then((v) => {
        if (v?.verification_id) setSession(v);
      }).catch(() => {});
    }
  }, [caseId]);

  async function handleStart() {
    if (!investorId) {
      toast('No investor linked — cannot verify', 'warning');
      return;
    }
    setLoading(true);
    try {
      const s = await verification.start({
        investor_id: parseInt(investorId),
        call_id: callId ? parseInt(callId) : undefined,
        method: 'verbal',
      });
      setSession(s);
      toast('Verification session started', 'success');
    } catch (err) {
      toast(err.message || 'Failed to start verification', 'error');
    } finally {
      setLoading(false);
    }
  }

  async function handleStep(step, passed) {
    if (!session) return;
    setStepping(step);
    try {
      const updated = await verification.updateStep(session.verification_id, { step, passed });
      setSession(updated);
      if (updated.status === 'passed') {
        if (caseId) {
          await verification.linkToCase(updated.verification_id, { case_id: Number(caseId) }).catch(() => {});
        }
        toast('Identity verified successfully', 'success');
        onComplete?.(updated);
      } else if (updated.status === 'failed') {
        toast('Verification failed — identity could not be confirmed', 'error');
        onComplete?.(updated);
      }
    } catch (err) {
      toast(err.message || 'Failed to update step', 'error');
    } finally {
      setStepping(null);
    }
  }

  if (!session) {
    return (
      <div className={`${compact ? '' : 'card p-4 sm:p-5'}`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Lock size={16} className="text-amber-500 shrink-0" />
            <span className="text-sm font-medium text-slate-700">Identity Verification</span>
          </div>
          <button
            onClick={handleStart}
            disabled={loading || !investorId}
            className="btn-primary text-sm flex items-center gap-2 min-h-[44px]"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Shield size={14} />}
            Start Verification
          </button>
        </div>
        {!investorId && (
          <p className="text-xs text-slate-400 mt-2">
            Link an investor to this case to enable verification
          </p>
        )}
      </div>
    );
  }

  const isTerminal = session.status === 'passed' || session.status === 'failed';
  const steps = session.steps_required || [];
  const completed = session.steps_completed || {};
  const completedCount = Object.keys(completed).length;

  return (
    <div className={`${compact ? '' : 'card p-4 sm:p-5'} space-y-3 ${compact ? '' : 'max-h-[85vh] overflow-y-auto'}`}>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap min-w-0">
          <Shield size={16} className={
            session.status === 'passed' ? 'text-green-500' :
            session.status === 'failed' ? 'text-red-500' : 'text-blue-500 shrink-0'
          } />
          <span className="text-sm font-semibold text-slate-700">Identity Verification</span>
          <span className={`badge text-xs ${STATUS_STYLES[session.status] || ''}`}>
            {session.status}
          </span>
        </div>
        <span className="text-xs text-slate-400">
          {completedCount}/{steps.length} steps
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-slate-100 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all ${
            session.status === 'passed' ? 'bg-green-500' :
            session.status === 'failed' ? 'bg-red-500' : 'bg-blue-500'
          }`}
          style={{ width: `${(completedCount / Math.max(steps.length, 1)) * 100}%` }}
        />
      </div>

      {/* Investor info */}
      {session.investor_name && (
        <div className="bg-slate-50 rounded-lg px-3 py-2 text-sm flex items-center gap-2">
          <User size={14} className="text-slate-400" />
          <span className="font-medium">{session.investor_name}</span>
          {session.investor_code && (
            <span className="text-xs text-slate-400 font-mono">{session.investor_code}</span>
          )}
        </div>
      )}

      {/* Steps */}
      <div className="space-y-2">
        {steps.map((step) => {
          const config = STEP_CONFIG[step] || { label: step, prompt: '', icon: Shield };
          const Icon = config.icon;
          const result = completed[step];
          const isPending = !result;
          const isCurrent = isPending && !isTerminal;

          return (
            <div
              key={step}
              className={`rounded-lg border p-3 transition-all ${
                result === 'passed' ? 'border-green-200 bg-green-50' :
                result === 'failed' ? 'border-red-200 bg-red-50' :
                isCurrent ? 'border-blue-200 bg-blue-50 ring-1 ring-blue-300' :
                'border-slate-200 bg-white'
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <Icon size={14} className={
                    result === 'passed' ? 'text-green-600' :
                    result === 'failed' ? 'text-red-600' :
                    isCurrent ? 'text-blue-600' : 'text-slate-400 shrink-0'
                  } />
                  <span className="text-sm font-medium">{config.label}</span>
                  {result && (
                    result === 'passed'
                      ? <CheckCircle size={14} className="text-green-500" />
                      : <XCircle size={14} className="text-red-500" />
                  )}
                </div>

                {isCurrent && (
                  <div className="flex gap-1.5 flex-shrink-0">
                    <button
                      onClick={() => handleStep(step, true)}
                      disabled={stepping === step}
                      className="bg-green-500 hover:bg-green-600 text-white text-xs px-3 py-2 sm:py-1.5 rounded-lg
                        flex items-center gap-1 transition-colors min-h-[44px] touch-manipulation"
                    >
                      {stepping === step
                        ? <Loader2 size={12} className="animate-spin" />
                        : <CheckCircle size={12} />}
                      Pass
                    </button>
                    <button
                      onClick={() => handleStep(step, false)}
                      disabled={stepping === step}
                      className="bg-red-500 hover:bg-red-600 text-white text-xs px-3 py-2 sm:py-1.5 rounded-lg
                        flex items-center gap-1 transition-colors min-h-[44px] touch-manipulation"
                    >
                      <XCircle size={12} /> Fail
                    </button>
                  </div>
                )}
              </div>

              {isCurrent && config.prompt && (
                <p className="text-xs text-blue-600 mt-1.5 ml-6">{config.prompt}</p>
              )}
            </div>
          );
        })}
      </div>

      {/* Terminal status */}
      {isTerminal && (
        <div className={`rounded-lg p-3 text-sm font-medium text-center ${
          session.status === 'passed'
            ? 'bg-green-100 text-green-700'
            : 'bg-red-100 text-red-700'
        }`}>
          {session.status === 'passed'
            ? 'Identity verified — caller confirmed'
            : `Verification failed${session.failure_reason ? `: ${session.failure_reason}` : ''}`}
        </div>
      )}

      {/* Method badge */}
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <span>Method: {session.method}</span>
        {session.created_at && <span>· Started: {new Date(session.created_at).toLocaleTimeString()}</span>}
      </div>
    </div>
  );
}
