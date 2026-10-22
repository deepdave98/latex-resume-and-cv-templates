const POINTS_PER_MM = 72 / 25.4;
const FORMATS = [
  { name: 'A4', short: 210 * POINTS_PER_MM, long: 297 * POINTS_PER_MM, unit: 'mm' },
  { name: 'US Letter', short: 612, long: 792, unit: 'in' },
  { name: 'US Legal', short: 612, long: 1008, unit: 'in' },
];

// Dimensions come from PDF.js getViewport({ scale: 1 }), which already applies
// the visible crop box, page rotation, and the PDF's UserUnit scaling.
export function formatPageSize(width, height) {
  if (![width, height].every(value => typeof value === 'number' && Number.isFinite(value) && value > 0)) {
    return 'Page size unavailable';
  }
  const short = Math.min(width, height);
  const long = Math.max(width, height);
  // One point allows for rounded page boxes without treating different sizes
  // as the same format. Match before rounding the displayed dimensions.
  const format = FORMATS.find(item => Math.abs(short - item.short) <= 1 && Math.abs(long - item.long) <= 1);
  const unit = format?.unit ?? 'mm';
  const dimension = points => unit === 'in'
    ? String(Number((points / 72).toFixed(2)))
    : String(Number((points / POINTS_PER_MM).toFixed(1)));
  const orientation = width === height ? 'Square' : width > height ? 'Landscape' : 'Portrait';
  return `${format?.name ?? 'Custom size'} · ${dimension(width)} × ${dimension(height)} ${unit} · ${orientation}`;
}
