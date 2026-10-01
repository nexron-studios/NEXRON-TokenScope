import type { ProviderId, ServiceStatus } from '@/api/types'

/**
 * Kurzname für die Kopfzeile. „Claude Code" aus `BRANDS` ist für die Stelle
 * neben der Uhr zu lang, und Produktnamen werden nicht übersetzt.
 */
export const SHORT_PROVIDER_NAMES: Record<ProviderId, string> = {
  claude: 'Claude',
  codex: 'Codex',
}

/**
 * Nur eine echte Störung bekommt Fläche im Dashboard. Wartung, „eben behoben"
 * und ein unbekannter Stand stehen in der Kopfzeile – sie verlangen nichts.
 */
export const isDisrupted = (status: ServiceStatus): boolean =>
  !status.stale && (status.level === 'degraded' || status.level === 'outage')

/** „https://status.openai.com" → „status.openai.com" */
export const pageHost = (pageUrl: string): string => pageUrl.replace(/^https?:\/\//, '')
