export function normalizeWordForVocabLookup(input: string): string {
  if (!input) {
    return '';
  }
  let s = input.toLowerCase();
  try {
    s = s.normalize('NFKC');
  } catch {
    // ignore
  }
  // German ASCII transliteration before stripping non-letters (ß is not [a-z])
  s = s
    .replace(/ß/g, 'ss')
    .replace(/ä/g, 'ae')
    .replace(/ö/g, 'oe')
    .replace(/ü/g, 'ue');
  try {
    s = s.normalize('NFD');
  } catch {
    // ignore
  }
  // Strip all Unicode non-spacing marks (Mn), aligned with Go unicode.IsMark
  s = s.replace(/\p{Mn}/gu, '');
  s = s.replace(/[^a-z0-9]/g, '');
  return s;
}
