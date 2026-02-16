<template>
  <WorkUsersSection v-if="ctx.isAdmin" :ctx="ctx.usersSectionCtx" />
</template>

<script setup>
import WorkUsersSection from './WorkUsersSection.vue'

defineProps({
  ctx: { type: Object, required: true },
})
</script>
