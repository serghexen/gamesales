<template>
  <details class="role-access-group role-active-deals">
    <summary class="role-access-group__summary">
      <span>{{ groupName }}</span>
      <small v-if="groupDescription">{{ groupDescription }}</small>
    </summary>

    <details v-if="showListPanel" class="role-active-deals__panel">
      <summary>Список сделок</summary>
      <div class="role-active-deals__chips">
        <label
          v-for="column in listColumns"
          :key="column.action"
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
          :class="{ 'role-active-deals__chip--new-row': startsNewOperationRow(action) }"
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
        <table class="role-active-deals__matrix">
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
                <template v-if="fieldContexts(field).includes(context.key)">
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
  ACTIVE_DEAL_FIELD_GROUPS,
  dealFieldAction,
  dealListColumns,
  dealPermissionActions,
  dealPermissionContexts,
} from '../dealActivePermissions.js'

const props = defineProps({
  groupCode: { type: String, default: 'deals_active' },
  groupName: { type: String, default: 'Активные сделки' },
  groupDescription: { type: String, default: '' },
  items: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
  setAction: { type: Function, required: true },
})

const contexts = computed(() => dealPermissionContexts(props.groupCode))
const contextActions = computed(() => dealPermissionActions(props.groupCode))
const listColumns = computed(() => dealListColumns(props.groupCode))
const showListPanel = computed(() => props.groupCode !== 'deals_draft')
const fields = ACTIVE_DEAL_FIELD_GROUPS.flatMap((group) => group.fields)
const contextKeys = computed(() => new Set(contexts.value.map((context) => context.key)))
const totalFieldCount = computed(() => fields.reduce((sum, field) => sum + fieldContexts(field).length, 0))
const enabledFieldCount = computed(() => {
  return fields.reduce((sum, field) => {
    return sum + fieldContexts(field).filter((contextKey) => canAction(fieldAction(contextKey, field.key))).length
  }, 0)
})

function actionItem(actionCode) {
  // Ищем action в списке роли, чтобы матрица показывала сохраненное значение.
  const code = String(actionCode || '').trim()
  return props.items.find((item) => String(item?.action_code || '') === code)
}

function canAction(actionCode) {
  return Boolean(actionItem(actionCode)?.can_do)
}

function fieldAction(contextKey, fieldKey) {
  return dealFieldAction(props.groupCode, contextKey, fieldKey)
}

function fieldContexts(field) {
  // Оставляем в матрице только те контексты, которые существуют у текущей группы сделок.
  return (field?.contexts || []).filter((contextKey) => contextKeys.value.has(contextKey))
}

function isRequiredField(field, contextKey) {
  // Показывает подсказку обязательности в конкретной ячейке поля и контекста.
  return Array.isArray(field?.requiredContexts) && field.requiredContexts.includes(contextKey)
}

function startsNewOperationRow(action) {
  // Первый action шеринга переносим на новую строку, чтобы операции читались двумя блоками.
  return props.groupCode === 'deals_active' && String(action?.action || '') === 'deals_active.new.rental.create'
}
</script>
