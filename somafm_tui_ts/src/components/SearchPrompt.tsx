/**
 * Search Prompt component
 * Ported from Python ui.py search
 */

import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';
import { ThemeColors } from '../types';

interface Props {
  theme: ThemeColors;
  onSearch: (query: string) => void;
  onCancel: () => void;
}

const MAX_QUERY_LENGTH = 50;

export const SearchPrompt: React.FC<Props> = ({ theme, onSearch, onCancel }) => {
  const [query, setQuery] = useState('');

  useInput((inputChar, key) => {
    if (key.escape || inputChar === 'q') {
      onCancel();
      return;
    }

    if (inputChar === 'enter') {
      onSearch(query);
      return;
    }

    if (key.backspace) {
      setQuery(prev => prev.slice(0, -1));
      return;
    }

    if (inputChar.length === 1 && query.length < MAX_QUERY_LENGTH) {
      setQuery(prev => prev + inputChar);
    }
  });

  return (
    <Box marginTop={1} marginLeft={1}>
      <Box borderStyle="single" borderColor={theme.header} paddingX={1}>
        <Text color={theme.header}>Search: </Text>
        <Text color={theme.selected}>{query}█</Text>
      </Box>
    </Box>
  );
};
