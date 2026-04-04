/**
 * Main App component - Orchestrates all components
 * Ported from Python player.py
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Box, useApp, useInput, useStdout, Text } from 'ink';
import { ChannelList } from './ChannelList';
import { NowPlaying } from './NowPlaying';
import { StatusBar } from './StatusBar';
import { SleepTimerOverlay } from './SleepTimerOverlay';
import { SearchPrompt } from './SearchPrompt';
import { HelpOverlay } from './HelpOverlay';
import { Channel, TrackMetadata, TrackHistoryEntry, ThemeColors } from '../types';
import { AudioPlayer } from '../lib/audio-player';
import { fetchChannels } from '../lib/somafm-api';
import { getTheme, getNextTheme, getPreviousTheme, listThemes } from '../lib/themes';
import { markFavorites, toggleFavorite } from '../lib/favorites';
import { loadConfig, saveConfig } from '../lib/config';
import { extractBitrateFromUrl, getBitrateSortKey } from '../lib/bitrate-utils';

const DEFAULT_THEME: ThemeColors = {
  name: 'Default Dark',
  bgColor: '#000000',
  header: '#00ffff',
  selected: '#00ff00',
  info: '#ffff00',
  metadata: '#ff00ff',
  instructions: '#8888ff',
  favorite: '#ff0000',
  isLight: false,
};

export const App: React.FC = () => {
  const { exit } = useApp();
  const { stdout } = useStdout();

  // State
  const [channels, setChannels] = useState<Channel[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [scrollOffset, setScrollOffset] = useState(0);
  const [currentChannel, setCurrentChannel] = useState<Channel | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [metadata, setMetadata] = useState<TrackMetadata | null>(null);
  const [history, setHistory] = useState<TrackHistoryEntry[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [themeName, setThemeName] = useState('default');
  const [theme, setTheme] = useState<ThemeColors>(DEFAULT_THEME);
  const [volume, setVolume] = useState(100);
  const [sleepTimerMinutes, setSleepTimerMinutes] = useState(0);
  const [isSleepTimerActive, setIsSleepTimerActive] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Overlays
  const [showSearch, setShowSearch] = useState(false);
  const [showSleepTimer, setShowSleepTimer] = useState(false);
  const [showHelp, setShowHelp] = useState(false);

  // Player
  const [player] = useState(() => new AudioPlayer());

  // Initialize
  useEffect(() => {
    (async () => {
      try {
        // Load config
        const config = await loadConfig();
        const loadedTheme = getTheme(config.theme) || DEFAULT_THEME;
        setThemeName(config.theme);
        setTheme(loadedTheme);
        setVolume(config.volume);

        // Fetch channels
        setIsLoading(true);
        const chs = await fetchChannels();
        await markFavorites(chs);
        setChannels(chs);
        setIsLoading(false);
      } catch (err) {
        setError(`Failed to load: ${err instanceof Error ? err.message : err}`);
        setIsLoading(false);
      }
    })();

    // Start MPV
    player.start().catch(console.error);
    player.on('playing', () => {
      setIsPlaying(true);
      setIsPaused(false);
    });
    player.on('pause', (paused: boolean) => setIsPaused(paused));
    player.on('stopped', () => {
      setIsPlaying(false);
      setIsPaused(false);
      setCurrentChannel(null);
      setMetadata(null);
    });
    player.on('error', (err: any) => console.error('Player error:', err));

    return () => { player.quit(); };
  }, []);

  // Calculate visible count based on terminal height
  const visibleCount = Math.max(5, (stdout?.rows || 24) - 8);

  // Navigation
  const handleNavigate = useCallback((delta: number) => {
    setSelectedIndex(prev => {
      const filtered = channels.filter(ch =>
        ch.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        ch.description.toLowerCase().includes(searchQuery.toLowerCase())
      );
      const maxIndex = filtered.length - 1;
      const next = Math.max(0, Math.min(maxIndex, prev + delta));

      // Update scroll offset
      if (next < scrollOffset) {
        setScrollOffset(next);
      } else if (next >= scrollOffset + visibleCount) {
        setScrollOffset(next - visibleCount + 1);
      }

      return next;
    });
  }, [channels, searchQuery, scrollOffset, visibleCount]);

  // Play selected channel
  const handleSelect = useCallback(async () => {
    const filtered = channels.filter(ch =>
      ch.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ch.description.toLowerCase().includes(searchQuery.toLowerCase())
    );
    const channel = filtered[selectedIndex];
    if (!channel?.streamUrl) return;

    setCurrentChannel(channel);
    setMetadata({ artist: 'Loading...', title: 'Loading...', duration: '--:--' });
    await player.play(channel.streamUrl);
    setIsPlaying(true);
  }, [channels, selectedIndex, searchQuery, player]);

  // Global keybinds
  useInput((input, key) => {
    // Ignore keys if overlay is active
    if (showSearch || showSleepTimer || showHelp) return;

    if (input === 'q') {
      exit();
      return;
    }

    if (input === ' ') {
      player.togglePause();
      return;
    }

    if (input === 'h') {
      player.stop();
      return;
    }

    if (input === 'f' && currentChannel) {
      (async () => {
        const added = await toggleFavorite(currentChannel.id);
        setChannels(prev => prev.map(ch =>
          ch.id === currentChannel.id ? { ...ch, isFavorite: added } : ch
        ));
        setCurrentChannel(prev => prev ? { ...prev, isFavorite: added } : null);
      })();
      return;
    }

    if (input === 'r' && currentChannel) {
      // Cycle bitrate
      const availableBitrates = currentChannel.getAvailableBitrates?.() || ['mp3:128k'];
      const currentBitrate = `${currentChannel.bitrate}`;
      const currentIndex = availableBitrates.indexOf(currentBitrate);
      const nextIndex = (currentIndex + 1) % availableBitrates.length;
      const nextBitrate = availableBitrates[nextIndex];

      // Get new stream URL
      const [fmt] = nextBitrate.split(':');
      const newUrl = currentChannel.playlists.find(p => p.format === fmt)?.url;
      if (newUrl) {
        player.play(newUrl);
        setCurrentChannel(prev => prev ? { ...prev, bitrate: nextBitrate } : null);
      }
      return;
    }

    if (input === 's') {
      setShowSleepTimer(true);
      return;
    }

    if (input === 't') {
      const nextThemeName = getNextTheme(themeName);
      const nextThemeColors = getTheme(nextThemeName);
      if (nextThemeColors) {
        setThemeName(nextThemeName);
        setTheme(nextThemeColors);
        saveConfig({ theme: nextThemeName });
      }
      return;
    }

    if (input === 'y') {
      const prevThemeName = getPreviousTheme(themeName);
      const prevThemeColors = getTheme(prevThemeName);
      if (prevThemeColors) {
        setThemeName(prevThemeName);
        setTheme(prevThemeColors);
        saveConfig({ theme: prevThemeName });
      }
      return;
    }

    if (input === '/') {
      setShowSearch(true);
      return;
    }

    if (input === '?') {
      setShowHelp(true);
      return;
    }

    // Volume
    if (key.pageUp) {
      const newVolume = Math.min(100, volume + 5);
      setVolume(newVolume);
      player.setVolume(newVolume);
      saveConfig({ volume: newVolume });
      return;
    }

    if (key.pageDown) {
      const newVolume = Math.max(0, volume - 5);
      setVolume(newVolume);
      player.setVolume(newVolume);
      saveConfig({ volume: newVolume });
      return;
    }
  });

  // Sleep timer handler
  const handleSetSleepTimer = useCallback((minutes: number) => {
    setSleepTimerMinutes(minutes);
    setIsSleepTimerActive(true);
    setShowSleepTimer(false);

    // Simple timeout (in real app, would be more sophisticated)
    setTimeout(() => {
      player.stop();
      setIsSleepTimerActive(false);
      setSleepTimerMinutes(0);
    }, minutes * 60 * 1000);
  }, [player]);

  // Search handler
  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    setShowSearch(false);
    setSelectedIndex(0);
    setScrollOffset(0);
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <Box justifyContent="center" alignItems="center" height="100%">
        <Text color={theme.metadata}>Loading channels...</Text>
      </Box>
    );
  }

  // Error state
  if (error) {
    return (
      <Box flexDirection="column" justifyContent="center" alignItems="center" height="100%">
        <Text color={theme.favorite}>Error: {error}</Text>
        <Text color={theme.instructions}>Press q to quit</Text>
      </Box>
    );
  }

  return (
    <Box flexDirection="column" height="100%">
      <Box flexDirection="row" flexGrow={1}>
        <ChannelList
          channels={channels}
          selectedIndex={selectedIndex}
          searchQuery={searchQuery}
          theme={theme}
          scrollOffset={scrollOffset}
          visibleCount={visibleCount}
          onNavigate={handleNavigate}
          onSelect={handleSelect}
        />
        <NowPlaying
          channel={currentChannel}
          metadata={metadata}
          history={history}
          isPlaying={isPlaying}
          isPaused={isPaused}
          theme={theme}
        />
      </Box>
      <StatusBar
        theme={theme}
        volume={volume}
        sleepTimerMinutes={sleepTimerMinutes}
        isSleepTimerActive={isSleepTimerActive}
      />

      {/* Overlays */}
      {showSleepTimer && (
        <SleepTimerOverlay
          theme={theme}
          onSet={handleSetSleepTimer}
          onCancel={() => setShowSleepTimer(false)}
        />
      )}
      {showSearch && (
        <SearchPrompt
          theme={theme}
          onSearch={handleSearch}
          onCancel={() => {
            setShowSearch(false);
            setSearchQuery('');
          }}
        />
      )}
      {showHelp && (
        <HelpOverlay
          theme={theme}
          onClose={() => setShowHelp(false)}
        />
      )}
    </Box>
  );
};
