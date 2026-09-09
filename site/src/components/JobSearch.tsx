import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { postedAt } from '../lib/dates';
import { loadAllJobs, loadManifest, resetDataLoader } from '../lib/data-loader';
import {
  countActiveFilters,
  DEFAULT_FILTERS,
  parseFiltersFromUrl,
  serializeFiltersToUrl,
  type FilterState,
} from '../lib/filters';
import {
  buildSearchIndex,
  collectFacetValues,
  computeStats,
  filterJobs,
  getMobilityClaims,
  paginateJobs,
  totalPages,
} from '../lib/search';
import {
  loadPreferences,
  recordVisit,
  setOriginCountry,
  toggleDismissedJob,
  toggleSavedJob,
} from '../lib/storage';
import type { Job, MobilityFlag, SiteStats, SortMode } from '../lib/types';
import EvidenceModal from './EvidenceModal';
import FilterPanel from './FilterPanel';
import JobRow from './JobRow';
import StatsBar from './StatsBar';

interface JobSearchProps {
  initialStats?: SiteStats;
  companySlug?: string;
  showStats?: boolean;
}

interface EvidenceState {
  job: Job;
  flag: MobilityFlag;
}

const EMPTY_STATS: SiteStats = {
  totalJobs: 0,
  totalCompanies: 0,
  withVisa: 0,
  withRelocation: 0,
  remoteCount: 0,
  newSinceVisit: 0,
  generatedAt: new Date().toISOString(),
};

