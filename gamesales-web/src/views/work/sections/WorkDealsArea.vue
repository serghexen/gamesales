<template>
  <WorkDealsSection :ctx="ctx.dealsSectionCtx">
    <div class="divider"></div>
    <WorkDealEditorModalShell :ctx="ctx.dealEditorModalShellCtx">
      <WorkDealEditorModalBody :ctx="ctx.dealEditorModalBodyCtx">
        <WorkDealEditorForm :ctx="ctx.dealEditorFormCtx" />
      </WorkDealEditorModalBody>
    </WorkDealEditorModalShell>
  </WorkDealsSection>
</template>

<script setup>
import WorkDealsSection from './WorkDealsSection.vue'
import WorkDealEditorModalShell from './WorkDealEditorModalShell.vue'
import WorkDealEditorModalBody from './WorkDealEditorModalBody.vue'
import WorkDealEditorForm from './WorkDealEditorForm.vue'

// Контекст вкладки сделок + модалки сделки.
defineProps({
  ctx: { type: Object, required: true },
})
</script>
