import { useEffect, useState } from 'react';
import { cx, aiApi } from '../lib/api';
import Loader from '../components/Loader';
import { BookOpen, Search, ChevronDown, ChevronUp } from 'lucide-react';

export default function KnowledgeBase() {
  const [articles, setArticles] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedId, setExpandedId] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadArticles = (category, search) => {
    const params = {};
    if (category) params.category = category;
    if (search) params.search = search;
    const useSemantic = search && search.trim().length > 2;
    if (useSemantic) {
      aiApi.kbSemanticSearch({ query: search.trim(), limit: 25, category: category || undefined })
        .then(setArticles)
        .catch(() => cx.kbArticles(params).then(setArticles).catch(() => setArticles([])))
        .finally(() => setLoading(false));
    } else {
      cx.kbArticles(params)
        .then(setArticles)
        .catch(() => setArticles([]))
        .finally(() => setLoading(false));
    }
  };

  useEffect(() => {
    cx.kbCategories().then(setCategories).catch(() => []);
    loadArticles();
  }, []);

  const handleSearch = () => {
    setLoading(true);
    loadArticles(selectedCategory, searchTerm);
  };

  const handleCategoryChange = (cat) => {
    setSelectedCategory(cat);
    setLoading(true);
    loadArticles(cat, searchTerm);
  };

  if (loading && articles.length === 0) return <Loader />;

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold flex items-center gap-2">
        <BookOpen size={24} /> Knowledge Base
      </h1>

      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search articles..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <select
          value={selectedCategory}
          onChange={(e) => handleCategoryChange(e.target.value)}
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">All Categories</option>
          {categories.map(cat => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>
        <button
          onClick={handleSearch}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700"
        >
          Search
        </button>
      </div>

      {articles.length === 0 ? (
        <div className="card p-12 text-center text-slate-400">No articles found</div>
      ) : (
        <div className="space-y-2">
          {articles.map(article => (
            <div key={article.article_id} className="card overflow-hidden">
              <button
                onClick={() => setExpandedId(expandedId === article.article_id ? null : article.article_id)}
                className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-slate-50"
              >
                <div>
                  <h3 className="font-medium text-slate-900">{article.title}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 text-xs rounded-full font-medium">
                      {article.category}
                    </span>
                    {article.tags && article.tags.split(',').slice(0, 3).map(tag => (
                      <span key={tag} className="px-1.5 py-0.5 bg-slate-100 text-slate-500 text-[10px] rounded">
                        {tag.trim()}
                      </span>
                    ))}
                  </div>
                </div>
                {expandedId === article.article_id ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
              </button>
              {expandedId === article.article_id && (
                <div className="px-4 pb-4 border-t border-slate-100">
                  <pre className="mt-3 text-sm text-slate-700 whitespace-pre-wrap font-sans leading-relaxed">
                    {article.content}
                  </pre>
                  <div className="mt-3 text-xs text-slate-400">
                    Last updated: {article.updated_at}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
