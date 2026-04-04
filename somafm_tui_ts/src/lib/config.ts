/**
 * Configuration management with XDG compliance
 * Ported from Python config.py
 */

import { JSONFilePreset } from 'lowdb/node';
import { AppConfig } from '../types';
import { join } from 'path';
import { existsSync, mkdirSync } from 'fs';

export interface ConfigData {
  theme: string;
  volume: number;
  alternativeBgMode: boolean;
  dbusAllowed: boolean;
  dbusSendMetadata: boolean;
}

function getConfigDir(): string {
  return process.env.XDG_CONFIG_HOME 
    ? join(process.env.XDG_CONFIG_HOME, 'somafm-tui')
    : join(process.env.HOME || '/tmp', '.config', 'somafm-tui');
}

function ensureConfigDir(): void {
  const dir = getConfigDir();
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
}

function getConfigPath(): string {
  ensureConfigDir();
  return join(getConfigDir(), 'config.json');
}

/**
 * Load application configuration
 */
export async function loadConfig(): Promise<AppConfig> {
  const defaultData: ConfigData = {
    theme: 'default',
    volume: 100,
    alternativeBgMode: false,
    dbusAllowed: false,
    dbusSendMetadata: false,
  };

  try {
    const db = await JSONFilePreset<ConfigData>(getConfigPath(), defaultData);
    return {
      theme: db.data.theme,
      volume: db.data.volume,
      alternativeBgMode: db.data.alternativeBgMode,
      dbusAllowed: db.data.dbusAllowed,
      dbusSendMetadata: db.data.dbusSendMetadata,
    };
  } catch {
    return {
      theme: defaultData.theme,
      volume: defaultData.volume,
      alternativeBgMode: defaultData.alternativeBgMode,
      dbusAllowed: defaultData.dbusAllowed,
      dbusSendMetadata: defaultData.dbusSendMetadata,
    };
  }
}

/**
 * Save application configuration
 */
export async function saveConfig(config: Partial<AppConfig>): Promise<void> {
  const defaultData: ConfigData = {
    theme: 'default',
    volume: 100,
    alternativeBgMode: false,
    dbusAllowed: false,
    dbusSendMetadata: false,
  };

  ensureConfigDir();
  const db = await JSONFilePreset<ConfigData>(getConfigPath(), defaultData);

  if (config.theme !== undefined) db.data.theme = config.theme;
  if (config.volume !== undefined) db.data.volume = config.volume;
  if (config.alternativeBgMode !== undefined) db.data.alternativeBgMode = config.alternativeBgMode;
  if (config.dbusAllowed !== undefined) db.data.dbusAllowed = config.dbusAllowed;
  if (config.dbusSendMetadata !== undefined) db.data.dbusSendMetadata = config.dbusSendMetadata;

  await db.write();
}
