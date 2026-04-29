import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import type { Underlying } from "@/lib/api";

function useDebounce(value: string, delay: number) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

const TYPE_STYLES: Record<string, string> = {
  EQ: "bg-emerald-500/15 text-emerald-400",
  FUT: "bg-blue-500/15 text-blue-400",
  INDICES: "bg-purple-500/15 text-purple-400",
};

function TypeBadge({ type }: { type: string }) {
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${TYPE_STYLES[type] ?? "bg-bg-elevated text-text-muted"}`}
    >
      {type}
    </span>
  );
}

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Underlying[]>([]);
  const [cachePopulated, setCachePopulated] = useState(true);
  const [open, setOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const debouncedQuery = useDebounce(query, 300);

  // Derived: spinner shows while the debounce is pending (before the API call fires)
  const loading = query.trim() !== debouncedQuery.trim() && query.trim().length > 0;

  useEffect(() => {
    if (!debouncedQuery.trim()) return;

    let cancelled = false;

    api.searchUnderlyings(debouncedQuery)
      .then((res) => {
        if (cancelled) return;
        setResults(res.results);
        setCachePopulated(res.cache_populated);
        setActiveIdx(-1);
      })
      .catch(() => {
        if (!cancelled) setResults([]);
      });

    return () => { cancelled = true; };
  }, [debouncedQuery]);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  function handleSelect(item: Underlying) {
    navigate(`/symbol/${item.instrument_token}`);
    setQuery("");
    setOpen(false);
    setResults([]);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!open) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && activeIdx >= 0) {
      e.preventDefault();
      handleSelect(results[activeIdx]);
    } else if (e.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
    }
  }

  const hasQuery = query.trim().length > 0;
  const showDropdown = open && hasQuery;

  function renderDropdownBody() {
    if (loading) return null;
    if (!cachePopulated) {
      return (
        <p className="px-3 py-2.5 text-xs text-[var(--color-text-muted)]">
          Instrument data not loaded — authenticate with Kite first.
        </p>
      );
    }
    if (results.length === 0) {
      return (
        <p className="px-3 py-2.5 text-xs text-[var(--color-text-muted)]">No results found</p>
      );
    }
    return (
      <ul>
        {results.map((item, idx) => (
          <li key={item.instrument_token}>
            <button
              onMouseDown={() => handleSelect(item)}
              onMouseEnter={() => setActiveIdx(idx)}
              className={`flex w-full items-center justify-between px-3 py-2 text-left text-xs transition ${
                activeIdx === idx
                  ? "bg-[var(--color-accent)]/10 text-[var(--color-accent)]"
                  : "text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)]"
              }`}
            >
              <span className="font-medium">{item.symbol}</span>
              <span className="flex items-center gap-1">
                <TypeBadge type={item.instrument_type} />
                <span className="rounded px-1.5 py-0.5 text-[10px] font-medium bg-bg-elevated text-text-muted">
                  {item.exchange}
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div ref={containerRef} className="relative w-72">
      <div className="flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-3 py-1.5">
        <svg className="h-3.5 w-3.5 shrink-0 text-[var(--color-text-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="Search symbol…"
          className="w-full bg-transparent text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none"
        />
        {loading && (
          <svg className="h-3 w-3 shrink-0 animate-spin text-[var(--color-text-muted)]" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        )}
      </div>

      {showDropdown && (
        <div className="absolute left-0 top-full z-50 mt-1 w-full overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-surface)] shadow-lg">
          {renderDropdownBody()}
        </div>
      )}
    </div>
  );
}
