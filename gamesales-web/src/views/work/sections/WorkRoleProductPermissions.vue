<template>
  <details class="role-access-group role-active-deals">
    <summary class="role-access-group__summary">
      <span>{{ groupName }}</span>
      <small v-if="groupDescription">{{ groupDescription }}</small>
    </summary>

    <details class="role-active-deals__panel">
      <summary>Список товаров</summary>
      <div class="role-active-deals__chips">
        <label
          v-for="column in listColumns"
          :key="column.key"
          class="check-item role-active-deals__chip"
        >
          <input
            type="checkbox"
            :checked="canAction(column.action)"
            :disabled="disabled"
            @change="setAction(column.action, $event.target.checked)"
          />
          <span>{{ column.label }}</span>
        </label>
      </div>
    </details>

    <details class="role-active-deals__panel">
      <summary>Операции</summary>
      <div class="role-active-deals__ops">
        <label
          v-for="action in contextActions"
          :key="action.action"
          class="check-item role-active-deals__chip"
        >
          <input
            type="checkbox"
            :checked="canAction(action.action)"
            :disabled="disabled"
            @change="setAction(action.action, $event.target.checked)"
          />
          <span>{{ action.label }}</span>
        </label>
      </div>
    </details>

    <details class="role-active-deals__panel role-active-deals__panel--fields">
      <summary>
        <span>Поля формы</span>
        <span class="role-active-deals__summary-count">{{ enabledFieldCount }}/{{ totalFieldCount }}</span>
      </summary>
      <div class="role-active-deals__matrix-wrap">
        <table class="role-active-deals__matrix role-active-deals__matrix--accounts">
          <thead>
            <tr>
              <th>Поле</th>
              <th v-for="context in contexts" :key="context.key">{{ context.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="field in fields" :key="field.key">
              <td>{{ field.label }}</td>
              <td v-for="context in contexts" :key="`${field.key}-${context.key}`">
                <template v-if="field.contexts.includes(context.key)">
                  <input
                    type="checkbox"
                    :checked="canAction(fieldAction(context.key, field.key))"
                    :disabled="disabled"
                    :aria-label="`${field.label}: ${context.label}`"
                    @change="setAction(fieldAction(context.key, field.key), $event.target.checked)"
                  />
                  <span
                    v-if="isRequiredField(field, context.key)"
                    class="role-active-deals__required-badge"
                    title="Обязательное поле"
                  >
                    обяз.
                  </span>
                </template>
                <span v-else class="muted">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </details>
  </details>
</template>

<script setup>
import { computed } from 'vue'
import {
  PRODUCT_CONTEXT_ACTIONS,
  PRODUCT_CONTEXTS,
  PRODUCT_FIELD_GROUPS,
  PRODUCT_LIST_COLUMNS,
  productFieldAction,
} from '../productPermissions.js'

const props = defineProps({
  groupName: { type: String, default: 'Товары' },
  groupDescription: { type: String, default: '' },
  items: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
  setAction: { type: Function, required: true },
})

const contexts = PRODUCT_CONTEXTS
const contextActions = PRODUCT_CONTEXT_ACTIONS
const listColumns = PRODUCT_LIST_COLUMNS
const fields = PRODUCT_FIELD_GROUPS.flatMap((group) => group.fields)
const totalFieldCount = computed(() => fields.reduce((sum, field) => sum + field.contexts.length, 0))
const enabledFieldCount = computed(() => {
  return fields.reduce((sum, field) => {
    return sum + field.contexts.filter((contextKey) => canAction(fieldAction(contextKey, field.key))).length
  }, 0)
})

function actionItem(actionCode) {
  // Ищем право товара в загруженной роли, чтобы матрица показывала сохраненное состояние.
  const code = String(actionCode || '').trim()
  return props.items.find((item) => String(item?.action_code || '') === code)
}

function canAction(actionCode) {
  return Boolean(actionItem(actionCode)?.can_do)
}

function fieldAction(contextKey, fieldKey) {
  return productFieldAction(contextKey, fieldKey)
}

function isRequiredField(field, contextKey) {
  // Показывает подсказку обязательности в конкретной ячейке поля и контекста.
  return Array.isArray(field?.requiredContexts) && field.requiredContexts.includes(contextKey)
}
</script>
