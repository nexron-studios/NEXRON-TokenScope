import { useLocalStorage } from '@vueuse/core'
import type { ProviderId } from '@/api/types'
import type { Language } from '@/composables/useI18n'

export type HistoryRange = 6 | 24 | 72 | 168

export interface AppSettings {
  /** Sprache der lokalen Oberfläche. */
  language: Language
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
  language: 'de',
  autoRefresh: true,
  refreshIntervalSeconds: 60,
  enabledProviders: { claude: true, codex: true },
  historyHours: 24,
  logDays: 7,
  kioskMode: false,
  nightMode: false,
  largeText: false,
}

const SETTINGS_KEY = 'nexron-tokenscope:settings'
const LEGACY_SETTINGS_KEY = 'ai-usage-monitor:settings'

// Bestehende Installationen behalten ihre lokalen Anzeigeoptionen. Der alte
// Key bleibt nur als Migrationsquelle erhalten und wird nicht weiter benutzt.
if (
  typeof window !== 'undefined' &&
  window.localStorage.getItem(SETTINGS_KEY) === null
) {
  const legacy = window.localStorage.getItem(LEGACY_SETTINGS_KEY)
  if (legacy !== null) window.localStorage.setItem(SETTINGS_KEY, legacy)
}

const settings = useLocalStorage<AppSettings>(
  SETTINGS_KEY,
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
