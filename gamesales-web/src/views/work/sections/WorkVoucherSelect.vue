<template>
  <button ref="trigger" v-bind="$attrs" type="button" class="input voucher-supplier-picker" role="combobox" :aria-label="label" aria-haspopup="listbox"
    :aria-expanded="open" :aria-controls="open ? listId : undefined" :aria-activedescendant="open ? `${listId}-${activeIndex}` : undefined"
    :disabled="disabled || !selectable.length" @click="toggle" @keydown="onKeydown">
    <span>{{ options.find((item) => item.code === modelValue)?.name || placeholder }}</span>
    <svg viewBox="0 0 20 20" aria-hidden="true" :class="{ 'is-open': open }"><path d="m6 8 4 4 4-4" /></svg>
  </button>
  <teleport to="body">
    <div v-if="open" :id="listId" ref="menu" class="voucher-supplier-menu" :style="menuStyle" role="listbox" :aria-label="label">
      <div v-for="(option, index) in options" :id="`${listId}-${index}`" :key="option.code" role="option" :aria-selected="option.code === modelValue"
        :aria-disabled="Boolean(option.disabled)" class="voucher-supplier-menu__option" :class="{ 'is-active': index === activeIndex }" @pointermove="!option.disabled && (activeIndex = index)" @mousedown.prevent @click="choose(index)">
        <span>{{ option.name }}</span><svg v-if="option.code === modelValue" viewBox="0 0 20 20" aria-hidden="true"><path d="m4 10 4 4 8-8" /></svg>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
defineOptions({ inheritAttrs: false })
const props = defineProps({ label: { type: String, default: 'Поставщик' }, placeholder: { type: String, default: 'Выберите поставщика' }, modelValue: { type: String, default: '' }, options: { type: Array, default: () => [] }, disabled: Boolean })
const emit = defineEmits(['update:modelValue', 'change'])
const trigger = ref(null)
const menu = ref(null)
const open = ref(false)
const activeIndex = ref(0)
const menuStyle = ref({})
const listId = `voucher-select-${useId()}`
// Недоступные пункты видны с причиной, но пропускаются при навигации и выборе.
const selectable = computed(() => props.options.flatMap((option, index) => option.disabled ? [] : [index]))

function close() {
  // Фокус остаётся на поле, поэтому закрытие меню не нарушает ловушку фокуса модалки.
  open.value = false
}

async function show() {
  // Меню вынесено из прокручиваемой формы: его края совпадают с полем и не обрезаются окном.
  if (props.disabled || !selectable.value.length) return
  const rect = trigger.value.getBoundingClientRect()
  // Teleport меняет родителя: явно переносим шрифт поля, чтобы меню не наследовало шрифт body.
  const font = window.getComputedStyle(trigger.value)
  const gap = 6, edge = 8
  const below = Math.max(0, window.innerHeight - rect.bottom - gap - edge)
  const above = Math.max(0, rect.top - gap - edge)
  const wanted = Math.min(248, props.options.length * 36 + 10)
  const upwards = below < wanted && above > below
  const width = Math.min(rect.width, window.innerWidth - edge * 2)
  menuStyle.value = {
    fontFamily: font.fontFamily || "'Space Grotesk', sans-serif", fontSize: font.fontSize || '13px',
    fontWeight: font.fontWeight || '400', lineHeight: font.lineHeight,
    left: `${Math.max(edge, Math.min(rect.left, window.innerWidth - width - edge))}px`, width: `${width}px`,
    maxHeight: `${Math.min(248, upwards ? above : below)}px`,
    ...(upwards ? { bottom: `${window.innerHeight - rect.top + gap}px` } : { top: `${rect.bottom + gap}px` }),
  }
  const selected = props.options.findIndex((option) => option.code === props.modelValue && !option.disabled)
  activeIndex.value = selected < 0 ? selectable.value[0] : selected
  open.value = true
  await nextTick()
  if (open.value) document.getElementById(`${listId}-${activeIndex.value}`)?.scrollIntoView?.({ block: 'nearest' })
}

