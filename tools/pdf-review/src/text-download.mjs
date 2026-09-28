export const MAX_DRAFT_CHARS = 500_100;

/** Keep the chosen PDF's name, with no paths, hidden controls, or active extension. */
export function textFilename(filename) {
  let stem = typeof filename === 'string' ? filename.split(/[\\/]/u).pop() : '';
  stem = stem.normalize('NFC').replace(/\.pdf$/iu, '')
    .replace(/[\p{C}<>:"|?*]/gu, '').replace(/^[.\s]+|[.\s]+$/gu, '');
  let shortened = '';
  let bytes = 0;
  const encoder = new TextEncoder();
  for (const character of stem) {
    bytes += encoder.encode(character).length;
    if (bytes > 180) break;
    shortened += character;
  }
  stem = shortened.replace(/[.\s]+$/gu, '');
  return `${stem || 'resume'}-text.txt`;
}

export function createTextDownload(filename, text) {
  if (typeof text !== 'string' || !text.trim() || text.length > MAX_DRAFT_CHARS) {
    throw new RangeError('Text is empty or exceeds the export limit.');
  }
  return {
    filename: textFilename(filename),
    blob: new Blob([text], { type: 'text/plain;charset=utf-8' }),
  };
}
