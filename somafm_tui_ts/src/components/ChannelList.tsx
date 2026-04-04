/**
 * Channel List component - Left panel
 * Ported from Python ui.py channel panel
 */

import React from 'react';
import { Box, Text, useInput } from 'ink';
import { Channel, ThemeColors } from '../types';

interface Props {
  channels: Channel[];
  selectedIndex: number;
  searchQuery: string;
  theme: ThemeColors;
  scrollOffset: number;
  visibleCount: number;
}

export const ChannelList: React.FC<Props & { onNavigate: (delta: number) => void; onSelect: () => void }> = ({
  channels,
  selectedIndex,
  searchQuery,
  theme,
  scrollOffset,
  visibleCount,
  onNavigate,
  onSelect,
}) => {
  const filtered = channels.filter(ch =>
    ch.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    ch.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  useInput((input, key) => {
    if (input === 'j' || key.downArrow) onNavigate(1);
    if (input === 'k' || key.upArrow) onNavigate(-1);
    if (input === 'enter' || input === 'l') onSelect();
  });

  const visibleChannels = filtered.slice(scrollOffset, scrollOffset + visibleCount);

  return (
    <Box flexDirection="column" width="40%" borderStyle="single" borderColor={theme.header}>
      <Box>
        <Text color={theme.header}>{` Channels (${filtered.length}) `}</Text>
      </Box>
      {visibleChannels.map((channel, idx) => {
        const absoluteIndex = idx + scrollOffset;
        const isSelected = absoluteIndex === selectedIndex;
        const heart = channel.isFavorite ? '♥ ' : '  ';
        const prefix = isSelected ? '▶ ' : '  ';

        return (
          <Box key={channel.id}>
            {isSelected ? (
              <Text backgroundColor="white" color={theme.selected}>
                {prefix}{heart}{channel.title.padEnd(30).slice(0, 30)}
              </Text>
            ) : (
              <Text color={theme.info}>
                {prefix}{heart}{channel.title.padEnd(30).slice(0, 30)}
              </Text>
            )}
          </Box>
        );
      })}
    </Box>
  );
};
