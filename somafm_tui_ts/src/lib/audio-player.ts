/**
 * MPV Audio Player wrapper using node-mpv
 * Ported from Python core/playback.py
 */

import NodeMPV from 'node-mpv';
import { EventEmitter } from 'events';

interface MPVStatus {
  pause?: boolean;
}

export interface PlaybackState {
  isPlaying: boolean;
  isPaused: boolean;
  volume: number;
}

export class AudioPlayer extends EventEmitter {
  private mpv: NodeMPV;
  private state: PlaybackState = {
    isPlaying: false,
    isPaused: false,
    volume: 100,
  };

  constructor() {
    super();
    this.mpv = new NodeMPV({
      audio_only: true,
      input_default_bindings: false,
      terminal: false,
    });

    this.setupEventListeners();
  }

  private setupEventListeners(): void {
    this.mpv.on('quit', () => {
      this.state.isPlaying = false;
      this.state.isPaused = false;
      this.emit('stopped');
    });

    this.mpv.on('crash', () => {
      this.state.isPlaying = false;
      this.emit('error', 'MPV crashed');
    });

    this.mpv.on('status', (status: MPVStatus) => {
      if (status.pause !== undefined) {
        this.state.isPaused = status.pause;
        this.emit('paused', status.pause);
      }
    });

    this.mpv.on('stopped', () => {
      this.state.isPlaying = false;
      this.state.isPaused = false;
      this.emit('stopped');
    });
  }

  /**
   * Start MPV instance
   */
  async start(): Promise<void> {
    try {
      await this.mpv.start();
    } catch (error) {
      throw new Error(`Failed to start MPV: ${error instanceof Error ? error.message : error}`);
    }
  }

  /**
   * Play a stream URL
   */
  async play(url: string): Promise<void> {
    try {
      await this.mpv.loadfile(url);
      this.state.isPlaying = true;
      this.state.isPaused = false;
      this.emit('playing', url);
    } catch (error) {
      this.emit('error', error);
    }
  }

  /**
   * Toggle pause
   */
  async togglePause(): Promise<void> {
    try {
      await this.mpv.pause();
      this.state.isPaused = !this.state.isPaused;
      this.emit('pause', this.state.isPaused);
    } catch (error) {
      this.emit('error', error);
    }
  }

  /**
   * Stop playback
   */
  async stop(): Promise<void> {
    try {
      await this.mpv.stop();
      this.state.isPlaying = false;
      this.state.isPaused = false;
      this.emit('stopped');
    } catch (error) {
      this.emit('error', error);
    }
  }

  /**
   * Set volume (0-100)
   */
  async setVolume(volume: number): Promise<void> {
    try {
      await this.mpv.volume(Math.max(0, Math.min(100, volume)));
      this.state.volume = volume;
      this.emit('volume', volume);
    } catch (error) {
      this.emit('error', error);
    }
  }

  /**
   * Get current playback state
   */
  getState(): PlaybackState {
    return { ...this.state };
  }

  /**
   * Quit MPV and cleanup
   */
  async quit(): Promise<void> {
    try {
      await this.mpv.quit();
    } catch {
      // Ignore errors during quit
    }
  }
}
