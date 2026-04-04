/**
 * Now Playing component - Right panel
 * Ported from Python ui.py now playing panel
 */

import React from 'react';
import { Box, Text } from 'ink';
import { Channel, TrackMetadata, TrackHistoryEntry, ThemeColors } from '../types';

interface Props {
  channel: Channel | null;
  metadata: TrackMetadata | null;
  history: TrackHistoryEntry[];
  isPlaying: boolean;
  isPaused: boolean;
  theme: ThemeColors;
}

export const NowPlaying: React.FC<Props> = ({
  channel,
  metadata,
  history,
  isPlaying,
  isPaused,
  theme,
}) => {
  if (!channel) {
    return (
      <Box flexDirection="column" flexGrow={1} paddingLeft={1} borderStyle="single" borderColor={theme.header}>
        <Text color={theme.metadata}>No channel selected</Text>
        <Text color={theme.instructions}>  Use j/k to navigate, l/Enter to play</Text>
      </Box>
    );
  }

  const playIcon = isPaused ? '❚❚' : isPlaying ? '▶' : ' ';

  return (
    <Box flexDirection="column" flexGrow={1} paddingLeft={1} borderStyle="single" borderColor={theme.header}>
      <Box>
        <Text color={theme.header}>♪ {channel.title}</Text>
      </Box>
      <Box>
        <Text color={theme.info} wrap="wrap">{channel.description}</Text>
      </Box>
      <Box marginTop={1}>
        <Text color={theme.metadata}>[L] {channel.listeners} | [B] {channel.bitrate}</Text>
      </Box>
      {metadata && (
        <Box marginTop={1}>
          <Text color={theme.selected}>{playIcon} {metadata.artist} - {metadata.title}</Text>
        </Box>
      )}
      {history.length > 0 && (
        <Box flexDirection="column" marginTop={1}>
          <Text color={theme.header}> History:</Text>
          {history.slice(0, 10).map((entry, i) => (
            <Box key={i}>
              <Text color={theme.metadata}>  {entry.artist} - {entry.title}</Text>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
};
