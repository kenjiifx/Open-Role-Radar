import { useEffect, useRef } from 'react';
import type { EvidenceClaim } from '../lib/types';
import { MOBILITY_LABELS, type MobilityFlag } from '../lib/types';

interface EvidenceModalProps {
  open: boolean;
  title: string;
  claim: EvidenceClaim;
  mobilityFlag?: MobilityFlag;
  onClose: () => void;
}

const STATUS_LABELS: Record<EvidenceClaim['status'], string> = {
  confirmed: 'Confirmed',
  not_available: 'Not available',
  unknown: 'Unknown',
  not_applicable: 'Not applicable',
};

export default function EvidenceModal({
  open,
  title,
  claim,
  mobilityFlag,
  onClose,
}: EvidenceModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
      closeButtonRef.current?.focus();
    }
    if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  const label = mobilityFlag ? MOBILITY_LABELS[mobilityFlag] : title;

  return (
    <dialog
      ref={dialogRef}
      className="evidence-modal"
      aria-labelledby="evidence-modal-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === dialogRef.current) onClose();
      }}
    >
      <article className="evidence-modal__panel" role="document">
        <header className="evidence-modal__header">
          <h2 id="evidence-modal-title">{label}</h2>
          <button
            ref={closeButtonRef}
            type="button"
            className="btn btn--ghost"
            onClick={onClose}
            aria-label="Close evidence dialog"
          >
            ×
          </button>
        </header>
        <dl className="evidence-modal__details">
          <div>
            <dt>Status</dt>
            <dd>
              <span className={`badge badge--${claim.status}`}>
                {STATUS_LABELS[claim.status]}
              </span>
            </dd>
          </div>
          <div>
            <dt>Confidence</dt>
            <dd>{Math.round(claim.confidence * 100)}%</dd>
          </div>
          {claim.extraction_rule ? (
            <div>
              <dt>Extraction rule</dt>
              <dd>
                <code>{claim.extraction_rule}</code>
              </dd>
            </div>
          ) : null}
        </dl>
        {claim.evidence_excerpt ? (
          <blockquote className="evidence-modal__excerpt">
            <p>{claim.evidence_excerpt}</p>
          </blockquote>
        ) : (
          <p className="evidence-modal__empty">No evidence excerpt available for this claim.</p>
        )}
      </article>
    </dialog>
  );
}

interface EvidenceTooltipProps {
  claim: EvidenceClaim;
  label: string;
  children: React.ReactNode;
}

export function EvidenceTooltip({ claim, label, children }: EvidenceTooltipProps) {
  const excerpt = claim.evidence_excerpt?.slice(0, 120);
  const title = [
    `${label}: ${STATUS_LABELS[claim.status]}`,
    excerpt ? `"${excerpt}${claim.evidence_excerpt && claim.evidence_excerpt.length > 120 ? '…' : ''}"` : '',
  ]
    .filter(Boolean)
    .join(' — ');

  return (
    <span className="evidence-tooltip" title={title}>
      {children}
    </span>
  );
}
