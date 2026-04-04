/**
 * TypeScript interfaces for SomaFM TUI
 */

export interface TrackMetadata {
  artist: string;
  title: string;
  duration: string;
  timestamp?: string;
}

export interface PlaylistEntry {
  format: string;
  url: string;
}

export interface Channel {
  id: string;
  title: string;
  description: string;
  streamUrl?: string;
  largeImage?: string;
  image?: string;
  playlists: PlaylistEntry[];
  listeners: number;
  bitrate: string;
  lastPlaying: string;
  isFavorite?: boolean;
  getAvailableBitrates?: () => string[];
}

export interface ChannelApiData {
  id: string;
  title: string;
  description: string;
  playlists: PlaylistEntry[];
  listeners: string;
  lastPlaying: string;
  image?: string;
  largeimage?: string;
}

export interface TrackHistoryEntry {
  artist: string;
  title: string;
  timestamp: string;
}

export interface ThemeColors {
  name: string;
  bgColor: string;
  header: string;
  selected: string;
  info: string;
  metadata: string;
  instructions: string;
  favorite: string;
  isLight: boolean;
}

export interface AppConfig {
  theme: string;
  volume: number;
  alternativeBgMode: boolean;
  dbusAllowed: boolean;
  dbusSendMetadata: boolean;
}

export interface AppState {
  channels: Channel[];
  selectedIndex: number;
  currentChannel: Channel | null;
  isPlaying: boolean;
  isPaused: boolean;
  currentMetadata: TrackMetadata | null;
  trackHistory: TrackHistoryEntry[];
  searchQuery: string;
  isSearchActive: boolean;
  isSleepTimerActive: boolean;
  sleepTimerMinutes: number;
  volume: number;
  showVolumeIndicator: boolean;
  currentTheme: string;
  isLoading: boolean;
  error: string | null;
}