function toggle() {
  // Повторный клик по полю закрывает список без изменения поставщика.
  if (open.value) close()
  else show()
}

function choose(index) {
  // Оповещаем форму только при выборе другого значения, чтобы не сбрасывать связанные поля зря.
  const option = props.options[index]
  if (!option || option.disabled || props.disabled) return
  close()
  trigger.value?.focus()
  if (option.code === props.modelValue) return
  emit('update:modelValue', option.code)
  emit('change')
}

async function onKeydown(event) {
  // Стрелки выбирают пункт, Enter подтверждает, а Escape закрывает только список.
  if (event.key === 'Tab') { close(); return }
  if (event.key === 'Escape' && open.value) { event.preventDefault(); event.stopPropagation(); close(); return }
  if (!['ArrowDown', 'ArrowUp', 'Home', 'End', 'Enter', ' '].includes(event.key)) return
  event.preventDefault()
  event.stopPropagation()
  if (!open.value) { show(); return }
  if (event.key === 'Enter' || event.key === ' ') { choose(activeIndex.value); return }
  const indices = selectable.value
  if (!indices.length) { close(); return }
  if (event.key === 'Home') activeIndex.value = indices[0]
  else if (event.key === 'End') activeIndex.value = indices.at(-1)
  else activeIndex.value = indices[(indices.indexOf(activeIndex.value) + (event.key === 'ArrowDown' ? 1 : -1) + indices.length) % indices.length]
  await nextTick()
  document.getElementById(`${listId}-${activeIndex.value}`)?.scrollIntoView?.({ block: 'nearest' })
}

function outside(event) {
  // Клик за меню закрывает его; выбор пункта обрабатывается самим списком.
  if (!trigger.value?.contains(event.target) && !menu.value?.contains(event.target)) close()
}

function onScroll(event) {
  // При прокрутке формы меню закрывается, чтобы не остаться в старой позиции.
  if (!menu.value?.contains(event.target)) close()
}

watch(() => props.disabled, close)
watch(() => props.options, close)
onMounted(() => {
  // Обработчики нужны только пока поле присутствует в форме связки.
  document.addEventListener('pointerdown', outside, true)
  document.addEventListener('scroll', onScroll, true)
  window.addEventListener('resize', close)
})
onBeforeUnmount(() => {
  // Уход из формы убирает меню и все глобальные обработчики.
  document.removeEventListener('pointerdown', outside, true)
  document.removeEventListener('scroll', onScroll, true)
  window.removeEventListener('resize', close)
})
</script>

<style scoped>
.voucher-supplier-picker.input { display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%; text-align: left; font-weight: 400; box-shadow: none; cursor: pointer; }
.voucher-supplier-picker span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.voucher-supplier-picker svg, .voucher-supplier-menu svg { flex: 0 0 auto; width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; }
.voucher-supplier-picker .is-open { transform: rotate(180deg); }
.voucher-supplier-menu { position: fixed; z-index: 2800; box-sizing: border-box; overflow-y: auto; overscroll-behavior: contain; scrollbar-width: thin; padding: 4px; border: 1px solid rgba(160,174,198,.28); border-radius: 10px; background: #111827; color: #e8edf7; box-shadow: 0 10px 28px rgba(0,0,0,.35); font: inherit; }
.voucher-supplier-menu__option { display: flex; align-items: center; justify-content: space-between; gap: 10px; box-sizing: border-box; min-height: 36px; padding: 8px 10px; border-radius: 6px; font-size: inherit; line-height: 1.4; cursor: pointer; }
.voucher-supplier-menu__option.is-active { background: rgba(84,213,173,.12); }
.voucher-supplier-menu__option[aria-selected="true"] { color: #54d5ad; }
.voucher-supplier-menu__option[aria-disabled="true"] { opacity: .45; cursor: default; }
</style>
