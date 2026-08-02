import { useLocalStorage } from '@vueuse/core'
import type { ProviderId } from '@/api/types'

export type HistoryRange = 6 | 24 | 72 | 168

export interface AppSettings {
  /** Automatisch neu laden (das Backend pollt ohnehin weiter). */
  autoRefresh: boolean
  /** Abholintervall des Frontends in Sekunden. */
  refreshIntervalSeconds: number
  /** Sichtbare Anbieter. */
  enabledProviders: Record<ProviderId, boolean>
  /** Zeitfenster des Verlaufscharts in Stunden. */
  historyHours: HistoryRange
  /** Tage, über die die JSONL-Logs ausgewertet werden. */
  logDays: number
  /** Kiosk: Mauszeiger ausblenden, keine Hover-Zustände. */
  kioskMode: boolean
  /** Nachtmodus dimmt das Panel, ohne die Hintergrundbeleuchtung zu ändern. */
  nightMode: boolean
  /** Größere Typo zum Ablesen aus Entfernung. */
  largeText: boolean
}

const DEFAULTS: AppSettings = {
  autoRefresh: true,
  refreshIntervalSeconds: 60,
  enabledProviders: { claude: true, codex: true },
  historyHours: 24,
  logDays: 7,
  kioskMode: false,
  nightMode: false,
  largeText: false,
}

const settings = useLocalStorage<AppSettings>(
  'ai-usage-monitor:settings',
  { ...DEFAULTS },
  { mergeDefaults: true },
)

export function useSettings() {
  const resetSettings = () => {
    settings.value = {
      ...DEFAULTS,
      enabledProviders: { ...DEFAULTS.enabledProviders },
    }
  }

  return { settings, resetSettings, DEFAULTS }
}
