import { describe, it, expect } from 'vitest';
import { loadThemes, getTheme, listThemes, getNextTheme, getPreviousTheme } from '../themes';

describe('themes', () => {
  it('loads all 24 themes', () => {
    const themes = loadThemes();
    expect(Object.keys(themes)).toHaveLength(24);
  });

  it('returns dracula theme', () => {
    const theme = getTheme('dracula');
    expect(theme).not.toBeNull();
    expect(theme?.name).toBe('Dracula');
    expect(theme?.bgColor).toBe('#282a36');
    expect(theme?.header).toBe('#f8f8f2');
  });

  it('returns null for non-existent theme', () => {
    const theme = getTheme('non-existent');
    expect(theme).toBeNull();
  });

  it('lists themes sorted by dark first', () => {
    const themes = listThemes();
    // First themes should be dark
    expect(themes.length).toBe(24);
    const firstTheme = themes[0];
    const loadedThemes = loadThemes();
    expect(loadedThemes[firstTheme]?.isLight).toBe(false);
  });

  it('cycles to next theme', () => {
    const themes = listThemes();
    const next = getNextTheme(themes[0]);
    expect(next).toBe(themes[1]);
  });

  it('cycles to previous theme', () => {
    const themes = listThemes();
    const prev = getPreviousTheme(themes[0]);
    expect(prev).toBe(themes[themes.length - 1]);
  });

  it('wraps around when cycling last theme', () => {
    const themes = listThemes();
    const next = getNextTheme(themes[themes.length - 1]);
    expect(next).toBe(themes[0]);
  });
});
