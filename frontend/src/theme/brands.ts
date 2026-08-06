import type { ProviderId } from '@/api/types'

export type Severity = 'ok' | 'warning' | 'critical'

/**
 * Statusfarben sind reserviert und niemals Seriennfarben. Sie treten immer
 * zusammen mit Symbol und Text auf, nie als alleiniger Bedeutungsträger.
 */
export const SEVERITY = {
  ok: { label: 'Reichlich', short: 'OK', color: '#0ca30c' },
  warning: { label: 'Wird knapp', short: 'Knapp', color: '#fab219' },
  critical: { label: 'Kritisch', short: 'Kritisch', color: '#d03b3b' },
} as const satisfies Record<Severity, { label: string; short: string; color: string }>

export function severityOf(remainingPercent: number): Severity {
  if (remainingPercent <= 15) return 'critical'
  if (remainingPercent <= 35) return 'warning'
  return 'ok'
}

export interface BrandTheme {
  id: ProviderId
  /** Anzeigename im Kachelkopf. */
  name: string
  /** Kurzform für Legenden und enge Zeilen. */
  short: string
  scheme: 'light' | 'dark'
  /** Kachelfläche. */
  surface: string
  surfaceRaised: string
  ink: string
  inkMuted: string
  inkSubtle: string
  hairline: string
  /** Markenakzent – Füllung des Meters im gesunden Zustand. */
  accent: string
  /** Hellerer Schritt derselben Rampe für die Meter-Spur. */
  track: string
  /** Geprüfter Serienschritt für den Verlaufschart auf dunkler Fläche. */
  series: string
  /** Displayschrift des Wortzeichens. */
  display: string
}

/**
 * Anthropic: warmes Anthrazit (#1A1A19), Korallenakzent, Serifen-Wortzeichen.
 * OpenAI/Codex: tiefes Schwarz, Haarlinien, monochrom-sachlich.
 *
 * Die Serienfarben (`series`) sind bewusst dunklere Schritte der jeweiligen
 * Markenfarbe: Sie liegen im OKLCH-Band der dunklen Chartfläche und bestehen
 * die CVD-Trennung, während die Kacheln den echten Markenton tragen.
 */
export const BRANDS: Record<ProviderId, BrandTheme> = {
  claude: {
    id: 'claude',
    name: 'Claude Code',
    short: 'Claude',
    scheme: 'dark',
    surface: '#1a1a19',
    surfaceRaised: '#252523',
    // Warmes Off-White statt reinem Weiß – bleibt in der Papier-Anmutung.
    ink: '#f5f4ef',
    inkMuted: '#d6d4cc',
    inkSubtle: '#bab8b0',
    hairline: 'rgb(245 244 239 / 13%)',
    accent: '#d97757',
    track: 'rgb(217 119 87 / 22%)',
    series: '#d0704e',
    display: '"Iowan Old Style", "Palatino Linotype", Georgia, ui-serif, serif',
  },
  codex: {
    id: 'codex',
    name: 'Codex',
    short: 'Codex',
    scheme: 'dark',
    surface: '#0a0a0a',
    surfaceRaised: '#161616',
    ink: '#ffffff',
    inkMuted: '#d4d4d8',
    inkSubtle: '#b4b4b9',
    hairline: 'rgb(255 255 255 / 14%)',
    accent: '#10a37f',
    track: 'rgb(16 163 127 / 22%)',
    series: '#00a3a3',
    display: '"Segoe UI", Inter, ui-sans-serif, system-ui, sans-serif',
  },
}

export function brandOf(id: ProviderId): BrandTheme {
  return BRANDS[id] ?? BRANDS.claude
}

/** CSS-Variablen einer Marke für `:style` auf dem Kachelelement. */
export function brandVars(theme: BrandTheme): Record<string, string> {
  return {
    '--brand-surface': theme.surface,
    '--brand-surface-raised': theme.surfaceRaised,
    '--brand-ink': theme.ink,
    '--brand-ink-muted': theme.inkMuted,
    '--brand-ink-subtle': theme.inkSubtle,
    '--brand-hairline': theme.hairline,
    '--brand-accent': theme.accent,
    '--brand-track': theme.track,
    '--brand-display': theme.display,
  }
}
