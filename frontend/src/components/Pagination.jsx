import { ChevronLeft, ChevronRight } from 'lucide-react';

export default function Pagination({ offset, limit, total, onChange }) {
  if (!total || total <= limit) return null;

  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);

  function goTo(page) {
    const clamped = Math.max(1, Math.min(page, totalPages));
    onChange((clamped - 1) * limit);
  }

  const pages = [];
  const range = 2;
  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || (i >= currentPage - range && i <= currentPage + range)) {
      pages.push(i);
    } else if (pages[pages.length - 1] !== '...') {
      pages.push('...');
    }
  }

  return (
    <div className="flex items-center justify-between pt-4">
      <span className="text-sm text-slate-500">
        Showing {Math.min(offset + 1, total)}–{Math.min(offset + limit, total)} of {total}
      </span>
      <div className="flex items-center gap-1">
        <button
          onClick={() => goTo(currentPage - 1)}
          disabled={currentPage <= 1}
          className="p-1.5 rounded hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <ChevronLeft size={16} />
        </button>
        {pages.map((p, i) =>
          p === '...' ? (
            <span key={`dots-${i}`} className="px-1 text-slate-400">...</span>
          ) : (
            <button
              key={p}
              onClick={() => goTo(p)}
              className={`min-w-[32px] h-8 rounded text-sm font-medium ${
                p === currentPage
                  ? 'bg-indigo-600 text-white'
                  : 'hover:bg-slate-100 text-slate-600'
              }`}
            >
              {p}
            </button>
          )
        )}
        <button
          onClick={() => goTo(currentPage + 1)}
          disabled={currentPage >= totalPages}
          className="p-1.5 rounded hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}
