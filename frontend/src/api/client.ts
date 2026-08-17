import type {
  HealthResponse,
  HistoryResponse,
  LogGroupBy,
  LogSummary,
  UsageResponse,
} from '@/api/types'
import { useI18n } from '@/composables/useI18n'

/**
 * Basis-URL des lokalen Backends. Im Dev-Betrieb proxyt Vite `/api`,
 * im Kiosk-Betrieb liefert FastAPI das Frontend selbst aus – in beiden
 * Fällen bleibt der Pfad relativ. Es wird ausschließlich das eigene
 * Backend kontaktiert, nie ein Anbieter direkt.
 */
const BASE = import.meta.env.VITE_API_BASE ?? ''

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
    /** Zweite Zeile im Banner: was der Nutzer dagegen tun kann. */
    readonly hint?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/**
 * Fließtext für Stellen, die nur eine einzelne Zeile zeigen – dort ginge der
 * Hinweis sonst verloren. Das Dashboard-Banner setzt beides selbst.
 */
export function errorText(caught: unknown, fallback: string): string {
  if (!(caught instanceof ApiError)) return fallback
  return caught.hint ? `${caught.message}. ${caught.hint}` : caught.message
}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response
  const { t } = useI18n()

  try {
    response = await fetch(`${BASE}${path}`, {
      signal,
      // TokenScope liefert Live-Daten. Besonders WebView2 darf einen bereits
      // verwendeten GET wie `/api/usage?refresh=true` nicht wiederverwenden.
      cache: 'no-store',
      headers: { Accept: 'application/json' },
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(
      t('error.noBackend'),
      undefined,
      t('error.noBackendHint'),
    )
  }

  if (!response.ok) {
    throw new ApiError(
      t('error.http', { status: response.status }),
      response.status,
      t('error.httpHint'),
    )
  }

  try {
    return (await response.json()) as T
  } catch {
    throw new ApiError(
      t('error.invalid'),
      undefined,
      t('error.invalidHint'),
    )
  }
}

export const api = {
  usage: (options: { refresh?: boolean; signal?: AbortSignal } = {}) =>
    request<UsageResponse>(
      `/api/usage${options.refresh ? '?refresh=true' : ''}`,
      options.signal,
    ),

  history: (hours: number, signal?: AbortSignal) =>
    request<HistoryResponse>(`/api/history?hours=${hours}`, signal),

  logs: (days: number, groupBy: LogGroupBy, signal?: AbortSignal) =>
    request<LogSummary>(
      `/api/logs/summary?days=${days}&group_by=${groupBy}`,
      signal,
    ),

  health: (signal?: AbortSignal) => request<HealthResponse>('/api/health', signal),
}
