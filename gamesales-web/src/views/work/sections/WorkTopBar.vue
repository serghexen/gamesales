<template>
  <header class="top">
    <div class="brand">
      <div class="logo">
        <img src="../../../assets/logo.jpg" alt="Логотип" />
      </div>
      <div>
        <div class="title">Рабочая зона</div>
      </div>
    </div>

    <div class="actions">
      <nav class="tabs">
        <router-link
          v-if="showDashboard"
          class="tab"
          :class="{ active: activeTab === 'dashboard' }"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'dashboard' } }"
        >
          Дашборд
        </router-link>
        <router-link class="tab" :class="{ active: activeTab === 'deals' }" :to="{ name: 'work', query: { ...routeQuery, tab: 'deals' } }">
          Сделки
        </router-link>
        <router-link class="tab" :class="{ active: activeTab === 'accounts' }" :to="{ name: 'work', query: { ...routeQuery, tab: 'accounts' } }">
          Аккаунты
        </router-link>
        <router-link class="tab" :class="{ active: activeTab === 'products' }" :to="{ name: 'work', query: { ...routeQuery, tab: 'products' } }">
          Товары
        </router-link>
        <router-link
          v-if="isAdmin"
          class="tab"
          :class="{ active: activeTab === 'catalogs' }"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'catalogs' } }"
        >
          Справочники
        </router-link>
        <router-link
          v-if="showChatsTab"
          class="tab"
          :class="{ active: activeTab === 'telegram' }"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'telegram' } }"
        >
          Чаты
          <span class="tab__badge" aria-hidden="true"></span>
        </router-link>
        <router-link
          v-if="isAdmin"
          class="tab"
          :class="{ active: activeTab === 'analytics' }"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'analytics' } }"
        >
          Аналитика
          <span class="tab__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <path d="M6 10V8a6 6 0 1 1 12 0v2" />
              <rect x="5" y="10" width="14" height="10" rx="2" />
            </svg>
          </span>
        </router-link>
        <router-link
          v-if="isAdmin && showUsersTab"
          class="tab"
          :class="{ active: activeTab === 'users' }"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'users' } }"
        >
          Пользователи
        </router-link>
      </nav>
      <div class="tabs tabs--right">
        <span v-if="userRoleName" class="top-role">{{ userRoleName }}</span>
        <router-link
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
  </header>
</template>

<script setup>
import { computed, unref } from 'vue'

// Контекст верхней панели (табы, пользователь, выход).
const props = defineProps({
  ctx: {
    type: Object,
    required: true,
  },
})

const activeTab = computed(() => unref(props.ctx.activeTab))
const routeQuery = computed(() => unref(props.ctx.routeQuery) || {})
const isAdmin = computed(() => unref(props.ctx.isAdmin))
const showChatsTab = computed(() => unref(props.ctx.showChatsTab))
const showUsersTab = computed(() => unref(props.ctx.showUsersTab))
const showDashboard = computed(() => unref(props.ctx.showDashboard))
const userRoleName = computed(() => unref(props.ctx.userRoleName))
</script>
