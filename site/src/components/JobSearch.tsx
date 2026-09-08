import { useVirtualizer } from '@tanstack/react-virtual';
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
import JobCard from './JobCard';
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
  const [filters, setFilters] = useState<FilterState>(() =>
    typeof window !== 'undefined'
      ? parseFiltersFromUrl(window.location.search)
      : DEFAULT_FILTERS,
  );
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [prefs, setPrefs] = useState(() => loadPreferences());
  const [evidence, setEvidence] = useState<EvidenceState | null>(null);
  const [stats, setStats] = useState<SiteStats>(initialStats ?? EMPTY_STATS);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
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
        setStats(
          computeStats(scopedJobs, stored.lastVisit, manifest.generated_at),
        );

        if (stored.originCountry && !filters.originCountry) {
          setFilters((current) => ({ ...current, originCountry: stored.originCountry }));
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load jobs');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companySlug]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const query = serializeFiltersToUrl(filters);
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

  const index = useMemo(() => buildSearchIndex(jobs), [jobs]);
  const facets = useMemo(() => collectFacetValues(jobs), [jobs]);

  const filteredJobs = useMemo(
    () =>
      filterJobs(jobs, index, filters, {
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

  const useVirtualization = filters.view === 'cards' && pageJobs.length > 20;
  const virtualizer = useVirtualizer({
    count: useVirtualization ? pageJobs.length : 0,
    getScrollElement: () => listRef.current,
    estimateSize: () => 200,
    overscan: 4,
    enabled: useVirtualization,
  });

  const handleSave = useCallback((jobId: string) => {
    setPrefs(toggleSavedJob(jobId));
  }, []);

  const handleDismiss = useCallback((jobId: string) => {
    setPrefs(toggleDismissedJob(jobId));
  }, []);

  const handleEvidence = useCallback((job: Job, flag: MobilityFlag) => {
    setEvidence({ job, flag });
  }, []);

  const isNewJob = useCallback(
    (job: Job) => {
      if (!prefs.lastVisit) return false;
      const seen = Date.parse(postedAt(job));
      const visit = Date.parse(prefs.lastVisit);
      return !Number.isNaN(seen) && !Number.isNaN(visit) && seen > visit;
    },
    [prefs.lastVisit],
  );

  const renderJob = (job: Job) => (
    <JobCard
      key={job.job_id}
      job={job}
      saved={prefs.savedJobIds.includes(job.job_id)}
      isNew={isNewJob(job)}
      view={filters.view}
      onSave={handleSave}
      onDismiss={handleDismiss}
      onEvidence={handleEvidence}
    />
  );

  return (
    <div className="job-search">
      {showStats ? <StatsBar stats={stats} loading={loading} /> : null}

      <div className="job-search__layout">
        <FilterPanel
          filters={filters}
          disciplines={facets.disciplines}
          locations={facets.locations}
          activeCount={activeFilterCount}
          onChange={setFilters}
          onReset={() => setFilters({ ...DEFAULT_FILTERS, originCountry: prefs.originCountry })}
        />

        <section className="job-search__results" aria-label="Job results">
          <div className="job-search__toolbar">
            <p className="job-search__count" aria-live="polite">
              {loading
                ? 'Loading roles…'
                : `${filteredJobs.length.toLocaleString()} role${filteredJobs.length === 1 ? '' : 's'}`}
            </p>
            <div className="job-search__controls">
              <label className="job-search__sort">
                <span className="sr-only">Sort by</span>
                <select
                  value={filters.sort}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      sort: event.target.value as SortMode,
                      page: 1,
                    }))
                  }
                >
                  <option value="newest">Newest posted</option>
                  <option value="company">Company A–Z</option>
                  <option value="title">Title A–Z</option>
                </select>
              </label>
              <div className="job-search__view-toggle" role="group" aria-label="View mode">
                <button
                  type="button"
                  className={filters.view === 'cards' ? 'btn btn--secondary' : 'btn btn--ghost'}
                  aria-pressed={filters.view === 'cards'}
                  onClick={() => setFilters((current) => ({ ...current, view: 'cards' }))}
                >
                  Cards
                </button>
                <button
                  type="button"
                  className={filters.view === 'table' ? 'btn btn--secondary' : 'btn btn--ghost'}
                  aria-pressed={filters.view === 'table'}
                  onClick={() => setFilters((current) => ({ ...current, view: 'table' }))}
                >
                  Table
                </button>
              </div>
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

          {filters.view === 'table' && pageJobs.length > 0 ? (
            <div className="table-wrap">
              <table className="job-table">
                <caption className="sr-only">Job listings</caption>
                <thead>
                  <tr>
                    <th scope="col">Company</th>
                    <th scope="col">Title</th>
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
                <tbody>{pageJobs.map((job) => renderJob(job))}</tbody>
              </table>
            </div>
          ) : null}

          {filters.view === 'cards' && pageJobs.length > 0 ? (
            useVirtualization ? (
              <div ref={listRef} className="job-list job-list--virtual" tabIndex={0}>
                <div
                  style={{
                    height: `${virtualizer.getTotalSize()}px`,
                    width: '100%',
                    position: 'relative',
                  }}
                >
                  {virtualizer.getVirtualItems().map((virtualRow) => {
                    const job = pageJobs[virtualRow.index];
                    return (
                      <div
                        key={job.job_id}
                        className="job-list__item"
                        style={{
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          width: '100%',
                          transform: `translateY(${virtualRow.start}px)`,
                        }}
                      >
                        {renderJob(job)}
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="job-list">{pageJobs.map((job) => renderJob(job))}</div>
            )
          ) : null}

          {filteredJobs.length > 0 ? (
            <nav className="pagination" aria-label="Results pagination">
              <button
                type="button"
                className="btn btn--secondary"
                disabled={filters.page <= 1}
                onClick={() =>
                  setFilters((current) => ({ ...current, page: current.page - 1 }))
                }
              >
                Previous
              </button>
              <span>
                Page {filters.page} of {pages}
              </span>
              <button
                type="button"
                className="btn btn--secondary"
                disabled={filters.page >= pages}
                onClick={() =>
                  setFilters((current) => ({ ...current, page: current.page + 1 }))
                }
              >
                Next
              </button>
            </nav>
          ) : null}
        </section>
      </div>

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
