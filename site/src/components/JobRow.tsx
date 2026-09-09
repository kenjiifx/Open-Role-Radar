import { useId } from 'react';
import { formatDate, formatRelative, openedFreshness, postedAt } from '../lib/dates';
import { formatDiscipline, isStartupCompany } from '../lib/labels';
import { companyUrl } from '../lib/paths';
import { cleanSummary, looksLikeReadableSummary } from '../lib/summary';
import type { Job, MobilityFlag } from '../lib/types';
import { slugifyCompany } from '../lib/types';
import {
  ACADEMIC_TERM_LABELS,
  CAREER_LEVEL_LABELS,
  formatLocation,
  getMobilityFlags,
  MOBILITY_LABELS,
  WORKPLACE_LABELS,
} from '../lib/types';
import { EvidenceTooltip } from './EvidenceModal';

interface JobRowProps {
  job: Job;
  saved: boolean;
  isNew: boolean;
  expanded: boolean;
  selected: boolean;
  index: number;
  onToggle: (jobId: string) => void;
  onSelect: (jobId: string) => void;
  onSave: (jobId: string) => void;
  onDismiss: (jobId: string) => void;
  onEvidence: (job: Job, flag: MobilityFlag) => void;
}

function companyInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
}

function MobilityBadges({
  job,
  onEvidence,
}: {
  job: Job;
  onEvidence: (job: Job, flag: MobilityFlag) => void;
}) {
  const flags = getMobilityFlags(job.mobility);
  if (flags.length === 0) return null;

  return (
    <div className="mobility-badges" role="list" aria-label="Mobility benefits">
      {flags.map((flag) => {
        const claim = job.mobility[
          flag === 'visa'
            ? 'visa_sponsorship'
            : flag === 'relocation'
              ? 'relocation_assistance'
              : flag === 'housing'
                ? 'housing_provided'
                : 'airfare'
        ];
        return (
          <EvidenceTooltip key={flag} claim={claim} label={MOBILITY_LABELS[flag]}>
            <button
              type="button"
              className={`chip chip--${flag}`}
              role="listitem"
              onClick={(event) => {
                event.stopPropagation();
                onEvidence(job, flag);
              }}
              aria-label={`View evidence for ${MOBILITY_LABELS[flag]}`}
            >
              {MOBILITY_LABELS[flag]}
            </button>
          </EvidenceTooltip>
        );
      })}
    </div>
  );
}

function formatCompensation(job: Job): string | null {
  const comp = job.compensation;
  if (!comp) return null;
  const min = comp.min_amount;
  const max = comp.max_amount;
  const currency = comp.currency || 'USD';
  if (min == null && max == null) return null;
  const period = comp.period && comp.period !== 'unknown' ? ` / ${comp.period}` : '';
  if (min != null && max != null) {
    return `${currency} ${Math.round(min).toLocaleString()}–${Math.round(max).toLocaleString()}${period}`;
  }
  const amount = min ?? max;
  return amount == null ? null : `${currency} ${Math.round(amount).toLocaleString()}${period}`;
}

