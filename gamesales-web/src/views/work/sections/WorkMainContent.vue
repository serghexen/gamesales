<template>
  <main class="main">
    <WorkDashboardPanel
      v-if="showDashboard && activeTab === 'dashboard'"
      :ctx="props.ctx.dashboardSectionCtx"
    />

    <WorkProfileSection
      v-if="activeTab === 'profile'"
      :ctx="props.ctx.profileSectionCtx"
    />

    <WorkAccountsSection
      v-if="activeTab === 'accounts'"
      :ctx="props.ctx.accountsSectionCtx"
    />

    <WorkProductsSection
      v-if="activeTab === 'products'"
      :ctx="props.ctx.productsSectionCtx"
    />

    <WorkTelegramSection
      v-if="activeTab === 'telegram'"
      :ctx="props.ctx.telegramSectionCtx"
    />

    <WorkDealsArea
      v-if="activeTab === 'deals'"
      :ctx="props.ctx.dealsAreaCtx"
    />

    <WorkCatalogsSection
      v-if="isAdmin && activeTab === 'catalogs'"
      :ctx="props.ctx.catalogsSectionCtx"
    />

    <WorkUsersSection
      v-if="isAdmin && activeTab === 'users'"
      :ctx="props.ctx.usersSectionCtx"
    />
  </main>
</template>

<script setup>
import { computed, unref } from 'vue'
import WorkDashboardPanel from './WorkDashboardPanel.vue'
import WorkProfileSection from './WorkProfileSection.vue'
import WorkAccountsSection from './WorkAccountsSection.vue'
import WorkProductsSection from './WorkProductsSection.vue'
import WorkTelegramSection from './WorkTelegramSection.vue'
import WorkDealsArea from './WorkDealsArea.vue'
import WorkCatalogsSection from './WorkCatalogsSection.vue'
import WorkUsersSection from './WorkUsersSection.vue'

// Единый контекст для всех вкладок внутри центральной области страницы.
const props = defineProps({
  ctx: { type: Object, required: true },
})

const activeTab = computed(() => unref(props.ctx.activeTab))
const showDashboard = computed(() => unref(props.ctx.showDashboard))
const isAdmin = computed(() => unref(props.ctx.isAdmin))
</script>
