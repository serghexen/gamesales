import { describe, expect, it, vi } from 'vitest'
import { nextTick, reactive, ref } from 'vue'

import { useWorkLifecycleWatchers } from '../useWorkLifecycleWatchers.js'

describe('useWorkLifecycleWatchers', () => {
  it('rewrites removed tab query to normalized tab', async () => {
    const route = reactive({ query: { tab: 'analytics' } })
    const activeTab = ref('deals')
    const setActiveTab = vi.fn()

    useWorkLifecycleWatchers({
      route,
      TAB_KEYS: ['deals', 'finance'],
      normalizeWorkTab: (tab) => (tab === 'finance' ? 'finance' : 'deals'),
      setActiveTab,
      activeTab,
      telegram: reactive({ status: '', activeChatId: '' }),
      startTelegramPolling: vi.fn(),
      stopTelegramPolling: vi.fn(),
      handleTelegramActiveChatChange: vi.fn(),
      editAccount: reactive({ open: false }),
      domains: ref([]),
      loadDomains: vi.fn(),
      resetModalPos: vi.fn(),
    })

    await nextTick()

    expect(setActiveTab).toHaveBeenCalledWith('deals')
    expect(activeTab.value).toBe('deals')
  })
})
