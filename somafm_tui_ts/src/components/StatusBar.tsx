/**
 * Status Bar component - Bottom instruction bar
 * Ported from Python ui.py status bar
 */

import React from 'react';
import { Box, Text } from 'ink';
import { ThemeColors } from '../types';

interface Props {
  theme: ThemeColors;
  volume: number;
  sleepTimerMinutes: number;
  isSleepTimerActive: boolean;
}

export const StatusBar: React.FC<Props> = ({ theme, volume, sleepTimerMinutes, isSleepTimerActive }) => {
  const sleepText = isSleepTimerActive ? `[Sleep: ${sleepTimerMinutes}m]` : '';
  const volumeText = `[Vol: ${volume}%]`;

  return (
    <Box flexDirection="column" borderStyle="single" borderColor={theme.header} width="100%">
      <Text color={theme.instructions}>
        {'↑↓/jk - select | Enter/l - play | / - search | Space - pause | h - stop | f - favorite | r - bitrate | s - sleep | t/y - theme | PgUp/Dn - volume | q - quit'}
      </Text>
      <Box justifyContent="space-between">
        <Text color={theme.metadata}>{sleepText}</Text>
        <Text color={theme.metadata}>{volumeText}</Text>
      </Box>
    </Box>
  );
};
