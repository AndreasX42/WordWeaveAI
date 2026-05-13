/**
 * Browser-facing word URLs: normalized slug + per-segment encoding (matches
 * Angular router.navigate segments). Dynamo PK/SK normalization remains on
 * the backend; this aligns the client slug with {@link normalizeWordForVocabLookup}.
 */

import { normalizeWordForVocabLookup } from './word-normalize';

export interface WordRouteParams {
  sourceLanguage: string;
  targetLanguage: string;
  sourcePos: string;
  sourceWord: string;
}

/** Same rules as legacy POS normalization (e.g. "neuter noun" → "noun"). */
export function normalizePOSForWordRoute(pos: string): string {
  if (!pos) return 'pending';
  const posLower = pos.toLowerCase();
  return posLower.includes('noun') ? 'noun' : posLower;
}

function decodeSegment(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment;
  }
}

/** Raw segment values for router.navigate(['/words', ...]); router encodes. */
export function wordRouteSegments(
  params: WordRouteParams
): [string, string, string, string] {
  const slug = normalizeWordForVocabLookup(
    decodeSegment(params.sourceWord || '')
  );
  return [
    params.sourceLanguage,
    params.targetLanguage,
    normalizePOSForWordRoute(params.sourcePos || ''),
    slug,
  ];
}

/** Path-only URL string with encodeURIComponent per segment (meta tags, sharing). */
export function wordShareUrlPath(params: WordRouteParams): string {
  const [a, b, c, d] = wordRouteSegments(params);
  return `/words/${encodeURIComponent(a)}/${encodeURIComponent(b)}/${encodeURIComponent(c)}/${encodeURIComponent(d)}`;
}

const DEFAULT_SITE_ORIGIN = 'https://wordweave.xyz';

export function wordCanonicalAbsoluteUrl(
  params: WordRouteParams,
  origin: string = DEFAULT_SITE_ORIGIN
): string {
  const base = origin.replace(/\/$/, '');
  return `${base}${wordShareUrlPath(params)}`;
}
