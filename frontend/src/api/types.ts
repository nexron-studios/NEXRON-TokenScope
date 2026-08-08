export type ProviderId = 'claude' | 'codex'

export type ProviderStatus =
  | 'ok'
  | 'disabled'
  | 'auth_missing'
  | 'auth_expired'
  | 'unauthorized'
  | 'rate_limited'
  | 'unreachable'
  | 'unexpected_shape'
  | 'error'

export type SourceKind = 'api' | 'logs' | 'cli' | 'demo' | 'none'

export interface UsageWindow {
  key: string
  label: string
  used_percent: number
  remaining_percent: number
  resets_at: string | null
  window_minutes: number | null
  primary: boolean
}

export interface ProviderUsage {
  id: ProviderId
  name: string
  plan: string | null
  windows: UsageWindow[]
  source: SourceKind
  status: ProviderStatus
  message: string | null
  /** Zeitpunkt dieser Werte – bei `stale` älter als der letzte Poll. */
  fetched_at: string
  /** Werte stammen aus dem letzten geglückten Abruf. */
  stale: boolean
  /** Warum der frische Abruf scheiterte. */
  warning: string | null
  retry_after_seconds: number | null
}

export interface UsageResponse {
  generated_at: string
  poll_interval_seconds: number
  demo_mode: boolean
  providers: ProviderUsage[]
}

export interface HistoryPoint {
  captured_at: string
  used_percent: number
}

export interface HistorySeries {
  provider: ProviderId
  window_key: string
  label: string
  points: HistoryPoint[]
}

export interface HistoryResponse {
  since: string
  series: HistorySeries[]
}

export interface TokenTotals {
  input_tokens: number
  output_tokens: number
  cache_write_tokens: number
  cache_read_tokens: number
}

export type LogGroupBy = 'day' | 'project' | 'model' | 'provider'

export interface LogBucket {
  key: string
  label: string
  provider: ProviderId
  messages: number
  totals: TokenTotals
}

/** Eine Zelle des Wochenrasters: Wochentag (0 = Montag) × Stunde. */
export interface ActivityCell {
  weekday: number
  hour: number
  messages: number
  tokens: number
}

export interface LogInsights {
  sessions: number
  messages: number
  active_days: number
  current_streak: number
  longest_streak: number
  peak_hour: number | null
  top_model: string | null
  top_model_messages: number
  /** Nur belegte Zellen – das Raster wird in der Oberfläche aufgefüllt. */
  activity: ActivityCell[]
}

export interface LogSummary {
  since: string
  days: number
  group_by: LogGroupBy
  scanned_files: number
  skipped_lines: number
  totals: TokenTotals
  buckets: LogBucket[]
  insights: LogInsights
}

export interface HealthResponse {
  status: 'ok'
  version: string
  demo_mode: boolean
  loopback_only: boolean
  history_enabled: boolean
  last_poll_at: string | null
  last_poll_error: string | null
  sources: Record<string, boolean>
}
