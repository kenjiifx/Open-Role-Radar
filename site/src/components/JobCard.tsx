import { formatDate, formatRelative, postedAt } from '../lib/dates';
import { companyUrl } from '../lib/paths';
import type { Job, MobilityFlag } from '../lib/types';
import { slugifyCompany } from '../lib/types';
import {
  CAREER_LEVEL_LABELS,
  formatLocation,
  getMobilityFlags,
  isFirstPartyVerified,
  MOBILITY_LABELS,
  WORKPLACE_LABELS,
} from '../lib/types';
import { EvidenceTooltip } from './EvidenceModal';

interface JobCardProps {
  job: Job;
  saved: boolean;
  isNew: boolean;
  view: 'cards' | 'table';
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
              className={`badge badge--mobility badge--${flag}`}
              role="listitem"
              onClick={() => onEvidence(job, flag)}
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

export default function JobCard({
  job,
  saved,
  isNew,
  view,
  onSave,
  onDismiss,
  onEvidence,
}: JobCardProps) {
  const firstParty = isFirstPartyVerified(job);
  const applyLabel = firstParty ? 'Apply' : 'Apply';
  const posted = postedAt(job);
  const postedLabel = formatDate(posted);
  const postedRelative = formatRelative(posted);

  if (view === 'table') {
    return (
      <tr className={isNew ? 'job-row job-row--new' : 'job-row'}>
        <td>
          <a href={companyUrl(slugifyCompany(job.company_name))} className="link">
            {job.company_name}
          </a>
        </td>
        <td>
          <strong>{job.title}</strong>
          {isNew ? <span className="badge badge--new">New</span> : null}
        </td>
        <td>{formatLocation(job.locations)}</td>
        <td>{WORKPLACE_LABELS[job.workplace_type]}</td>
        <td>{CAREER_LEVEL_LABELS[job.career_level]}</td>
        <td>
          <MobilityBadges job={job} onEvidence={onEvidence} />
        </td>
        <td>
          <time dateTime={posted} title={postedLabel}>
            {postedRelative}
          </time>
        </td>
        <td className="job-row__actions">
          <a
            href={job.apply_url}
            className="btn btn--primary btn--sm"
            target="_blank"
            rel="noopener noreferrer"
          >
            {applyLabel}
          </a>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
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
    );
  }

  return (
    <article className={isNew ? 'job-card job-card--new' : 'job-card'} aria-labelledby={`job-${job.job_id}`}>
      <header className="job-card__header">
        <div className="job-card__identity">
          <p className="job-card__company">
            <a href={companyUrl(slugifyCompany(job.company_name))} className="link">
              {job.company_name}
            </a>
          </p>
          <h3 id={`job-${job.job_id}`} className="job-card__title">
            {job.title}
            {isNew ? <span className="badge badge--new">New</span> : null}
          </h3>
        </div>
        <time dateTime={posted} className="job-card__date" title={postedLabel}>
          <span className="job-card__date-label">Posted</span>
          <span className="job-card__date-value">{postedRelative}</span>
        </time>
      </header>

      <div className="job-card__meta">
        <span className="badge badge--level">{CAREER_LEVEL_LABELS[job.career_level]}</span>
        <span className="badge">{WORKPLACE_LABELS[job.workplace_type]}</span>
        <span className="job-card__location">{formatLocation(job.locations)}</span>
      </div>

      {job.summary ? <p className="job-card__summary">{job.summary}</p> : null}
      <MobilityBadges job={job} onEvidence={onEvidence} />

      <footer className="job-card__footer">
        <div className="job-card__actions">
          <a
            href={job.apply_url}
            className="btn btn--primary"
            target="_blank"
            rel="noopener noreferrer"
          >
            {applyLabel}
          </a>
          <button
            type="button"
            className="btn btn--secondary"
            onClick={() => onSave(job.job_id)}
            aria-pressed={saved}
          >
            {saved ? 'Saved' : 'Save'}
          </button>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => onDismiss(job.job_id)}
          >
            Dismiss
          </button>
        </div>
      </footer>
    </article>
  );
}
