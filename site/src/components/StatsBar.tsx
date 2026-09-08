import { formatUpdatedLabel } from '../lib/dates';
import type { SiteStats } from '../lib/types';

interface StatsBarProps {
  stats: SiteStats;
  loading?: boolean;
}

export default function StatsBar({ stats, loading }: StatsBarProps) {
  const updated = formatUpdatedLabel(stats.generatedAt);

  return (
    <section className="stats-bar" aria-label="Live dataset summary" aria-busy={loading}>
      <div className="stats-bar__pulse" aria-hidden="true" />
      <p className="stats-bar__line">
        <strong>{loading ? '…' : stats.totalJobs.toLocaleString()}</strong> open roles
        <span className="stats-bar__sep" aria-hidden="true">
          ·
        </span>
        <strong>{loading ? '…' : stats.totalCompanies.toLocaleString()}</strong> companies
        <span className="stats-bar__sep" aria-hidden="true">
          ·
        </span>
        <strong>{loading ? '…' : stats.withVisa.toLocaleString()}</strong> with visa signal
        <span className="stats-bar__sep" aria-hidden="true">
          ·
        </span>
        <time dateTime={stats.generatedAt}>{loading ? 'Refreshing…' : updated}</time>
      </p>
      {!loading && stats.newSinceVisit > 0 ? (
        <p className="stats-bar__new">{stats.newSinceVisit} new since your last visit</p>
      ) : null}
    </section>
  );
}
