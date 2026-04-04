/**
 * Sleep Timer Overlay component
 * Ported from Python ui.py sleep timer overlay
 */

import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';
import { ThemeColors } from '../types';

interface Props {
  theme: ThemeColors;
  onSet: (minutes: number) => void;
  onCancel: () => void;
}

const MAX_DIGITS = 3;
const MAX_MINUTES = 480;

export const SleepTimerOverlay: React.FC<Props> = ({ theme, onSet, onCancel }) => {
  const [input, setInput] = useState('');

  useInput((inputChar, key) => {
    if (key.escape || inputChar === 'q') {
      onCancel();
      return;
    }

    if (inputChar === 'enter' && input.length > 0) {
      const minutes = parseInt(input, 10);
      if (minutes >= 1 && minutes <= MAX_MINUTES) {
        onSet(minutes);
      }
      return;
    }

    // Only digits allowed
    if (/^[1-9]$/.test(inputChar) && input.length < MAX_DIGITS) {
      // Validate first digit (1-4)
      if (input.length === 0 && parseInt(inputChar, 10) > 4) return;
      
      // Validate against max 480
      const newValue = input + inputChar;
      const numValue = parseInt(newValue, 10);
      if (numValue <= MAX_MINUTES) {
        setInput(newValue);
      }
    }
  });

  return (
    <Box
      justifyContent="center"
      alignItems="center"
      flexGrow={1}
      flexDirection="column"
    >
      <Box
        borderStyle="double"
        borderColor={theme.header}
        paddingX={2}
        paddingY={1}
        flexDirection="column"
      >
        <Text color={theme.header}>Sleep Timer (1-480 min)</Text>
        <Text color={theme.selected}>Enter minutes: {input}█</Text>
        <Text color={theme.instructions}>Esc/Enter to confirm</Text>
      </Box>
    </Box>
  );
};
