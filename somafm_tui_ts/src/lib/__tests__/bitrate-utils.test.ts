import { describe, it, expect } from 'vitest';
import {
  extractBitrateFromUrl,
  extractBitrateFromPlaylistFilename,
  mapLabelToBitrateNumbers,
  getBitrateSortKey,
} from '../bitrate-utils';

describe('bitrate-utils', () => {
  describe('extractBitrateFromUrl', () => {
    it('extracts 320k from URL', () => {
      expect(extractBitrateFromUrl('https://somafm.com/bootliquor320.pls')).toBe('320k');
    });

    it('extracts 128k from 130 URL', () => {
      expect(extractBitrateFromUrl('https://somafm.com/beatblender130.pls')).toBe('128k');
    });

    it('returns default 128k when no match', () => {
      expect(extractBitrateFromUrl('https://somafm.com/stream.pls')).toBe('128k');
    });
  });

  describe('extractBitrateFromPlaylistFilename', () => {
    it('extracts bitrate from filename', () => {
      expect(extractBitrateFromPlaylistFilename('bootliquor320.pls')).toBe('320k');
    });

    it('returns null for non-matching', () => {
      expect(extractBitrateFromPlaylistFilename('stream.pls')).toBeNull();
    });
  });

  describe('mapLabelToBitrateNumbers', () => {
    it('maps 128k to filename patterns', () => {
      expect(mapLabelToBitrateNumbers('128k')).toEqual(['130', '128']);
    });

    it('maps 320k correctly', () => {
      expect(mapLabelToBitrateNumbers('320k')).toEqual(['320']);
    });
  });

  describe('getBitrateSortKey', () => {
    it('sorts mp3 before aac', () => {
      const mp3Key = getBitrateSortKey('mp3:128k');
      const aacKey = getBitrateSortKey('aac:128k');
      expect(mp3Key).toBeLessThan(aacKey);
    });

    it('sorts higher bitrates correctly', () => {
      const key320 = getBitrateSortKey('mp3:320k');
      const key128 = getBitrateSortKey('mp3:128k');
      expect(key320).toBeLessThan(key128);
    });
  });
});
