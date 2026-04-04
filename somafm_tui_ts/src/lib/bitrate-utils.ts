/**
 * Bitrate utility functions for SomaFM TUI
 *
 * Ported from Python bitrate_utils.py
 */

export const LABEL_TO_BITRATE_NUMS: Record<string, string[]> = {
  '320k': ['320'],
  '128k': ['130', '128'],
  '64k': ['64'],
  '96k': ['96'],
  '160k': ['160'],
  '256k': ['256'],
};

export const FORMAT_PRIORITY: Record<string, number> = {
  mp3: 0,
  aac: 1,
  aacp: 2,
};

export const BITRATE_ORDER = ['320k', '256k', '160k', '128k', '64k', '96k'];

/**
 * Extract bitrate label from stream URL
 * Example: https://somafm.com/bootliquor320.pls -> '320k'
 */
export function extractBitrateFromUrl(url: string): string {
  const match = url.match(/(\d{2,3})\.pls/);
  if (match) {
    const num = match[1];
    for (const [label, nums] of Object.entries(LABEL_TO_BITRATE_NUMS)) {
      if (nums.includes(num)) return label;
    }
    return `${num}k`;
  }
  return '128k';
}

/**
 * Extract bitrate from playlist filename
 * Example: bootliquor320.pls -> '320k'
 */
export function extractBitrateFromPlaylistFilename(url: string): string | null {
  const match = url.match(/(\d{2,3})\.pls$/);
  if (match) return `${match[1]}k`;
  return null;
}

/**
 * Map bitrate label back to filename patterns
 * Example: '128k' -> ['130', '128']
 */
export function mapLabelToBitrateNumbers(label: string): string[] {
  return LABEL_TO_BITRATE_NUMS[label] || [];
}

/**
 * Get sort key for bitrate string (format:bitrate)
 * Lower values = higher priority
 */
export function getBitrateSortKey(bitrate: string): number {
  const [fmt, label] = bitrate.split(':');
  const formatPriority = FORMAT_PRIORITY[fmt] ?? 99;
  const bitrateIndex = BITRATE_ORDER.indexOf(label);
  const bitratePriority = bitrateIndex >= 0 ? bitrateIndex : 99;
  return formatPriority * 1000 + bitratePriority;
}
