<template>
  <section class="panel panel--wide">
    <div class="panel__body">
      <div v-if="ctx.isAdmin" class="tabs profile-admin-links">
        <!-- Переносим вход в аналитику в профиль админа, чтобы не держать вкладку в шапке. -->
        <router-link
          class="tab"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'analytics' } }"
        >
          Аналитика
        </router-link>
        <!-- Переносим справочники в профиль админа, чтобы разгрузить шапку. -->
        <router-link
          class="tab"
          :to="{ name: 'work', query: { ...routeQuery, tab: 'catalogs' } }"
        >
          Справочники
        </router-link>
      </div>
      <WorkUsersSection v-if="ctx.isAdmin" :ctx="ctx.usersSectionCtx" />
    </div>
  </section>
</template>

<script setup>
import { computed, unref } from 'vue'
import WorkUsersSection from './WorkUsersSection.vue'

const props = defineProps({
  ctx: { type: Object, required: true },
})

// Сохраняем текущие query-параметры при переходе в аналитику из профиля.
const routeQuery = computed(() => unref(props.ctx.routeQuery) || {})
</script>
