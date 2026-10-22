export function checkTextLimit(text, value = '') {
  if (typeof text !== 'string') throw new TypeError('Expected a text copy.');
  // Match HTML text fields: count UTF-16 code units, including whitespace.
  const count = text.length;
  const input = String(value ?? '').trim();
  if (!input) return { count, status: 'unset' };
  const limit = Number(input);
  if (input.length > 32 || !/^\d+$/u.test(input) || !Number.isSafeInteger(limit) || limit < 1) {
    return { count, status: 'invalid' };
  }
  return { count, limit, status: count > limit ? 'over' : 'within' };
}
