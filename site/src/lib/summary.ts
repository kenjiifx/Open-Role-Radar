/** Decode HTML entities and strip leftover tags from job summaries. */

const BLOCK_BREAK = /<\/(?:p|div|li|h[1-6]|tr|section|article)|<br\s*\/?>/gi;
const TAGS = /<[^>]+>/g;

function decodeEntities(value: string): string {
  if (typeof document === 'undefined') {
    return value
      .replace(/&nbsp;/gi, ' ')
      .replace(/&amp;/gi, '&')
      .replace(/&lt;/gi, '<')
      .replace(/&gt;/gi, '>')
      .replace(/&quot;/gi, '"')
      .replace(/&#39;/g, "'")
      .replace(/&#x27;/gi, "'");
  }
  let current = value;
  const textarea = document.createElement('textarea');
  for (let i = 0; i < 4; i += 1) {
    textarea.innerHTML = current;
    const decoded = textarea.value;
    if (decoded === current) break;
    current = decoded;
  }
  return current;
}

export function cleanSummary(raw: string | null | undefined): string {
  if (!raw) return '';
  let text = decodeEntities(raw.trim());
  text = text.replace(BLOCK_BREAK, '\n');
  text = text.replace(TAGS, ' ');
  if (text.includes('<') && text.includes('>')) {
    text = decodeEntities(text);
    text = text.replace(BLOCK_BREAK, '\n');
    text = text.replace(TAGS, ' ');
  }
  text = text
    .replace(/[^\S\n]+/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .join('\n');

  // If it still looks like markup soup, treat as empty.
  const tagRatio = (text.match(/[<>&]/g) ?? []).length / Math.max(text.length, 1);
  if (tagRatio > 0.08) return '';
  return text.trim();
}

export function looksLikeReadableSummary(text: string): boolean {
  const cleaned = cleanSummary(text);
  return cleaned.length >= 40;
}
