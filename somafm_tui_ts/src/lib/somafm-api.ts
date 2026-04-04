/**
 * SomaFM API client with caching
 * Ported from Python channels.py
 */

import { Channel, ChannelApiData } from '../types';
import { getCached, setCached } from './cache';
import { extractBitrateFromUrl } from './bitrate-utils';

const SOMAFM_API_URL = 'https://api.somafm.com/channels.json';

/**
 * Parse channel from API response
 */
function parseChannel(data: ChannelApiData): Channel {
  let streamUrl: string | undefined;
  let bitrate = '128k';

  for (const playlist of data.playlists) {
    if (playlist.format === 'mp3') {
      streamUrl = playlist.url;
      bitrate = extractBitrateFromUrl(playlist.url);
      break;
    }
  }

  return {
    id: data.id,
    title: data.title,
    description: data.description,
    streamUrl,
    largeImage: data.largeimage,
    image: data.image,
    playlists: data.playlists,
    listeners: parseInt(data.listeners, 10) || 0,
    bitrate,
    lastPlaying: data.lastPlaying,
    isFavorite: false,
  };
}

/**
 * Fetch all channels from SomaFM API
 * @param useCache - Whether to use cached data if available
 */
export async function fetchChannels(useCache: boolean = true): Promise<Channel[]> {
  if (useCache) {
    const cached = getCached<Channel[]>('channels');
    if (cached) return cached;
  }

  try {
    const response = await fetch(SOMAFM_API_URL);
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);

    const data = await response.json();
    const channels: Channel[] = (data.channels || []).map(parseChannel);

    setCached('channels', channels);
    return channels;
  } catch (error) {
    // Fallback to stale cache
    const stale = getCached<Channel[]>('channels');
    if (stale) return stale;
    throw new Error(`Failed to fetch channels: ${error instanceof Error ? error.message : error}`);
  }
}

/**
 * Get single channel by ID
 */
export async function getChannelById(id: string): Promise<Channel | null> {
  const channels = await fetchChannels();
  return channels.find(ch => ch.id === id) || null;
}
