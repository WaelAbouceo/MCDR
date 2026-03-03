import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { registry } from '../lib/api';
import Loader from '../components/Loader';
import { StatusBadge } from '../components/StatusBadge';
import { Search, User, Briefcase, Smartphone, FolderPlus } from 'lucide-react';

export default function InvestorSearch() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setSelected(null);
    try {
      const data = await registry.searchInvestors({ name: query, limit: 20 });
      setResults(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const selectInvestor = async (inv) => {
    setDetailLoading(true);
    try {
      const profile = await registry.investorProfile(inv.investor_id);
      setSelected(profile);
    } catch {
      setSelected(inv);
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold flex items-center gap-2">
        <Search size={24} /> Investor Lookup
      </h1>

      <div className="card p-4">
        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="input pl-9"
              placeholder="Search by investor name..."
            />
          </div>
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          {results.length > 0 && (
            <div className="card overflow-hidden">
              <div className="p-3 bg-slate-50 border-b border-slate-200">
                <p className="text-sm text-slate-500">{results.length} results</p>
              </div>
              <div className="divide-y divide-slate-100 max-h-[500px] overflow-y-auto">
                {results.map((inv) => (
                  <button
                    key={inv.investor_id}
                    onClick={() => selectInvestor(inv)}
                    className={`w-full text-left p-4 hover:bg-slate-50 transition-colors ${
                      selected?.investor_id === inv.investor_id ? 'bg-indigo-50 border-l-4 border-indigo-600' : ''
                    }`}
                  >
                    <p className="font-medium text-sm">{inv.full_name}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {inv.investor_code} · {inv.investor_type}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="lg:col-span-2">
          {detailLoading && <Loader />}
          {selected && !detailLoading && (
            <div className="space-y-4">
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => navigate(`/cases/new?investor_id=${selected.investor_id}`)}
                  className="btn-primary text-sm flex items-center gap-2"
                >
                  <FolderPlus size={16} /> Create Case for {selected.full_name?.split(' ')[0]}
                </button>
              </div>
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
                  <User size={16} /> Investor Profile
                </h3>
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <dt className="text-slate-500">Name</dt>
                    <dd className="font-medium">{selected.full_name}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Code</dt>
                    <dd className="font-mono">{selected.investor_code}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Type</dt>
                    <dd>{selected.investor_type}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Status</dt>
                    <dd><StatusBadge status={selected.account_status} /></dd>
                  </div>
                  {selected.national_id && (
                    <div>
                      <dt className="text-slate-500">National ID</dt>
                      <dd className="font-mono text-xs">{selected.national_id}</dd>
                    </div>
                  )}
                </dl>
              </div>

              {selected.app_user && (
                <div className="card p-5">
                  <h3 className="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
                    <Smartphone size={16} /> Mobile App User
                  </h3>
                  <dl className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <dt className="text-slate-500">Mobile</dt>
                      <dd>{selected.app_user.mobile}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-500">Email</dt>
                      <dd>{selected.app_user.email}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-500">Status</dt>
                      <dd><StatusBadge status={selected.app_user.status} /></dd>
                    </div>
                    <div>
                      <dt className="text-slate-500">OTP Verified</dt>
                      <dd>{selected.app_user.otp_verified ? 'Yes' : 'No'}</dd>
                    </div>
                  </dl>
                </div>
              )}

              {selected.portfolio && (
                <div className="card p-5">
                  <h3 className="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
                    <Briefcase size={16} /> Portfolio Summary
                  </h3>
                  <dl className="grid grid-cols-3 gap-3 text-sm">
                    <div className="text-center p-3 bg-slate-50 rounded-lg">
                      <dd className="text-xl font-bold">{selected.portfolio.positions}</dd>
                      <dt className="text-xs text-slate-500">Positions</dt>
                    </div>
                    <div className="text-center p-3 bg-slate-50 rounded-lg">
                      <dd className="text-xl font-bold">{selected.portfolio.total_shares?.toLocaleString()}</dd>
                      <dt className="text-xs text-slate-500">Total Shares</dt>
                    </div>
                    <div className="text-center p-3 bg-green-50 rounded-lg">
                      <dd className="text-xl font-bold text-green-600">
                        {selected.portfolio.total_value?.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                      </dd>
                      <dt className="text-xs text-slate-500">Total Value (SAR)</dt>
                    </div>
                  </dl>
                  {selected.portfolio.sectors && Object.keys(selected.portfolio.sectors).length > 0 && (
                    <div className="mt-4">
                      <p className="text-xs text-slate-500 mb-2">Sector Distribution</p>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(selected.portfolio.sectors).map(([sector, count]) => (
                          <span key={sector} className="badge bg-indigo-100 text-indigo-700">
                            {sector}: {count}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
