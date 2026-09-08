import { useEffect, useState } from 'react';
import { formatUpdatedLabel } from '../lib/dates';
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
    const from = 0;
    const duration = 700;

    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - (1 - progress) ** 3;
      setValue(Math.round(from + (target - from) * eased));
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
  const updated = formatUpdatedLabel(stats.generatedAt);

  return (
    <section className="stats-bar" aria-label="Live dataset summary" aria-busy={loading}>
      <div className="stats-bar__scan" aria-hidden="true" />
      <div className="stats-bar__grid">
        <div className="stat">
          <span className="stat__label">Open roles</span>
          <strong className="stat__value">{loading ? '—' : roles.toLocaleString()}</strong>
        </div>
        <div className="stat">
          <span className="stat__label">Companies</span>
          <strong className="stat__value">{loading ? '—' : companies.toLocaleString()}</strong>
        </div>
        <div className="stat">
          <span className="stat__label">Visa signals</span>
          <strong className="stat__value">{loading ? '—' : visa.toLocaleString()}</strong>
        </div>
        <div className="stat">
          <span className="stat__label">Feed</span>
          <strong className="stat__value stat__value--text">
            <time dateTime={stats.generatedAt}>{loading ? 'Refreshing…' : updated}</time>
          </strong>
        </div>
      </div>
      {!loading && stats.newSinceVisit > 0 ? (
        <p className="stats-bar__new">{stats.newSinceVisit} new since your last visit</p>
      ) : null}
    </section>
  );
}
