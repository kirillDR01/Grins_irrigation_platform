import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X, Users, Briefcase, Loader2 } from 'lucide-react';
import { useDebounce } from '@/shared/hooks';
import { customerApi } from '@/features/customers/api/customerApi';
import { jobApi } from '@/features/jobs/api/jobApi';
import type { Customer } from '@/features/customers/types';
import type { Job } from '@/features/jobs/types';
import { cn } from '@/shared/utils/cn';

interface SearchResult {
  type: 'customer' | 'job';
  id: string;
  title: string;
  subtitle: string;
  href: string;
}

export function GlobalSearch() {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const debouncedQuery = useDebounce(query, 300);

  // Search across all entities
  const performSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([]);
      return;
    }

    setIsLoading(true);
    try {
      // Note: Invoice API doesn't support search, so we only search customers and jobs
      const [customersRes, jobsRes] = await Promise.allSettled([
        customerApi.search(searchQuery),
        jobApi.search(searchQuery),
      ]);

      const searchResults: SearchResult[] = [];

      // Process customers
      if (customersRes.status === 'fulfilled') {
        customersRes.value.items.slice(0, 5).forEach((customer: Customer) => {
          searchResults.push({
            type: 'customer',
            id: customer.id,
            title: `${customer.first_name} ${customer.last_name}`,
            subtitle: customer.phone,
            href: `/customers/${customer.id}`,
          });
        });
      }

      // Process jobs
      if (jobsRes.status === 'fulfilled') {
        jobsRes.value.items.slice(0, 5).forEach((job: Job) => {
          searchResults.push({
            type: 'job',
            id: job.id,
            title: job.job_type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
            subtitle: job.status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
            href: `/jobs/${job.id}`,
          });
        });
      }

      setResults(searchResults);
      setSelectedIndex(0);
    } catch (error) {
      console.error('Search error:', error);
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Trigger search when debounced query changes
  useEffect(() => {
    performSearch(debouncedQuery);
  }, [debouncedQuery, performSearch]);

  // Handle click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || results.length === 0) {
      if (e.key === 'Escape') {
        setQuery('');
        setIsOpen(false);
        inputRef.current?.blur();
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % results.length);
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + results.length) % results.length);
        break;
      case 'Enter':
        e.preventDefault();
        if (results[selectedIndex]) {
          navigate(results[selectedIndex].href);
          setQuery('');
          setIsOpen(false);
        }
        break;
      case 'Escape':
        setQuery('');
        setIsOpen(false);
        inputRef.current?.blur();
        break;
    }
  };

  const handleResultClick = (result: SearchResult) => {
    navigate(result.href);
    setQuery('');
    setIsOpen(false);
  };

  const handleClear = () => {
    setQuery('');
    setResults([]);
    setIsOpen(false);
    inputRef.current?.focus();
  };

  const getIcon = (type: SearchResult['type']) => {
    switch (type) {
      case 'customer':
        return <Users className="h-4 w-4 text-teal-500" />;
      case 'job':
        return <Briefcase className="h-4 w-4 text-blue-500" />;
    }
  };

  const getTypeLabel = (type: SearchResult['type']) => {
    switch (type) {
      case 'customer':
        return 'Customer';
      case 'job':
        return 'Job';
    }
  };

  return (
    <div ref={containerRef} className="relative w-full" data-testid="global-search-container">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="Search customers, jobs..."
          className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-10 pr-10 py-2 text-sm text-slate-600 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-100 focus:border-teal-500 transition-colors"
          data-testid="global-search-input"
        />
        {isLoading && (
          <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 animate-spin" />
        )}
        {!isLoading && query && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
            data-testid="global-search-clear"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Results dropdown */}
      {isOpen && query.trim() && (
        <div
          className="absolute top-full left-0 right-0 mt-2 bg-white rounded-lg shadow-lg border border-slate-200 overflow-hidden z-50"
          data-testid="global-search-results"
        >
          {isLoading ? (
            <div className="p-4 text-center text-slate-500 text-sm">
              <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2" />
              Searching...
            </div>
          ) : results.length > 0 ? (
            <ul className="max-h-80 overflow-y-auto">
              {results.map((result, index) => (
                <li key={`${result.type}-${result.id}`}>
                  <button
                    type="button"
                    onClick={() => handleResultClick(result)}
                    onMouseEnter={() => setSelectedIndex(index)}
                    className={cn(
                      'w-full flex items-center gap-3 px-4 py-3 text-left transition-colors',
                      index === selectedIndex ? 'bg-slate-50' : 'hover:bg-slate-50'
                    )}
                    data-testid={`search-result-${result.type}-${result.id}`}
                  >
                    <div className="flex-shrink-0">{getIcon(result.type)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-slate-900 truncate">
                        {result.title}
                      </div>
                      <div className="text-xs text-slate-500 truncate">{result.subtitle}</div>
                    </div>
                    <div className="flex-shrink-0">
                      <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                        {getTypeLabel(result.type)}
                      </span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="p-4 text-center text-slate-500 text-sm" data-testid="no-search-results">
              No results found for "{query}"
            </div>
          )}

          {/* Keyboard hints */}
          {results.length > 0 && (
            <div className="px-4 py-2 border-t border-slate-100 bg-slate-50 text-xs text-slate-400 flex items-center gap-4">
              <span>
                <kbd className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-[10px]">↑</kbd>
                <kbd className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-[10px] ml-1">↓</kbd>
                <span className="ml-1">to navigate</span>
              </span>
              <span>
                <kbd className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-[10px]">Enter</kbd>
                <span className="ml-1">to select</span>
              </span>
              <span>
                <kbd className="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-[10px]">Esc</kbd>
                <span className="ml-1">to close</span>
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