export default function JobSearch({
  initialStats,
  companySlug,
  showStats = true,
}: JobSearchProps) {
  const [filters, setFilters] = useState<FilterState>(() => {
    if (typeof window === 'undefined') return DEFAULT_FILTERS;
    const parsed = parseFiltersFromUrl(window.location.search);
    return { ...parsed, view: 'table' };
  });
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [prefs, setPrefs] = useState(() => loadPreferences());
  const [evidence, setEvidence] = useState<EvidenceState | null>(null);
  const [stats, setStats] = useState<SiteStats>(initialStats ?? EMPTY_STATS);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);
  const [lastGeneratedAt, setLastGeneratedAt] = useState<string | null>(null);
  const tableRef = useRef<HTMLDivElement>(null);
  const silentRef = useRef(false);

  const reload = useCallback((silent = false) => {
    silentRef.current = silent;
    setReloadToken((token) => token + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!silentRef.current) {
        setLoading(true);
      }
      setError(null);
      try {
        resetDataLoader();
        const manifest = await loadManifest();
        const allJobs = await loadAllJobs(manifest);
        if (cancelled) return;

        const scopedJobs = companySlug
          ? allJobs.filter(
              (job) =>
                job.company_name
                  .toLowerCase()
                  .replace(/[^a-z0-9]+/g, '-')
                  .replace(/^-+|-+$/g, '') === companySlug,
            )
          : allJobs;

        setJobs(scopedJobs);
        const stored = loadPreferences();
        setPrefs(stored);
        setStats(computeStats(scopedJobs, stored.lastVisit, manifest.generated_at));
        setLastGeneratedAt(manifest.generated_at);

        if (stored.originCountry && !filters.originCountry) {
          setFilters((current) => ({
            ...current,
            originCountry: stored.originCountry,
            view: 'table',
          }));
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load jobs');
        }
      } finally {
        if (!cancelled) setLoading(false);
        silentRef.current = false;
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companySlug, reloadToken]);

  useEffect(() => {
    const onFocus = () => reload(true);
    const onVisible = () => {
      if (document.visibilityState === 'visible') reload(true);
    };
    const onPageShow = (event: PageTransitionEvent) => {
      // Always re-fetch after bfcache restores or any refresh.
      if (event.persisted) reload(true);
    };
    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('pageshow', onPageShow);
    const timer = window.setInterval(() => reload(true), 20_000);
    return () => {
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('pageshow', onPageShow);
      window.clearInterval(timer);
    };
  }, [reload]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const query = serializeFiltersToUrl({ ...filters, view: 'table' });
    const base = window.location.pathname;
    window.history.replaceState(null, '', query ? `${base}${query}` : base);
  }, [filters]);

  useEffect(() => {
    if (filters.originCountry !== prefs.originCountry) {
      const next = setOriginCountry(filters.originCountry);
      setPrefs(next);
    }
  }, [filters.originCountry, prefs.originCountry]);

  useEffect(() => {
    const handleLeave = () => recordVisit();
    window.addEventListener('pagehide', handleLeave);
    return () => {
      window.removeEventListener('pagehide', handleLeave);
      handleLeave();
    };
  }, []);

  useEffect(() => {
    const node = tableRef.current;
    if (!node) return;

    const onMove = (event: MouseEvent) => {
      const rect = node.getBoundingClientRect();
      node.style.setProperty('--spot-x', `${event.clientX - rect.left}px`);
      node.style.setProperty('--spot-y', `${event.clientY - rect.top}px`);
    };

    node.addEventListener('mousemove', onMove);
    return () => node.removeEventListener('mousemove', onMove);
  }, [loading]);

  const index = useMemo(() => buildSearchIndex(jobs), [jobs]);
  const facets = useMemo(() => collectFacetValues(jobs), [jobs]);

  const filteredJobs = useMemo(
    () =>
      filterJobs(jobs, index, { ...filters, view: 'table' }, {
        savedJobIds: new Set(prefs.savedJobIds),
        dismissedJobIds: new Set(prefs.dismissedJobIds),
        lastVisit: prefs.lastVisit,
      }),
    [jobs, index, filters, prefs],
  );

  const pageJobs = useMemo(
    () => paginateJobs(filteredJobs, filters.page, filters.pageSize),
    [filteredJobs, filters.page, filters.pageSize],
  );

  const pages = totalPages(filteredJobs.length, filters.pageSize);
  const activeFilterCount = countActiveFilters(filters);

  const handleSave = useCallback((jobId: string) => {
    setPrefs(toggleSavedJob(jobId));
  }, []);

  const handleDismiss = useCallback((jobId: string) => {
    setPrefs(toggleDismissedJob(jobId));
    setExpandedId((current) => (current === jobId ? null : current));
  }, []);

  const handleEvidence = useCallback((job: Job, flag: MobilityFlag) => {
    setEvidence({ job, flag });
  }, []);

  const isNewJob = useCallback(
    (job: Job) => {
      const posted = Date.parse(postedAt(job));
      const firstSeen = Date.parse(job.first_seen_at);
      const now = Date.now();
      const hotWindow = 24 * 60 * 60 * 1000;
      if (!Number.isNaN(firstSeen) && now - firstSeen < hotWindow) return true;
      if (!Number.isNaN(posted) && now - posted < hotWindow) return true;
      if (!prefs.lastVisit) return false;
      const visit = Date.parse(prefs.lastVisit);
      return !Number.isNaN(posted) && !Number.isNaN(visit) && posted > visit;
    },
    [prefs.lastVisit],
  );

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return;
      if (pageJobs.length === 0) return;

      const currentIndex = Math.max(
        0,
        pageJobs.findIndex((job) => job.job_id === selectedId),
      );

      if (event.key === 'j' || event.key === 'ArrowDown') {
        event.preventDefault();
        const next = pageJobs[Math.min(pageJobs.length - 1, currentIndex + 1)];
        setSelectedId(next.job_id);
        document
          .querySelector<HTMLElement>(`[data-job-id="${next.job_id}"]`)
          ?.scrollIntoView({ block: 'nearest' });
      }

      if (event.key === 'k' || event.key === 'ArrowUp') {
        event.preventDefault();
        const next = pageJobs[Math.max(0, currentIndex - 1)];
        setSelectedId(next.job_id);
        document
          .querySelector<HTMLElement>(`[data-job-id="${next.job_id}"]`)
          ?.scrollIntoView({ block: 'nearest' });
      }

      if (event.key === 'Enter' && selectedId) {
        event.preventDefault();
        setExpandedId((current) => (current === selectedId ? null : selectedId));
      }

      if (event.key === 's' && selectedId) {
        event.preventDefault();
        handleSave(selectedId);
      }
    };

    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [pageJobs, selectedId, handleSave]);

  useEffect(() => {
    if (pageJobs.length === 0) {
      setSelectedId(null);
      return;
    }
    if (!selectedId || !pageJobs.some((job) => job.job_id === selectedId)) {
      setSelectedId(pageJobs[0].job_id);
    }
  }, [pageJobs, selectedId]);

  return (
    <div className="job-search">
      {showStats ? <StatsBar stats={stats} loading={loading} /> : null}

      <div className="job-search__layout">
        <div className={filtersOpen ? 'filter-shell filter-shell--open' : 'filter-shell'}>
          <FilterPanel
            filters={filters}
            disciplines={facets.disciplines}
            locations={facets.locations}
            activeCount={activeFilterCount}
            onChange={(next) => setFilters({ ...next, view: 'table' })}
            onReset={() =>
              setFilters({
                ...DEFAULT_FILTERS,
                originCountry: prefs.originCountry,
                view: 'table',
              })
            }
          />
        </div>

        <section className="job-search__results" aria-label="Job results">
          <div className="job-search__toolbar">
            <div className="job-search__toolbar-left">
              <button
                type="button"
                className="btn btn--secondary btn--sm filter-toggle"
                onClick={() => setFiltersOpen((open) => !open)}
                aria-expanded={filtersOpen}
              >
                Filters{activeFilterCount > 0 ? ` (${activeFilterCount})` : ''}
              </button>
              <p className="job-search__count" aria-live="polite">
                {loading
                  ? 'Syncing roles…'
                  : `${filteredJobs.length.toLocaleString()} role${filteredJobs.length === 1 ? '' : 's'}`}
              </p>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => reload(false)}
                title="Reload the latest published dataset"
              >
                Refresh data
              </button>
            </div>
            <div className="job-search__controls">
              <p className="job-search__hint" title="Keyboard shortcuts">
                <kbd>j</kbd>/<kbd>k</kbd> move · <kbd>Enter</kbd> expand · <kbd>s</kbd> save
                {lastGeneratedAt ? (
                  <>
                    {' '}
                    · live feed
                  </>
                ) : null}
              </p>
              <label className="job-search__sort">
                <span className="sr-only">Sort by</span>
                <select
                  value={filters.sort}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      sort: event.target.value as SortMode,
                      page: 1,
                      view: 'table',
                    }))
                  }
                >
                  <option value="diverse">Mixed companies</option>
                  <option value="newest">Newest posted</option>
                  <option value="company">Company A–Z</option>
                  <option value="title">Title A–Z</option>
                </select>
              </label>
            </div>
          </div>

          {error ? (
            <div className="alert alert--error" role="alert">
              {error}
            </div>
          ) : null}

          {!loading && filteredJobs.length === 0 ? (
            <div className="empty-state">
              <h3>No roles match</h3>
              <p>Loosen filters or check back after the next sync.</p>
            </div>
          ) : null}

          {pageJobs.length > 0 ? (
            <div ref={tableRef} className="table-wrap table-wrap--spotlight">
              <table className="job-table">
                <caption className="sr-only">Early-career job listings</caption>
                <thead>
                  <tr>
                    <th scope="col">Company</th>
                    <th scope="col">Role</th>
                    <th scope="col">Location</th>
                    <th scope="col">Workplace</th>
                    <th scope="col">Level</th>
                    <th scope="col">Mobility</th>
                    <th scope="col">Posted</th>
                    <th scope="col">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {pageJobs.map((job, index) => (
                    <JobRow
                      key={job.job_id}
                      job={job}
                      index={index}
                      saved={prefs.savedJobIds.includes(job.job_id)}
                      isNew={isNewJob(job)}
                      expanded={expandedId === job.job_id}
                      selected={selectedId === job.job_id}
                      onToggle={(jobId) =>
                        setExpandedId((current) => (current === jobId ? null : jobId))
                      }
                      onSelect={setSelectedId}
                      onSave={handleSave}
                      onDismiss={handleDismiss}
                      onEvidence={handleEvidence}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {filteredJobs.length > 0 ? (
            <nav className="pagination" aria-label="Results pagination">
              <button
                type="button"
                className="btn btn--secondary"
                disabled={filters.page <= 1}
                onClick={() =>
                  setFilters((current) => ({ ...current, page: current.page - 1, view: 'table' }))
                }
              >
                Previous
              </button>
              <span className="pagination__status">
                Page {filters.page} of {pages}
              </span>
              <button
                type="button"
                className="btn btn--secondary"
                disabled={filters.page >= pages}
                onClick={() =>
                  setFilters((current) => ({ ...current, page: current.page + 1, view: 'table' }))
                }
              >
                Next
              </button>
            </nav>
          ) : null}
        </section>
      </div>

      {filtersOpen ? (
        <button
          type="button"
          className="filter-backdrop"
          aria-label="Close filters"
          onClick={() => setFiltersOpen(false)}
        />
      ) : null}

      {evidence ? (
        <EvidenceModal
          open
          title={evidence.job.title}
          mobilityFlag={evidence.flag}
          claim={getMobilityClaims(evidence.job.mobility, evidence.flag)}
          onClose={() => setEvidence(null)}
        />
      ) : null}
    </div>
  );
}
