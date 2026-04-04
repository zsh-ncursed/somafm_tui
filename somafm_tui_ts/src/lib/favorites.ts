/**
 * Favorites management using lowdb for JSON persistence
 * Ported from Python channels.py favorites system
 */

import { JSONFilePreset } from 'lowdb/node';
import { Channel } from '../types';
import { join } from 'path';

export interface FavoritesData {
  channelIds: string[];
}

function getFavoritesPath(): string {
  const configDir = process.env.XDG_CONFIG_HOME 
    ? join(process.env.XDG_CONFIG_HOME, 'somafm-tui')
    : join(process.env.HOME || '/tmp', '.config', 'somafm-tui');
  return join(configDir, 'favorites.json');
}

/**
 * Get set of favorite channel IDs
 */
export async function getFavorites(): Promise<Set<string>> {
  const defaultData: FavoritesData = { channelIds: [] };
  const db = await JSONFilePreset<FavoritesData>(getFavoritesPath(), defaultData);
  return new Set(db.data.channelIds);
}

/**
 * Toggle channel favorite status
 * @returns true if added, false if removed
 */
export async function toggleFavorite(channelId: string): Promise<boolean> {
  const defaultData: FavoritesData = { channelIds: [] };
  const db = await JSONFilePreset<FavoritesData>(getFavoritesPath(), defaultData);

  const index = db.data.channelIds.indexOf(channelId);
  if (index >= 0) {
    db.data.channelIds.splice(index, 1);
    await db.write();
    return false; // Removed
  } else {
    db.data.channelIds.push(channelId);
    await db.write();
    return true; // Added
  }
}

/**
 * Mark channels with favorite status
 */
export async function markFavorites(channels: Channel[]): Promise<void> {
  const favorites = await getFavorites();
  for (const channel of channels) {
    channel.isFavorite = favorites.has(channel.id);
  }
}

/**
 * Check if channel is favorite
 */
export async function isFavorite(channelId: string): Promise<boolean> {
  const favorites = await getFavorites();
  return favorites.has(channelId);
}
