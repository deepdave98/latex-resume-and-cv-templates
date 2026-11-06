export function formatFileSize(bytes) {
  if (!Number.isSafeInteger(bytes) || bytes < 0) return 'File size unavailable';
  // Keep the exact byte count beside the abbreviated size. 1 MB = 1,000,000 bytes.
  const label = bytes < 1_000_000 ? `${(bytes / 1_000).toFixed(1)} KB` : `${(bytes / 1_000_000).toFixed(2)} MB`;
  return `${label} (${bytes.toLocaleString('en-US')} bytes)`;
}
