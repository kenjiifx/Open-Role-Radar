import type { SiteStats } from '../lib/types';

interface StatsBarProps {
  stats: SiteStats;
  loading?: boolean;
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="stat-card">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

export default function StatsBar({ stats, loading }: StatsBarProps) {
  const generated = new Date(stats.generatedAt);
  const generatedLabel = Number.isNaN(generated.getTime())
    ? '—'
    : generated.toLocaleString(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short',
      });

  return (
    <section className="stats-bar" aria-label="Platform statistics" aria-busy={loading}>
      <h2 className="sr-only">Statistics</h2>
      <dl className="stats-bar__grid">
        <StatCard label="Open roles" value={loading ? '…' : stats.totalJobs.toLocaleString()} />
        <StatCard
          label="Companies"
          value={loading ? '…' : stats.totalCompanies.toLocaleString()}
        />
        <StatCard
          label="Visa sponsorship"
          value={loading ? '…' : stats.withVisa.toLocaleString()}
        />
        <StatCard
          label="Relocation support"
          value={loading ? '…' : stats.withRelocation.toLocaleString()}
        />
        <StatCard label="Remote roles" value={loading ? '…' : stats.remoteCount.toLocaleString()} />
        <StatCard
          label="New since visit"
          value={loading ? '…' : stats.newSinceVisit.toLocaleString()}
        />
      </dl>
      <p className="stats-bar__updated">
        Data updated: <time dateTime={stats.generatedAt}>{generatedLabel}</time>
      </p>
    </section>
  );
}
