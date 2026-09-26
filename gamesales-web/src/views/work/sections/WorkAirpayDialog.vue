<template>
  <teleport to="body">
    <div class="work-page work-modal-root modal-backdrop airpay-dialog-backdrop" :class="{ 'airpay-dialog-backdrop--purchase': purchase, 'airpay-dialog-backdrop--history': history }" @click.self="close" @keydown="onKey">
      <section ref="dialog" class="modal modal--auto airpay-dialog" :class="{ 'airpay-dialog--purchase': purchase, 'airpay-dialog--history': history }" role="dialog" aria-modal="true" :aria-label="title" tabindex="-1">
        <header class="modal__head panel__head panel__head--tight">
          <div><p class="supplier-catalog__eyebrow">{{ purchase ? 'Поставщик · подтверждение покупки' : 'Поставщик · Airpay' }}</p><h3>{{ title }}</h3></div>
          <button v-if="purchase || history" class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close" type="button" :disabled="busy" :aria-label="history ? 'Закрыть историю Airpay' : 'Закрыть подтверждение покупки'" title="Закрыть" @click="close"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6l-12 12" /></svg></button>
          <button v-else class="ghost" type="button" :disabled="busy" aria-label="Закрыть окно Airpay" @click="close">Закрыть</button>
        </header>
        <div class="modal__body airpay-dialog__body"><slot /></div>
      </section>
    </div>
  </teleport>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
const props = defineProps({ title: { type: String, required: true }, busy: { type: Boolean, default: false }, purchase: { type: Boolean, default: false }, history: { type: Boolean, default: false } })
const emit = defineEmits(['close'])
const dialog = ref(null)
let previousFocus
function close() {
  // Не закрываем форму во время сетевого шага, чтобы результат остался перед пользователем.
  if (!props.busy) emit('close')
}
function onKey(event) {
  // Escape закрывает окно, а Tab удерживает клавиатуру внутри текущей покупки.
  if (event.key === 'Escape') { event.preventDefault(); close() }
  if (event.key !== 'Tab') return
  const nodes = [...dialog.value.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), summary, a[href], [tabindex="0"]')]
  const current = nodes.indexOf(document.activeElement)
  if (!nodes.length) { event.preventDefault(); dialog.value.focus(); return }
  if ((event.shiftKey && current <= 0) || (!event.shiftKey && (current < 0 || current === nodes.length - 1))) {
    event.preventDefault(); nodes[event.shiftKey ? nodes.length - 1 : 0].focus()
  }
}
onMounted(() => {
  // После открытия фокус переходит в окно, не оставляя управление под модальным слоем.
  previousFocus = document.activeElement
  dialog.value.focus()
})
onBeforeUnmount(() => {
  // Возвращаем пользователя к той услуге, из которой он открыл подготовку.
  if (previousFocus?.isConnected) previousFocus.focus()
})
</script>

<style scoped src="../styles/work-supplier-catalog.css"></style>
<style scoped>
.airpay-dialog-backdrop { z-index: 1100; }
.airpay-dialog { width: min(900px, calc(100vw - 32px)); max-height: 90vh; display: flex; flex-direction: column; }
.airpay-dialog h3 { margin: 0; }
.airpay-dialog__body { overflow-y: auto; padding: 20px; }
.airpay-dialog-backdrop--purchase { --modal-bg: #101626; --modal-text: #f4f7ff; --ink: #f4f7ff; --muted: #b5bfd3; --ghost-bg: rgba(255, 255, 255, .08); --ghost-text: #f4f7ff; --ghost-border: rgba(255, 255, 255, .18); align-items: center; padding: 16px; }
.work-page.work-modal-root.modal-backdrop .airpay-dialog--purchase { width: min(520px, calc(100vw - 32px)); max-width: 520px; min-height: 0; max-height: 90vh; height: auto; padding: 16px; overflow: auto; }
.work-page.work-modal-root.modal-backdrop .airpay-dialog--purchase .modal__head { margin-bottom: 0; padding: 0 0 13px; border-bottom: 1px solid rgba(181, 194, 219, .16); background: transparent; }
.work-page.work-modal-root.modal-backdrop .airpay-dialog--purchase h3 { margin: 0; color: #f4f7ff; font-size: 22px; letter-spacing: -.02em; }
.work-page.work-modal-root.modal-backdrop .airpay-dialog--purchase .airpay-dialog__body { flex: 0 0 auto; overflow: visible; padding: 18px 0 0; }
.airpay-dialog-backdrop--history { --modal-bg: #101626; --modal-text: #f4f7ff; --ink: #f4f7ff; --muted: #b5bfd3; --table-bg: #202838; --table-border: rgba(181,194,219,.22); --input-bg: #0d1320; --input-border: rgba(181,194,219,.28); --ghost-bg: rgba(255,255,255,.08); --ghost-text: #f4f7ff; --ghost-border: rgba(255,255,255,.18); }
.work-page.work-modal-root.modal-backdrop .airpay-dialog--history { width: min(1180px, calc(100vw - 32px)); max-width: 1180px; min-height: 0; height: auto; max-height: min(850px, calc(100dvh - 32px)); padding: 16px; }
.work-page.work-modal-root.modal-backdrop .airpay-dialog--history .modal__head { padding: 0 0 12px; margin-bottom: 0; border-bottom: 1px solid rgba(181,194,219,.16); background: transparent; }
.work-page.work-modal-root.modal-backdrop .airpay-dialog--history h3 { color: #f4f7ff; font-size: 22px; letter-spacing: -.02em; }
.work-page.work-modal-root.modal-backdrop .airpay-dialog--history .airpay-dialog__body { padding: 12px 0 0; min-height: 0; }
@media (max-width: 640px) {
  .work-page.work-modal-root.modal-backdrop .airpay-dialog--history { width: calc(100vw - 16px); max-height: calc(100dvh - 16px); padding: 12px; }
}
</style>
