import type { HistorySeries, ProviderId, ProviderUsage } from '@/api/types'
import type { Language } from '@/composables/useI18n'
import { brandOf } from '@/theme/brands'
import { scopeKey, scopeOf } from '@/utils/scope'

export interface ChartPoint {
  t: number
  used: number
}

export interface ChartSeries {
  /** `scopeKey` – eine Linie je Login. */
  key: string
  provider: ProviderId
  /** Direktbeschriftung am Linienende – bei mehreren Logins der Account. */
  short: string
  /** Legende und Tooltip: Anbieter, bei mehreren Logins mit Account. */
  legend: string
  color: string
  /**
   * Zweiter und weiterer Login desselben Anbieters: eigene Farbe wie seine
   * Kachel, zusätzlich gestrichelt. Die Identität hängt so nie allein an der
   * Farbe.
   */
  dashed: boolean
  label: string
  points: ChartPoint[]
  /** Jüngster Punkt – trägt Endmarker und Direktbeschriftung. */
  last: ChartPoint
}

const WINDOW_LABELS_EN: Record<string, string> = {
  five_hour: '5 hours',
  seven_day: '7 days',
  seven_day_opus: '7 days · Opus',
  seven_day_oauth_apps: '7 days · Apps',
  monthly: '30 days',
}

const rankOf = (key: string): number =>
  key === 'five_hour' || key === 'primary' ? 0 : key === 'seven_day' ? 1 : 2

const windowLabel = (entry: HistorySeries, language: Language): string => {
  if (language !== 'en') return entry.label
  if (entry.window_key === 'primary') return entry.label === '7 Tage' ? '7 days' : entry.label
  return WINDOW_LABELS_EN[entry.window_key] ?? entry.label
}

const pointsOf = (entry: HistorySeries): ChartPoint[] =>
  entry.points
    .map((point) => ({ t: new Date(point.captured_at).getTime(), used: point.used_percent }))
    .filter((point) => Number.isFinite(point.t))
    .sort((a, b) => a.t - b.t)

/**
 * Pro sichtbarem Login genau eine Linie: das kürzeste gespeicherte Fenster.
 * Reihenfolge und Strichart folgen den Kacheln, damit Linie und Kachel
 * zusammengehören.
 */
export const buildHistorySeries = (
  raw: HistorySeries[],
  visible: ProviderUsage[],
  tones: Record<string, number>,
  language: Language,
): ChartSeries[] => {
  const order = visible.map(scopeOf)
  const chosen = new Map<
    string,
    { rank: number; entry: HistorySeries; points: ChartPoint[]; last: ChartPoint }
  >()

  for (const entry of raw) {
    const key = scopeKey(entry.provider, entry.account)
    if (!order.includes(key)) continue

    const rank = rankOf(entry.window_key)
    const existing = chosen.get(key)
    if (existing && existing.rank <= rank) continue

    const points = pointsOf(entry)
    const last = points.at(-1)
    if (!last) continue
    chosen.set(key, { rank, entry, points, last })
  }

  return visible.flatMap((usage) => {
    const found = chosen.get(scopeOf(usage))
    if (!found) return []

    const tone = tones[scopeOf(usage)] ?? 0
    const brand = brandOf(usage.id, tone)
    const siblings = visible.filter((other) => other.id === usage.id)
    const account = siblings.length > 1 ? usage.account : null

    return [
      {
        key: scopeOf(usage),
        provider: usage.id,
        short: account ? account.name : brand.short,
        legend: account ? `${brand.short} · ${account.name}` : brand.short,
        color: brand.series,
        dashed: tone > 0,
        label: windowLabel(found.entry, language),
        points: found.points,
        last: found.last,
      },
    ]
  })
}
