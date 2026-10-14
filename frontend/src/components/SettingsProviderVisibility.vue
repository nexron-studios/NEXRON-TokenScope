<script setup lang="ts">
import { computed } from 'vue'
import ProviderMark from '@/components/ProviderMark.vue'
import { useI18n } from '@/composables/useI18n'
import { useSettings } from '@/composables/useSettings'
import { BRANDS } from '@/theme/brands'
import { scopeOf } from '@/utils/scope'
import type { ProviderId, ProviderUsage } from '@/api/types'
import { Eye, EyeOff, Info } from '@lucide/vue'

const { providers } = defineProps<{
  /** Alle Kacheln vom Backend, auch ausgeblendete – sonst ließe sich nichts wieder einblenden. */
  providers: ProviderUsage[]
}>()

const { settings } = useSettings()
const { t } = useI18n()

const PROVIDERS: ProviderId[] = ['claude', 'codex']

/** Logins nur zeigen, wo es mehr als einen gibt – sonst ist der Anbieter-Schalter dasselbe. */
const loginsOf = computed(() => {
  const grouped: Record<ProviderId, ProviderUsage[]> = { claude: [], codex: [] }
  for (const usage of providers) {
    if (usage.account) grouped[usage.id].push(usage)
  }
  return grouped
})

const hasAccountList = computed(() =>
  PROVIDERS.some((id) => loginsOf.value[id].length > 1),
)

const isAccountVisible = (usage: ProviderUsage) =>
  !settings.value.hiddenAccounts.includes(scopeOf(usage))

const toggleProvider = (id: ProviderId) => {
  settings.value.enabledProviders = {
    ...settings.value.enabledProviders,
    [id]: !settings.value.enabledProviders[id],
  }
}

const toggleAccount = (usage: ProviderUsage) => {
  const key = scopeOf(usage)
  const hidden = settings.value.hiddenAccounts
  settings.value.hiddenAccounts = hidden.includes(key)
    ? hidden.filter((entry) => entry !== key)
    : [...hidden, key]
}
</script>

<template>
  <div class="flex min-w-0 flex-col gap-[0.55rem]">
    <p class="text-[0.6875rem] font-extrabold uppercase tracking-[0.1em] text-[#bcbcc5]">
      {{ t('settings.providers') }}
    </p>

    <template v-for="id in PROVIDERS" :key="id">
      <button
        type="button"
        class="flex min-h-[3.25rem] touch-manipulation items-center gap-[0.6rem] rounded-[0.9rem] border border-white/8 bg-white/3 px-[0.9rem]"
        :class="settings.enabledProviders[id] ? 'text-[#f4f4f6]' : 'text-[#acacb6]'"
        role="switch"
        :aria-checked="settings.enabledProviders[id]"
        @click="toggleProvider(id)"
      >
        <ProviderMark
          class="shrink-0"
          :class="{ 'opacity-35': !settings.enabledProviders[id] }"
          :provider="id"
          :size="22"
        />
        <span class="text-sm font-bold">{{ BRANDS[id].name }}</span>
        <span class="ml-auto flex items-center gap-[0.35rem] text-xs text-[#bababf]">
          <component
            :is="settings.enabledProviders[id] ? Eye : EyeOff"
            class="size-[0.9rem] shrink-0"
            aria-hidden="true"
          />
          {{ settings.enabledProviders[id] ? t('settings.visible') : t('settings.off') }}
        </span>
      </button>

      <ul
        v-if="settings.enabledProviders[id] && loginsOf[id].length > 1"
        class="ml-5 flex flex-col gap-[0.4rem] border-l border-white/8 pl-3"
        :aria-label="t('settings.accountsOf', { provider: BRANDS[id].name })"
      >
        <li v-for="usage in loginsOf[id]" :key="scopeOf(usage)">
          <button
            type="button"
            class="flex min-h-[2.75rem] w-full touch-manipulation items-center gap-[0.6rem] rounded-[0.8rem] border border-white/7 px-[0.8rem] text-left"
            :class="isAccountVisible(usage) ? 'text-[#f4f4f6]' : 'text-[#acacb6]'"
            role="switch"
            :aria-checked="isAccountVisible(usage)"
            @click="toggleAccount(usage)"
          >
            <span class="flex min-w-0 flex-col">
              <span class="text-[0.8125rem] font-bold">
                {{ usage.account?.name }}
                <span v-if="usage.plan" class="font-normal text-[#bababf]">· {{ usage.plan }}</span>
              </span>
              <span
                v-if="usage.account?.email"
                class="truncate text-[0.6875rem] text-[#b2b2bb]"
              >
                {{ usage.account.email }}
              </span>
            </span>
            <span class="ml-auto flex shrink-0 items-center gap-[0.35rem] text-xs text-[#bababf]">
              <component
                :is="isAccountVisible(usage) ? Eye : EyeOff"
                class="size-[0.9rem] shrink-0"
                aria-hidden="true"
              />
              {{ isAccountVisible(usage) ? t('settings.visible') : t('settings.off') }}
            </span>
          </button>
        </li>
      </ul>
    </template>

    <p v-if="hasAccountList" class="flex gap-[0.45rem] text-xs leading-[1.4] text-[#b2b2bb]">
      <Info class="mt-[0.1rem] size-[0.875rem] flex-none opacity-80" aria-hidden="true" />
      <span>{{ t('settings.accountsHint') }}</span>
    </p>
  </div>
</template>
