import type {
  ServiceStatus,
  StatusPageResponse,
  StatusResult,
} from '@/services/usage.types'

const STATUS_BY_INDICATOR: Record<string, ServiceStatus> = {
  none: 'online',
  minor: 'degraded',
  major: 'outage',
  critical: 'outage',
}

const createTimeoutSignal = (externalSignal?: AbortSignal) => {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 4_500)

  externalSignal?.addEventListener('abort', () => controller.abort(), {
    once: true,
  })

  return {
    signal: controller.signal,
    dispose: () => window.clearTimeout(timeout),
  }
}

export async function getPublicServiceStatus(
  endpoint: string,
  signal?: AbortSignal,
): Promise<StatusResult> {
  const request = createTimeoutSignal(signal)

  try {
    const response = await fetch(endpoint, {
      cache: 'no-store',
      headers: { Accept: 'application/json' },
      signal: request.signal,
    })

    if (!response.ok) {
      throw new Error(`Statusseite antwortet mit HTTP ${response.status}`)
    }

    const payload = (await response.json()) as StatusPageResponse
    const indicator = payload.status?.indicator ?? ''

    return {
      status: STATUS_BY_INDICATOR[indicator] ?? 'unavailable',
      description: payload.status?.description ?? 'Status nicht verfügbar',
      checkedAt: payload.page?.updated_at ?? new Date().toISOString(),
    }
  } catch (error) {
    if (signal?.aborted) {
      throw error
    }

    return {
      status: 'unavailable',
      description:
        error instanceof Error
          ? error.message
          : 'Öffentlicher Dienststatus nicht erreichbar',
      checkedAt: new Date().toISOString(),
    }
  } finally {
    request.dispose()
  }
}
