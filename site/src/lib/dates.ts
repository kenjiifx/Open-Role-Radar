import type { Job } from './types';

/** Prefer the ATS posting date; fall back to when we first crawled it. */
export function postedAt(job: Pick<Job, 'source_posted_at' | 'first_seen_at'>): string {
  return job.source_posted_at || job.first_seen_at;
}

export function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function formatRelative(iso: string, now = Date.now()): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const deltaMs = now - date.getTime();
  const abs = Math.abs(deltaMs);
  const minutes = Math.round(abs / 60_000);
  const hours = Math.round(abs / 3_600_000);
  const days = Math.round(abs / 86_400_000);

  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 48) return `${hours}h ago`;
  if (days < 30) return `${days}d ago`;
  return formatDate(iso);
}

export function formatUpdatedLabel(iso: string, now = Date.now()): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  const relative = formatRelative(iso, now);
  if (relative === 'just now' || relative.endsWith('m ago') || relative.endsWith('h ago')) {
    return `Updated ${relative}`;
  }
  return `Updated ${formatDate(iso)}`;
}
