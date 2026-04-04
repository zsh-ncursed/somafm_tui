/**
 * Theme system for SomaFM TUI
 * Loads themes from themes.json and provides utility functions
 */

import { readFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { ThemeColors } from '../types';

const __dirname = dirname(fileURLToPath(import.meta.url));
const themesPath = join(__dirname, '..', '..', 'themes.json');

let themesCache: Record<string, ThemeColors> | null = null;

/**
 * Load all themes from themes.json
 */
export function loadThemes(): Record<string, ThemeColors> {
  if (themesCache) return themesCache;

  if (!existsSync(themesPath)) {
    console.error('themes.json not found');
    return {};
  }

  const raw = readFileSync(themesPath, 'utf-8');
  const rawThemes: Record<string, any> = JSON.parse(raw);

  themesCache = {};
  for (const [key, value] of Object.entries(rawThemes)) {
    themesCache[key] = {
      name: value.name,
      bgColor: value.bg_color,
      header: value.header,
      selected: value.selected,
      info: value.info,
      metadata: value.metadata,
      instructions: value.instructions,
      favorite: value.favorite,
      isLight: value.is_light,
    };
  }

  return themesCache;
}

/**
 * Get theme by name
 */
export function getTheme(name: string): ThemeColors | null {
  const themes = loadThemes();
  return themes[name] || null;
}

/**
 * List all theme names, sorted with dark themes first
 */
export function listThemes(): string[] {
  const themes = loadThemes();
  return Object.entries(themes)
    .sort(([, a], [, b]) => {
      if (a.isLight === b.isLight) return 0;
      return a.isLight ? 1 : -1; // Dark first
    })
    .map(([key]) => key);
}

/**
 * Get next theme in the list (for cycling)
 */
export function getNextTheme(currentTheme: string): string {
  const themes = listThemes();
  const currentIndex = themes.indexOf(currentTheme);
  const nextIndex = (currentIndex + 1) % themes.length;
  return themes[nextIndex];
}

/**
 * Get previous theme in the list (for cycling)
 */
export function getPreviousTheme(currentTheme: string): string {
  const themes = listThemes();
  const currentIndex = themes.indexOf(currentTheme);
  const prevIndex = (currentIndex - 1 + themes.length) % themes.length;
  return themes[prevIndex];
}
