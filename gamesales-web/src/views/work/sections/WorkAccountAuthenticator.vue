<template>
  <div class="account-authenticator field--full">
    <label class="field account-authenticator__code">
      <span class="label">Код аутентификатора</span>
      <input :value="code" class="input" placeholder="код" :readonly="readonly" @input="$emit('update:code', $event.target.value.trim())" />
    </label>
    <div class="account-authenticator__image" role="group" aria-label="QR аутентификатора" @paste="pasteImage">
      <span class="label">QR аутентификатора</span>
      <button v-if="image" type="button" class="account-authenticator__thumbnail" aria-label="Увеличить QR аутентификатора" @click="openPreview">
        <img :src="image" alt="QR аутентификатора" width="88" height="88" />
      </button>
      <span v-else-if="readonly" class="account-authenticator__empty">Не прикреплён</span>
      <div v-if="!readonly" class="account-authenticator__actions">
        <div class="account-authenticator__paste-row">
          <input class="input account-authenticator__paste" type="text" value="" placeholder="Ctrl+V / ⌘V" aria-label="Вставить изображение QR из буфера" title="Нажмите на поле и вставьте изображение: Ctrl+V / ⌘V" autocomplete="off" :disabled="reading" @beforeinput.prevent @input="clearPasteText" />
          <button type="button" class="btn--ghost account-authenticator__action account-authenticator__attach" :disabled="reading" :aria-label="image ? 'Заменить QR файлом' : 'Прикрепить QR файлом'" :title="image ? 'Заменить QR файлом' : 'Прикрепить QR файлом'" @click="fileInput?.click()">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m21 11-8.5 8.5a6 6 0 0 1-8.5-8.5l9-9a4 4 0 0 1 5.7 5.7l-9 9a2 2 0 0 1-2.8-2.8L15 6" /></svg>
          </button>
        </div>
        <button v-if="image" type="button" class="btn--ghost account-authenticator__action" :disabled="reading" @click="$emit('update:image', '')">Удалить</button>
        <input ref="fileInput" class="account-authenticator__file" type="file" accept="image/png,image/jpeg,image/webp" aria-label="Прикрепить QR аутентификатора" @change="selectFile" />
        <small>PNG, JPEG, WebP · до 15 МБ</small>
      </div>
      <p v-if="error" class="bad account-authenticator__error" role="alert">{{ error }}</p>
    </div>
    <dialog ref="preview" class="account-authenticator__preview" aria-label="QR аутентификатора" @click="closeOnBackdrop" @keydown.esc.stop.prevent="closePreview">
      <div class="modal__head account-authenticator__preview-head">
        <button type="button" class="btn btn--icon-plain btn--icon-round deal-create-action-btn deal-create-action-btn--close" aria-label="Закрыть" title="Закрыть" autofocus @click="closePreview">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 6l12 12M18 6l-12 12" />
          </svg>
        </button>
      </div>
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

function selectFile(event) {
  // Повторный выбор того же файла проходит общую проверку, как и вставка из буфера.
  const file = event.target.files?.[0]
  event.target.value = ''
  return attachImage(file)
}

function pasteImage(event) {
  // Перехватываем только изображение внутри блока QR; вставку текста не меняем.
  if (props.readonly || reading.value) return
  const clipboard = event.clipboardData
  const item = Array.from(clipboard?.items || []).find((entry) => entry.kind === 'file' && entry.type.startsWith('image/'))
  const file = item?.getAsFile() || Array.from(clipboard?.files || []).find((entry) => entry.type.startsWith('image/'))
  if (!file) {
    // Поле принимает изображение, а не путь или ссылку; остальные текстовые поля не затрагиваем.
    if (event.target.classList.contains('account-authenticator__paste')) {
      event.preventDefault()
      error.value = 'В буфере нет изображения. Скопируйте само изображение или выберите файл через скрепку.'
    }
    return
  }
  event.preventDefault()
  return attachImage(file, { fromClipboard: true })
}

function clearPasteText(event) {
  // Не оставляем набранный текст или путь в поле, предназначенном для вставки изображения.
  event.target.value = ''
}

async function attachImage(file, options) {
  // Оба способа проверяют файл одинаково; поздний ответ после отмены не меняет карточку.
  if (!file || props.readonly || reading.value) return
  const currentRequest = ++requestId
  error.value = ''
  reading.value = true
  emit('loading', true)
  try {
    const result = await readAuthenticatorImage(file, options)
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
.account-authenticator { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 220px); align-items: start; gap: 16px; min-width: 0; }
.account-authenticator__code { min-width: 0; }
.account-authenticator__image { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; min-width: 0; }
.account-authenticator__thumbnail { width: 96px; height: 96px; box-sizing: border-box; flex: none; padding: 4px; background: #fff; border: 1px solid #64748b; border-radius: 10px; cursor: zoom-in; }
.account-authenticator__thumbnail img { display: block; width: 100%; height: 100%; object-fit: contain; }
.account-authenticator__actions { display: flex; flex-wrap: wrap; gap: 6px; width: 100%; min-width: 0; }
.account-authenticator__paste-row { display: grid; grid-template-columns: minmax(0, 1fr) 36px; gap: 6px; width: 100%; }
.account-authenticator .account-authenticator__paste { min-width: 0; width: 100%; height: 36px; padding: 0 10px; font-size: 12px; border-radius: 10px; }
.account-authenticator .account-authenticator__paste:focus { border-color: var(--ink); box-shadow: 0 0 0 1px var(--input-border); }
/* Общий .btn в компактной форме имеет min-width: 200px; действия QR используют свои размеры. */
.account-authenticator__action { box-sizing: border-box; width: auto; min-width: 0; max-width: 100%; min-height: 32px; padding: 6px 8px; border: 1px solid var(--ghost-border); border-radius: 10px; background: var(--ghost-bg); color: var(--ghost-text); font: inherit; font-size: 12px; line-height: 18px; cursor: pointer; overflow-wrap: anywhere; }
.account-authenticator__action:hover:not(:disabled) { filter: brightness(1.15); }
.account-authenticator__action:disabled { opacity: .55; cursor: not-allowed; }
.account-authenticator__action.account-authenticator__attach { display: grid; place-items: center; width: 36px; height: 36px; padding: 0; }
.account-authenticator__attach svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.account-authenticator__action:focus-visible, .account-authenticator__thumbnail:focus-visible { outline: 2px solid var(--ink, #fff); outline-offset: 2px; }
.account-authenticator__actions small, .account-authenticator__empty { font-size: 12px; opacity: .7; }
.account-authenticator__actions small { flex-basis: 100%; overflow-wrap: anywhere; }
.account-authenticator__file { display: none; }
.account-authenticator__error { margin: 0; font-size: 12px; overflow-wrap: anywhere; }
.account-authenticator__preview { width: min(640px, 88vw); max-width: 88vw; max-height: 88dvh; box-sizing: border-box; padding: 16px; border: 1px solid #64748b; border-radius: 16px; background: #101827; color: #fff; }
.account-authenticator__preview::backdrop { background: rgb(0 0 0 / .75); }
.account-authenticator__preview .account-authenticator__preview-head { display: flex; justify-content: flex-end; margin: 0; padding: 0; cursor: default; }
.account-authenticator__preview img { display: block; margin: 12px auto 0; max-width: 100%; max-height: min(68dvh, calc(88dvh - 88px)); object-fit: contain; background: #fff; }
@media (max-width: 600px) { .account-authenticator { grid-template-columns: minmax(0, 1fr); } }
</style>
