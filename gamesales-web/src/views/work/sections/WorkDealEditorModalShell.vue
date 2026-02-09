<template>
  <teleport to="body">
    <div
      v-if="isOpen"
      class="work-page work-modal-root modal-backdrop"
      @click.self="closeModal"
    >
      <div :ref="modalRef" class="modal modal--auto" :style="modalStyle">
        <!-- Шапка модалки сделки: сохранить/создать/редактировать/закрыть -->
        <div class="panel__head panel__head--tight modal__head" @mousedown="startModalDrag">
          <h3>{{ title }}</h3>
          <div class="toolbar-actions">
            <button
              v-if="showSaveEdit"
              class="btn btn--icon-plain"
              type="button"
              aria-label="Сохранить изменения"
              title="Сохранить изменения"
              @click="onSaveEdit"
              :disabled="actionsDisabled"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h12l4 4v12H4z" />
                <path d="M7 4v6h8V4" />
                <path d="M7 20v-6h10v6" />
              </svg>
            </button>
            <button
              v-if="showCreate"
              class="btn btn--icon-plain"
              type="button"
              aria-label="Сохранить сделку"
              title="Сохранить сделку"
              @click="onCreate"
              :disabled="actionsDisabled"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h12l4 4v12H4z" />
                <path d="M7 4v6h8V4" />
                <path d="M7 20v-6h10v6" />
              </svg>
            </button>
            <button
              v-if="showEdit"
              class="btn btn--icon-plain btn--icon-round btn--edit"
              type="button"
              aria-label="Редактировать"
              title="Редактировать"
              @click="onEdit"
              :disabled="editDisabled"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 20h4l10-10-4-4L4 16v4Z" />
                <path d="M13 6l4 4" />
              </svg>
            </button>
            <button
              class="btn btn--icon-plain btn--icon-round"
              type="button"
              aria-label="Закрыть"
              title="Закрыть"
              @click="closeModal"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 6l12 12M18 6l-12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Содержимое формы передаем слотом -->
        <slot />
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { reactive, toRefs } from 'vue'

// Контекст шапки модалки сделки.
const props = defineProps({
  ctx: { type: Object, required: true },
})
const ctx = reactive(props.ctx)

const {
  isOpen,
  closeModal,
  modalRef,
  modalStyle,
  startModalDrag,
  title,
  showSaveEdit,
  showCreate,
  showEdit,
  editDisabled,
  onSaveEdit,
  onCreate,
  onEdit,
  actionsDisabled,
} = toRefs(ctx)
</script>