export default function JobRow({
  job,
  saved,
  isNew,
  expanded,
  selected,
  index,
  onToggle,
  onSelect,
  onSave,
  onDismiss,
  onEvidence,
}: JobRowProps) {
  const detailId = useId();
  const posted = postedAt(job);
  const postedLabel = formatDate(posted);
  const postedRelative = formatRelative(posted);
  const location = formatLocation(job.locations);
  const freshness = openedFreshness(job);
  const summary = cleanSummary(job.summary);
  const hasSummary = looksLikeReadableSummary(job.summary ?? '');
  const compensation = formatCompensation(job);
  const term =
    job.academic_term && job.academic_term !== 'unknown'
      ? ACADEMIC_TERM_LABELS[job.academic_term]
      : null;
  const skills = (job.skills ?? []).slice(0, 8);
  const startup = isStartupCompany(job.company_name);

  return (
    <article
      className={[
        'job-card',
        isNew || freshness.tier === 'hot' ? 'job-card--new' : '',
        freshness.tier === 'hot' ? 'job-card--hot' : '',
        expanded ? 'job-card--expanded' : '',
        selected ? 'job-card--selected' : '',
        saved ? 'job-card--saved' : '',
      ]
        .filter(Boolean)
        .join(' ')}
      style={{ animationDelay: `${Math.min(index, 18) * 28}ms` }}
      data-job-id={job.job_id}
    >
      <div
        className="job-card__main"
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        aria-controls={detailId}
        onClick={() => {
          onSelect(job.job_id);
          onToggle(job.job_id);
        }}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            onSelect(job.job_id);
            onToggle(job.job_id);
          }
        }}
      >
        <div className="job-card__logo" aria-hidden="true">
          {companyInitials(job.company_name)}
        </div>

        <div className="job-card__body">
          <div className="job-card__top">
            <div className="job-card__identity">
              <a
                href={companyUrl(slugifyCompany(job.company_name))}
                className="job-card__company"
                onClick={(event) => event.stopPropagation()}
              >
                {job.company_name}
                {job.provenance.first_party_verified ? (
                  <span className="job-card__verified" title="First-party verified">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <circle cx="12" cy="12" r="10" fill="#3b82f6" />
                      <path
                        d="M8 12.5l2.5 2.5L16 9.5"
                        stroke="#fff"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>
                ) : null}
              </a>
              <h3 className="job-card__title">{job.title}</h3>
              <p className="job-card__location">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path
                    d="M12 21s7-5.4 7-11a7 7 0 10-14 0c0 5.6 7 11 7 11z"
                    stroke="currentColor"
                    strokeWidth="2"
                  />
                  <circle cx="12" cy="10" r="2.5" stroke="currentColor" strokeWidth="2" />
                </svg>
                {location}
              </p>
            </div>

            <div className="job-card__meta">
              <time className="job-card__time" dateTime={posted} title={postedLabel}>
                {postedRelative}
              </time>
              <div className="job-card__actions" onClick={(event) => event.stopPropagation()}>
                <a
                  href={job.apply_url}
                  className="btn btn--primary btn--sm"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Apply
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path
                      d="M7 17L17 7M17 7H9M17 7v8"
                      stroke="currentColor"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </a>
                <button
                  type="button"
                  className={saved ? 'icon-btn icon-btn--active' : 'icon-btn'}
                  onClick={() => onSave(job.job_id)}
                  aria-pressed={saved}
                  aria-label={saved ? 'Remove from saved jobs' : 'Save job'}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path
                      d="M6 4h12v17l-6-3.5L6 21V4z"
                      stroke="currentColor"
                      strokeWidth="2"
                      fill={saved ? 'currentColor' : 'none'}
                    />
                  </svg>
                </button>
                <button
                  type="button"
                  className="icon-btn"
                  onClick={() => onDismiss(job.job_id)}
                  aria-label="Dismiss job"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <circle cx="5" cy="12" r="1.6" fill="currentColor" />
                    <circle cx="12" cy="12" r="1.6" fill="currentColor" />
                    <circle cx="19" cy="12" r="1.6" fill="currentColor" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <div className="job-card__tags">
            <span className="chip chip--quiet">{WORKPLACE_LABELS[job.workplace_type]}</span>
            <span className="chip chip--level">{CAREER_LEVEL_LABELS[job.career_level]}</span>
            {term ? <span className="chip chip--season">{term}</span> : null}
            {startup ? <span className="chip chip--startup">Startup</span> : null}
            {freshness.tier === 'hot' ? (
              <span className="chip chip--hot">{freshness.label}</span>
            ) : null}
            {freshness.tier !== 'hot' && isNew ? <span className="chip chip--new">New</span> : null}
            {saved ? <span className="chip chip--saved">Saved</span> : null}
            <MobilityBadges job={job} onEvidence={onEvidence} />
          </div>
        </div>
      </div>

      <div
        className={expanded ? 'job-card__detail job-card__detail--open' : 'job-card__detail'}
        id={detailId}
      >
        <div className="job-detail__inner">
          <div className="job-detail__grid">
            <section className="job-detail__summary">
              <p className="job-detail__label">Role overview</p>
              {hasSummary ? (
                <p className="job-detail__body">{summary}</p>
              ) : (
                <div className="job-detail__empty">
                  <p>
                    Full posting text isn&apos;t in the public ATS feed for this role. Open the
                    source listing for the complete description.
                  </p>
                  <a
                    href={job.job_url}
                    className="btn btn--secondary btn--sm"
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(event) => event.stopPropagation()}
                  >
                    Read full posting
                  </a>
                </div>
              )}
            </section>
            <aside className="job-detail__aside">
              <p className="job-detail__label">Intel</p>
              <ul className="job-detail__meta">
                <li>
                  Posted <strong>{postedLabel}</strong>
                  <span className="job-detail__meta-sub">{postedRelative}</span>
                </li>
                <li>
                  First seen by radar <strong>{formatRelative(job.first_seen_at)}</strong>
                </li>
                <li>
                  Workplace <strong>{WORKPLACE_LABELS[job.workplace_type]}</strong>
                </li>
                <li>
                  Level <strong>{CAREER_LEVEL_LABELS[job.career_level]}</strong>
                </li>
                {term ? (
                  <li>
                    Season <strong>{term}</strong>
                  </li>
                ) : null}
                <li>
                  Location <strong>{location}</strong>
                </li>
                {compensation ? (
                  <li>
                    Comp <strong>{compensation}</strong>
                  </li>
                ) : null}
                {job.disciplines?.primary ? (
                  <li>
                    Discipline <strong>{formatDiscipline(job.disciplines.primary)}</strong>
                  </li>
                ) : null}
              </ul>
              {skills.length > 0 ? (
                <div className="job-detail__skills">
                  {skills.map((skill) => (
                    <span key={skill} className="chip chip--quiet">
                      {skill}
                    </span>
                  ))}
                </div>
              ) : null}
            </aside>
          </div>
          <div className="job-detail__cta">
            <a
              href={job.apply_url}
              className="btn btn--primary"
              target="_blank"
              rel="noopener noreferrer"
              onClick={(event) => event.stopPropagation()}
            >
              Open application
            </a>
            <a
              href={job.job_url}
              className="btn btn--secondary"
              target="_blank"
              rel="noopener noreferrer"
              onClick={(event) => event.stopPropagation()}
            >
              Source listing
            </a>
          </div>
        </div>
      </div>
    </article>
  );
}
