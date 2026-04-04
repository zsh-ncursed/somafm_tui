/**
 * Help Overlay component
 * Ported from Python ui.py help overlay
 */

import React from 'react';
import { Box, Text, useInput } from 'ink';
import { ThemeColors } from '../types';

interface Props {
  theme: ThemeColors;
  onClose: () => void;
}

const HELP_ITEMS = [
  ['↑↓/j/k', 'Navigate channels'],
  ['Enter/l', 'Play selected channel'],
  ['Space', 'Toggle pause'],
  ['h', 'Stop playback'],
  ['f', 'Toggle favorite'],
  ['r', 'Cycle bitrate'],
  ['s', 'Set sleep timer'],
  ['t', 'Next theme'],
  ['y', 'Previous theme'],
  ['PgUp/PgDn', 'Volume up/down'],
  ['/', 'Search channels'],
  ['?', 'Show this help'],
  ['q', 'Quit'],
];

export const HelpOverlay: React.FC<Props> = ({ theme, onClose }) => {
  useInput((input, key) => {
    if (input === '?' || input === 'q' || key.escape) {
      onClose();
    }
  });

  return (
    <Box
      justifyContent="center"
      alignItems="center"
      flexGrow={1}
    >
      <Box
        borderStyle="double"
        borderColor={theme.header}
        paddingX={2}
        paddingY={1}
        flexDirection="column"
      >
        <Text color={theme.header} bold>Keyboard Shortcuts</Text>
        <Text> </Text>
        {HELP_ITEMS.map(([key, desc]) => (
          <Box key={key}>
            <Text color={theme.selected} bold>{key.padEnd(12)}</Text>
            <Text color={theme.info}> {desc}</Text>
          </Box>
        ))}
        <Text> </Text>
        <Text color={theme.instructions}>Press ? or Esc to close</Text>
      </Box>
    </Box>
  );
};
