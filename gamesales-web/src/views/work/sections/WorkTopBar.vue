<template>
  <header class="top">
    <div class="brand">
      <div class="logo">
        <img :src="brandLogoSrc" alt="Логотип" />
      </div>
    </div>

    <div class="actions">
      <div class="actions__main">
        <nav class="tabs">
          <router-link
            v-if="canViewDashboardSection"
            class="tab"
            :class="{ active: activeTab === 'dashboard' }"
            :to="{ name: 'work', query: { ...routeQuery, tab: 'dashboard' } }"
          >
            Дашборд
          </router-link>
          <router-link v-if="canViewDealsSection" class="tab" :class="{ active: activeTab === 'deals' }" :to="{ name: 'work', query: { ...routeQuery, tab: 'deals' } }">
            Сделки
          </router-link>
          <router-link v-if="canViewAccountsSection" class="tab" :class="{ active: activeTab === 'accounts' }" :to="{ name: 'work', query: { ...routeQuery, tab: 'accounts' } }">
            Аккаунты
          </router-link>
          <router-link v-if="canViewProductsSection" class="tab" :class="{ active: activeTab === 'products' }" :to="{ name: 'work', query: { ...routeQuery, tab: 'products' } }">
            Товары
          </router-link>
          <router-link v-if="canViewNsGiftSection" class="tab" :class="{ active: activeTab === 'ns-gift' }" :to="{ name: 'work', query: { ...routeQuery, tab: 'ns-gift' } }">
            Магазин
          </router-link>
          <router-link v-if="canViewInterhubSection" class="tab" :class="{ active: activeTab === 'interhub' }" :to="{ name: 'work', query: { ...routeQuery, tab: 'interhub' } }">
            Платежи
          </router-link>
          <router-link
            v-if="canViewTelegramSection"
            class="tab"
            :class="{ active: activeTab === 'telegram' }"
            :to="{ name: 'work', query: { ...routeQuery, tab: 'telegram' } }"
          >
            Чаты
            <span class="tab__badge" aria-hidden="true"></span>
          </router-link>
          <router-link
            v-if="canViewUsersSection"
            class="tab"
            :class="{ active: activeTab === 'users' }"
            :to="{ name: 'work', query: { ...routeQuery, tab: 'users' } }"
          >
            Пользователи
          </router-link>
        </nav>
        <WorkTrCardBalanceWidget :ctx="ctx" />
        <div class="tab-workload">
          <span class="tab-workload__title">Сделок в работе:</span>
          <div class="tab-workload__line">
            <span
              v-for="item in managerLoadPreview"
              :key="`manager-load-${item.username}`"
              class="tab-workload__item"
            >
              <span class="tab-workload__dot" :class="{ 'is-online': item.isOnline }" aria-hidden="true"></span>
              <span class="tab-workload__name">{{ item.title }}</span>
              <span class="tab-workload__sep"> - </span>
              <span class="tab-workload__count">{{ item.pendingCount }}</span>
            </span>
          </div>
        </div>
        <div class="tabs tabs--right">
          <span v-if="userRoleName" class="top-role">{{ userRoleName }}</span>
          <router-link
            v-if="canViewProfileSection"
            class="top-profile-btn"
            :class="{ 'is-active': activeTab === 'profile' }"
            :to="{ name: 'work', query: { ...routeQuery, tab: 'profile' } }"
            aria-label="Профиль"
            title="Профиль"
          >
            <span class="top-profile-btn__content">
              <svg class="top-profile-btn__icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </span>
          </router-link>
          <button
            class="top-logout-btn"
            @click="ctx.onLogout"
            aria-label="Выйти"
            title="Выйти"
          >
            <span class="top-logout-btn__content">
              <svg class="top-logout-btn__icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
            </span>
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed, unref } from 'vue'
import defaultLogoSrc from '../../../assets/logo.jpg'
import stagingLogoSrc from '../../../assets/logo-staging.jpg'
import WorkTrCardBalanceWidget from './WorkTrCardBalanceWidget.vue'

// Контекст верхней панели (табы, пользователь, выход).
const props = defineProps({
  ctx: {
    type: Object,
    required: true,
  },
})

const activeTab = computed(() => unref(props.ctx.activeTab))
const routeQuery = computed(() => unref(props.ctx.routeQuery) || {})
// Для тестового стенда показываем отдельный логотип, не меняя production-сборку.
const brandLogoSrc = computed(() => {
  const appEnv = String(import.meta.env.VITE_APP_ENV || '').trim().toLowerCase()
  return appEnv === 'staging' ? stagingLogoSrc : defaultLogoSrc
})
const canViewDealsSection = computed(() => unref(props.ctx.canViewDealsSection))
const canViewAccountsSection = computed(() => unref(props.ctx.canViewAccountsSection))
const canViewProductsSection = computed(() => unref(props.ctx.canViewProductsSection))
const canViewNsGiftSection = computed(() => unref(props.ctx.canViewNsGiftSection))
const canViewInterhubSection = computed(() => unref(props.ctx.canViewInterhubSection))
const canViewTelegramSection = computed(() => unref(props.ctx.canViewTelegramSection))
const canViewUsersSection = computed(() => unref(props.ctx.canViewUsersSection))
const canViewProfileSection = computed(() => unref(props.ctx.canViewProfileSection))
const canViewDashboardSection = computed(() => unref(props.ctx.canViewDashboardSection))
const userRoleName = computed(() => unref(props.ctx.userRoleName))
const managerLoadPreview = computed(() => {
  // В шапке показываем только тех, у кого есть активные сделки в работе.
  const raw = unref(props.ctx.managersLoadItems) || []
  return (Array.isArray(raw) ? raw : [])
    .filter((item) => Number(item?.pending_count || 0) > 0)
    .map((item) => {
    const username = String(item?.username || '').trim()
    const name = String(item?.name || '').trim()
    const pendingCount = Number(item?.pending_count || 0)
    return {
      username,
      pendingCount,
      isOnline: Boolean(item?.is_online),
      title: name || username || 'Менеджер',
    }
  })
})
</script>
