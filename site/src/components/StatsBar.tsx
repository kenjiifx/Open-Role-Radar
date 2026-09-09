import { useEffect, useState } from 'react';
import { formatRelative, formatUpdatedLabel } from '../lib/dates';
import type { SiteStats } from '../lib/types';

interface StatsBarProps {
  stats: SiteStats;
  loading?: boolean;
}

function useCountUp(target: number, enabled: boolean) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!enabled) {
      setValue(0);
      return;
    }
    let frame = 0;
    const start = performance.now();
    const duration = 700;

    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - (1 - progress) ** 3;
      setValue(Math.round(target * eased));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, enabled]);

  return value;
}

export default function StatsBar({ stats, loading }: StatsBarProps) {
  const roles = useCountUp(stats.totalJobs, !loading);
  const companies = useCountUp(stats.totalCompanies, !loading);
  const visa = useCountUp(stats.withVisa, !loading);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 15_000);
    return () => window.clearInterval(timer);
  }, []);

  const relative = loading
    ? 'Refreshing…'
    : formatRelative(stats.generatedAt, now) || formatUpdatedLabel(stats.generatedAt, now);
  const syncClock = loading
    ? '—'
    : new Date(stats.generatedAt).toLocaleTimeString([], {
        hour: 'numeric',
        minute: '2-digit',
      });

  return (
    <section className="stats-bar" aria-label="Live dataset summary" aria-busy={loading}>
      <div className="stats-bar__item">
        <span className="stats-bar__icon" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M4 8l8-4 8 4v8l-8 4-8-4V8z" stroke="currentColor" strokeWidth="1.8" />
            <path d="M4 8l8 4 8-4M12 12v8" stroke="currentColor" strokeWidth="1.8" />
          </svg>
        </span>
        <div>
          <strong className="stat__value">{loading ? '—' : roles.toLocaleString()}</strong>
          <span className="stat__label">Open roles</span>
        </div>
      </div>
      <div className="stats-bar__item">
        <span className="stats-bar__icon" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path
              d="M4 20V9l8-4 8 4v11M9 20v-6h6v6"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        <div>
          <strong className="stat__value">{loading ? '—' : companies.toLocaleString()}</strong>
          <span className="stat__label">Companies</span>
        </div>
      </div>
      <div className="stats-bar__item">
        <span className="stats-bar__icon" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path
              d="M3 12h3l2-5 3 10 2-5h8"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        <div>
          <strong className="stat__value">{loading ? '—' : visa.toLocaleString()}</strong>
          <span className="stat__label">Visa signals</span>
        </div>
      </div>
      <div className="stats-bar__live">
        <span className="stats-bar__pulse" aria-hidden="true" />
        <div>
          <strong className="stat__value stat__value--text">
            Live · Updated {relative}
          </strong>
          <span className="stat__label">
            <time dateTime={stats.generatedAt}>Last sync {syncClock}</time>
          </span>
        </div>
      </div>
      {!loading && stats.newSinceVisit > 0 ? (
        <p className="stats-bar__new">{stats.newSinceVisit} new since your last visit</p>
      ) : null}
    </section>
  );
}
