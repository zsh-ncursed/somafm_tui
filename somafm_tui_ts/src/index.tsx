#!/usr/bin/env node
/**
 * SomaFM TUI - TypeScript Terminal Player
 * Entry point with CLI argument parsing
 * Ported from Python cli.py + player.py
 */

import React from 'react';
import { render } from 'ink';
import { Command } from 'commander';
import { App } from './components/App';
import { fetchChannels } from './lib/somafm-api';
import { listThemes } from './lib/themes';
import { getFavorites, markFavorites } from './lib/favorites';

const program = new Command();

program
  .name('somafm-tui')
  .description('SomaFM Terminal Player - Written in TypeScript')
  .version('0.1.0')
  .option('--play <channel>', 'Play specific channel by ID')
  .option('--list-channels', 'List all available channels')
  .option('--search <query>', 'Search channels by name or description')
  .option('--favorites', 'Show favorite channels')
  .option('--list-themes', 'List available themes')
  .option('--sleep <minutes>', 'Set sleep timer (1-480 minutes)')
  .option('--volume <level>', 'Set volume (0-100)');

program.parse(process.argv);
const options = program.opts();

// CLI mode handlers (non-interactive)
async function runCliMode() {
  if (options.listChannels) {
    const channels = await fetchChannels();
    await markFavorites(channels);
    console.log('\n📻 SomaFM Channels:');
    console.log('─'.repeat(50));
    for (const ch of channels) {
      const fav = ch.isFavorite ? ' ♥' : '';
      console.log(`${ch.id.padEnd(25)} ${ch.title}${fav}`);
    }
    console.log(`\nTotal: ${channels.length} channels`);
    process.exit(0);
  }

  if (options.search) {
    const channels = await fetchChannels();
    const query = options.search.toLowerCase();
    const filtered = channels.filter(ch =>
      ch.title.toLowerCase().includes(query) ||
      ch.description.toLowerCase().includes(query)
    );
    if (filtered.length === 0) {
      console.log(`No channels found for query: "${options.search}"`);
    } else {
      console.log(`\nSearch results for "${options.search}":`);
      for (const ch of filtered) {
        console.log(`  ${ch.id.padEnd(25)} ${ch.title}`);
      }
    }
    process.exit(0);
  }

  if (options.favorites) {
    const favIds = await getFavorites();
    if (favIds.size === 0) {
      console.log('No favorite channels yet. Press "f" in the app to add favorites.');
    } else {
      const channels = await fetchChannels();
      const favChannels = channels.filter(ch => favIds.has(ch.id));
      console.log('\n♥ Favorite Channels:');
      for (const ch of favChannels) {
        console.log(`  ${ch.id.padEnd(25)} ${ch.title}`);
      }
    }
    process.exit(0);
  }

  if (options.listThemes) {
    const themes = listThemes();
    console.log('\n🎨 Available Themes:');
    for (const theme of themes) {
      console.log(`  ${theme}`);
    }
    console.log(`\nTotal: ${themes.length} themes`);
    process.exit(0);
  }

  if (options.play) {
    console.log(`Playing channel: ${options.play}`);
    console.log('Starting interactive mode...');
    // Fall through to interactive mode
  }
}

// Run CLI mode if options provided
if (Object.keys(options).length > 0) {
  runCliMode().catch(err => {
    console.error('Error:', err.message);
    process.exit(1);
  });
}

// Interactive mode (default)
render(<App />);
