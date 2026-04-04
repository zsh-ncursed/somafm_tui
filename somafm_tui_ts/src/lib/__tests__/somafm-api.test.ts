import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock cache module
vi.mock('../cache', () => ({
  getCached: vi.fn(),
  setCached: vi.fn(),
}));

import * as cache from '../cache';

describe('somafm-api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchChannels', () => {
    it('returns cached channels when available', async () => {
      const mockChannels = [
        { 
          id: 'test', 
          title: 'Test', 
          playlists: [], 
          description: '', 
          listeners: 0, 
          bitrate: '128k', 
          lastPlaying: '' 
        }
      ];
      vi.mocked(cache.getCached).mockReturnValue(mockChannels as any);

      const { fetchChannels } = await import('../somafm-api');
      const result = await fetchChannels(true);
      
      expect(result).toEqual(mockChannels);
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('fetches from API when cache is empty', async () => {
      vi.mocked(cache.getCached).mockReturnValue(null);

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ channels: [] }),
      });

      const { fetchChannels } = await import('../somafm-api');
      await fetchChannels(true);
      
      expect(mockFetch).toHaveBeenCalledWith('https://api.somafm.com/channels.json');
    });

    it('falls back to stale cache on network error', async () => {
      const staleChannels = [
        { 
          id: 'stale', 
          title: 'Stale', 
          playlists: [], 
          description: '', 
          listeners: 0, 
          bitrate: '128k', 
          lastPlaying: '' 
        }
      ];
      
      vi.mocked(cache.getCached)
        .mockReturnValueOnce(null) // First call: no fresh cache
        .mockReturnValue(staleChannels as any); // Second call: stale cache

      mockFetch.mockRejectedValue(new Error('Network error'));

      const { fetchChannels } = await import('../somafm-api');
      const result = await fetchChannels(true);
      
      expect(result).toEqual(staleChannels);
    });
  });
});
