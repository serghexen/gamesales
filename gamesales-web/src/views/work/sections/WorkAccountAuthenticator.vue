<template>
  <div class="account-authenticator field--full">
    <label class="field account-authenticator__code">
      <span class="label">Код аутентификатора</span>
      <input :value="code" class="input" placeholder="код" :readonly="readonly" @input="$emit('update:code', $event.target.value.trim())" />
    </label>
    <div class="account-authenticator__image">
      <span class="label">QR аутентификатора</span>
      <button v-if="image" type="button" class="account-authenticator__thumbnail" aria-label="Увеличить QR аутентификатора" @click="openPreview">
        <img :src="image" alt="QR аутентификатора" width="88" height="88" />
      </button>
      <span v-else-if="readonly" class="account-authenticator__empty">Не прикреплён</span>
      <div v-if="!readonly" class="account-authenticator__actions">
        <button type="button" class="btn" :disabled="reading" @click="fileInput?.click()">{{ image ? 'Заменить' : 'Прикрепить' }}</button>
        <button v-if="image" type="button" class="btn" :disabled="reading" @click="$emit('update:image', '')">Удалить</button>
        <input ref="fileInput" class="account-authenticator__file" type="file" accept="image/png,image/jpeg,image/webp" aria-label="Прикрепить QR аутентификатора" @change="selectFile" />
        <small>PNG, JPEG, WebP · до 1 МБ</small>
      </div>
      <p v-if="error" class="bad account-authenticator__error" role="alert">{{ error }}</p>
    </div>
    <dialog ref="preview" class="account-authenticator__preview" aria-label="QR аутентификатора" @click="closeOnBackdrop" @keydown.esc.stop.prevent="closePreview">
      <button type="button" class="btn" autofocus @click="closePreview">Закрыть</button>
      <img v-if="previewOpen" :src="image" alt="QR аутентификатора — увеличенное изображение" />
    </dialog>
  </div>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { readAuthenticatorImage } from '../authenticatorImage'

const props = defineProps({ code: { type: String, default: '' }, image: { type: String, default: '' }, readonly: Boolean })
const emit = defineEmits(['update:code', 'update:image', 'loading'])
const fileInput = ref(null)
const preview = ref(null)
const previewOpen = ref(false)
const reading = ref(false)
const error = ref('')
let requestId = 0

async function selectFile(event) {
  // Старый ответ после закрытия карточки или выключения редактирования не меняет изображение.
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || props.readonly || reading.value) return
  const currentRequest = ++requestId
  error.value = ''
  reading.value = true
  emit('loading', true)
  try {
    const result = await readAuthenticatorImage(file)
    if (currentRequest === requestId && !props.readonly) emit('update:image', result)
  } catch (e) {
    if (currentRequest === requestId) error.value = e.message
  } finally {
    if (currentRequest === requestId) {
      reading.value = false
      emit('loading', false)
    }
  }
}

function openPreview() {
  // Нативный dialog удерживает фокус и показывает QR поверх карточки, не меняя её размеры.
  previewOpen.value = true
  preview.value?.showModal()
}

function closePreview() {
  // После закрытия полноразмерное изображение убирается из DOM.
  if (preview.value?.open) preview.value.close()
  previewOpen.value = false
}

function closeOnBackdrop(event) {
  // Клик по самому QR не закрывает просмотр.
  if (event.target === preview.value) closePreview()
}

function cancelReading() {
  // Отменяем применение результата без изменения уже выбранного изображения.
  requestId += 1
  reading.value = false
  emit('loading', false)
}

watch(() => props.readonly, (value) => {
  // При отмене редактирования незавершённая загрузка больше не относится к форме.
  if (value) cancelReading()
})
watch(() => props.image, () => closePreview())
onBeforeUnmount(() => {
  // Закрытие аккаунта очищает просмотр и снимает блокировку чтения файла.
  cancelReading()
  closePreview()
})
</script>

<style scoped>
.account-authenticator { display: grid; grid-template-columns: minmax(0, 1fr) 170px; align-items: start; gap: 16px; min-width: 0; }
.account-authenticator__code { min-width: 0; }
.account-authenticator__image { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; min-width: 0; }
.account-authenticator__thumbnail { width: 96px; height: 96px; box-sizing: border-box; flex: none; padding: 4px; background: #fff; border: 1px solid #64748b; border-radius: 10px; cursor: zoom-in; }
.account-authenticator__thumbnail img { display: block; width: 100%; height: 100%; object-fit: contain; }
.account-authenticator__actions { display: flex; flex-wrap: wrap; gap: 6px; max-width: 100%; }
.account-authenticator__actions .btn { min-width: 0; padding: 6px 10px; font-size: 12px; }
.account-authenticator__actions small, .account-authenticator__empty { font-size: 12px; opacity: .7; }
.account-authenticator__file { display: none; }
.account-authenticator__error { margin: 0; font-size: 12px; overflow-wrap: anywhere; }
.account-authenticator__preview { width: min(640px, 88vw); max-width: 88vw; max-height: 88dvh; box-sizing: border-box; padding: 16px; border: 1px solid #64748b; border-radius: 16px; background: #101827; color: #fff; }
.account-authenticator__preview::backdrop { background: rgb(0 0 0 / .75); }
.account-authenticator__preview img { display: block; margin: 12px auto 0; max-width: 100%; max-height: 68dvh; object-fit: contain; background: #fff; }
@media (max-width: 600px) { .account-authenticator { grid-template-columns: minmax(0, 1fr); } }
</style>
