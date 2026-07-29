export type ServiceId = 'chatgpt' | 'claude'
export type ServiceStatus = 'online' | 'degraded' | 'outage' | 'unavailable'
export type DataSource = 'live' | 'extension' | 'manual' | 'mock'

export interface AIUsageService {
  id: ServiceId
  name: string
  plan?: string
  usedPercentage?: number
  remainingPercentage?: number
  usageText?: string
  resetAt?: string
  updatedAt: string
  status: ServiceStatus
  dataSource: DataSource
  error?: string
}

export interface UsageProvider {
  getUsage(signal?: AbortSignal): Promise<AIUsageService>
}

export interface ManualUsageValue {
  plan: string
  remainingPercentage?: number
  resetAt: string
  usageText: string
}

export interface StatusPageResponse {
  page?: {
    updated_at?: string
  }
  status?: {
    description?: string
    indicator?: 'none' | 'minor' | 'major' | 'critical' | string
  }
}

export interface StatusResult {
  status: ServiceStatus
  description: string
  checkedAt: string
}
