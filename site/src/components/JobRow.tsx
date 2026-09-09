import { useId } from 'react';
import { formatDate, formatRelative, openedFreshness, postedAt } from '../lib/dates';
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

function MobilityBadges({
  job,
  onEvidence,
}: {
  job: Job;
  onEvidence: (job: Job, flag: MobilityFlag) => void;
}) {
  const flags = getMobilityFlags(job.mobility);
  if (flags.length === 0) {
    return <span className="text-muted mobility-empty">—</span>;
  }

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

  return (
    <>
      <tr
        className={[
          'job-row',
          isNew || freshness.tier === 'hot' ? 'job-row--new' : '',
          freshness.tier === 'hot' ? 'job-row--hot' : '',
          expanded ? 'job-row--expanded' : '',
          selected ? 'job-row--selected' : '',
          saved ? 'job-row--saved' : '',
        ]
          .filter(Boolean)
          .join(' ')}
        style={{ animationDelay: `${Math.min(index, 18) * 28}ms` }}
        data-job-id={job.job_id}
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
        <td className="job-row__company">
          <a
            href={companyUrl(slugifyCompany(job.company_name))}
            className="link"
            onClick={(event) => event.stopPropagation()}
          >
            {job.company_name}
          </a>
        </td>
        <td className="job-row__title">
          <div className="job-row__title-line">
            <strong>{job.title}</strong>
            {freshness.tier === 'hot' ? (
              <span className="chip chip--hot">{freshness.label}</span>
            ) : null}
            {freshness.tier !== 'hot' && isNew ? <span className="chip chip--new">New</span> : null}
            {saved ? <span className="chip chip--saved">Saved</span> : null}
          </div>
        </td>
        <td className="job-row__location">{location}</td>
        <td>
          <span className="chip chip--quiet">{WORKPLACE_LABELS[job.workplace_type]}</span>
        </td>
        <td>
          <span className="chip chip--level">{CAREER_LEVEL_LABELS[job.career_level]}</span>
        </td>
        <td onClick={(event) => event.stopPropagation()}>
          <MobilityBadges job={job} onEvidence={onEvidence} />
        </td>
        <td className="job-row__posted">
          <time dateTime={posted} title={postedLabel}>
            {postedRelative}
          </time>
        </td>
        <td className="job-row__actions" onClick={(event) => event.stopPropagation()}>
          <a
            href={job.apply_url}
            className="btn btn--primary btn--sm"
            target="_blank"
            rel="noopener noreferrer"
          >
            Apply
          </a>
          <button
            type="button"
            className={saved ? 'btn btn--secondary btn--sm' : 'btn btn--ghost btn--sm'}
            onClick={() => onSave(job.job_id)}
            aria-pressed={saved}
            aria-label={saved ? 'Remove from saved jobs' : 'Save job'}
          >
            {saved ? 'Saved' : 'Save'}
          </button>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => onDismiss(job.job_id)}
            aria-label="Dismiss job"
          >
            Dismiss
          </button>
        </td>
      </tr>
      <tr className={expanded ? 'job-detail job-detail--open' : 'job-detail'} id={detailId}>
        <td colSpan={8}>
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
                    First seen by radar{' '}
                    <strong>{formatRelative(job.first_seen_at)}</strong>
                  </li>
                  <li>
                    Workplace <strong>{WORKPLACE_LABELS[job.workplace_type]}</strong>
                  </li>
                  <li>
                    Level <strong>{CAREER_LEVEL_LABELS[job.career_level]}</strong>
                  </li>
                  {term ? (
                    <li>
                      Term <strong>{term}</strong>
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
                      Discipline <strong>{job.disciplines.primary}</strong>
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
        </td>
      </tr>
    </>
  );
}
