import { Loader2 } from 'lucide-react';

export default function Loader({ text = 'Loading...' }) {
  return (
    <div className="flex items-center justify-center py-20">
      <Loader2 className="animate-spin text-indigo-600 mr-3" size={24} />
      <span className="text-slate-500">{text}</span>
    </div>
  );
}
