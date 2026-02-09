<template>
  <header class="top">
    <div class="brand">
      <div class="logo">
        <img src="../../../assets/logo.jpg" alt="Логотип" />
      </div>
      <div>
        <div class="title">Рабочая зона</div>
        <div class="sub">Пользователь: <b>{{ userName }}</b></div>
      </div>
    </div>

    <div class="actions">
      <nav class="tabs">
        <router-link class="tab" :class="{ active: activeTab === 'deals' }" :to="{ name: 'work', query: { ...routeQuery, tab: 'deals' } }">
          Сделки
        </router-link>
        <router-link class="tab" :class="{ active: activeTab === 'accounts' }" :to="{ name: 'work', query: { ...routeQuery, tab: 'accounts' } }">
          Аккаунты
        </router-link>
        <router-link class="tab" :class="{ active: activeTab === 'games' }" :to="{ name: 'work', query: { ...routeQuery, tab: 'games' } }">
          Игры
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
        <router-link
          class="tab tab--icon"
          :class="{ active: activeTab === 'profile' }"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'profile' } }"
          aria-label="Профиль"
          title="Профиль"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4Z" />
            <path d="M4 20a8 8 0 0 1 16 0" />
          </svg>
        </router-link>
        <button
          class="tab tab--icon tab--danger"
          @click="ctx.onLogout"
          aria-label="Выйти"
          title="Выйти"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
            <path d="M10 17l5-5-5-5" />
            <path d="M15 12H3" />
          </svg>
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
const userName = computed(() => unref(props.ctx.userName))
</script>
