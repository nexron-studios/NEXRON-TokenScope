import type { ProviderId, ProviderUsage } from '@/api/types'

/**
 * Schlüssel einer Kachel: der Anbieter, bei mehreren Logins mit Account.
 * Dieselbe Form wie `scope_key` im Backend – der Log-Filter versteht sie direkt.
 */
export const scopeKey = (provider: ProviderId, account?: string | null): string =>
  account ? `${provider}:${account}` : provider

export const scopeOf = (usage: ProviderUsage): string =>
  scopeKey(usage.id, usage.account?.id)

/**
 * Position jedes Logins unter den Logins seines Anbieters, nach `scopeKey`.
 * Gezählt wird über die ungefilterte Liste: Blendet jemand einen Login aus,
 * behalten die übrigen ihre Farbe.
 */
export const accountTonesOf = (all: ProviderUsage[]): Record<string, number> => {
  const counted: Partial<Record<ProviderId, number>> = {}
  return Object.fromEntries(
    all.map((usage) => {
      const tone = counted[usage.id] ?? 0
      counted[usage.id] = tone + 1
      return [scopeOf(usage), tone]
    }),
  )
}

/** Ein Login ist sichtbar, wenn sein Anbieter an und er selbst nicht ausgeblendet ist. */
export const isScopeVisible = (
  enabledProviders: Record<ProviderId, boolean>,
  hiddenAccounts: string[],
  provider: ProviderId,
  account?: string | null,
): boolean =>
  enabledProviders[provider] !== false &&
  !hiddenAccounts.includes(scopeKey(provider, account))

/** Was der Verbrauchsauswertung fehlen soll: ganze Anbieter und einzelne Logins. */
export const excludedScopes = (
  enabledProviders: Record<ProviderId, boolean>,
  hiddenAccounts: string[],
): string[] => [
  ...(Object.keys(enabledProviders) as ProviderId[]).filter(
    (provider) => enabledProviders[provider] === false,
  ),
  ...hiddenAccounts,
]
