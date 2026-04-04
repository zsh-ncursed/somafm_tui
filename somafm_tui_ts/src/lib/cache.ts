/**
 * File-based caching for SomaFM TUI
 * Ported from Python cache system
 */

import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs';
import { join } from 'path';

const CACHE_DIR = process.env.XDG_CACHE_HOME 
  ? join(process.env.XDG_CACHE_HOME, 'somafm-tui')
  : join(process.env.HOME || '/tmp', '.cache', 'somafm-tui');

const CACHE_TTL_MS = 3600 * 1000; // 1 hour

export interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

function ensureCacheDir(): void {
  if (!existsSync(CACHE_DIR)) {
    mkdirSync(CACHE_DIR, { recursive: true });
  }
}

export function getCached<T>(key: string): T | null {
  ensureCacheDir();
  const filePath = join(CACHE_DIR, `${key}.json`);
  if (!existsSync(filePath)) return null;

  try {
    const raw = readFileSync(filePath, 'utf-8');
    const entry: CacheEntry<T> = JSON.parse(raw);
    const age = Date.now() - entry.timestamp;
    if (age > CACHE_TTL_MS) return null; // Stale
    return entry.data;
  } catch {
    return null;
  }
}

export function setCached<T>(key: string, data: T): void {
  ensureCacheDir();
  const filePath = join(CACHE_DIR, `${key}.json`);
  const entry: CacheEntry<T> = { data, timestamp: Date.now() };
  writeFileSync(filePath, JSON.stringify(entry, null, 2));
}

export function clearCache(): void {
  ensureCacheDir();
  const files = require('fs').readdirSync(CACHE_DIR);
  for (const file of files) {
    require('fs').unlinkSync(join(CACHE_DIR, file));
  }
}
