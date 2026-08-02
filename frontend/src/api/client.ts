import type {
  HealthResponse,
  HistoryResponse,
  LogGroupBy,
  LogSummary,
  UsageResponse,
} from '@/api/types'

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
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response

  try {
    response = await fetch(`${BASE}${path}`, {
      signal,
      headers: { Accept: 'application/json' },
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(
      'Der lokale Dienst antwortet nicht. Läuft das Backend auf Port 8787?',
    )
  }

  if (!response.ok) {
    throw new ApiError(`Backend meldet HTTP ${response.status}.`, response.status)
  }

  try {
    return (await response.json()) as T
  } catch {
    throw new ApiError('Antwort des Backends war kein gültiges JSON.')
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
