import { onBeforeUnmount, onMounted, ref } from 'vue'

// Дает таблице управляемые ширины колонок и drag-ресайз между соседними колонками.
export function useResizableTableColumns({ tableRef, storageKey, columns }) {
  const columnWidths = ref(buildDefaultWidths(columns))
  const resizeState = ref(null)

  // Возвращает inline-стиль для тега col по ключу колонки.
  function getColumnStyle(key) {
    return { width: `${Number(columnWidths.value[key] || 0)}%` }
  }

  // Загружает ширины пользователя из localStorage и нормализует их.
  function readWidths() {
    try {
      const raw = localStorage.getItem(storageKey)
      if (!raw) return
      const parsed = JSON.parse(raw)
      columnWidths.value = normalizeWidths(columns, parsed)
    } catch {
      columnWidths.value = buildDefaultWidths(columns)
    }
  }

  // Сохраняет актуальные ширины колонок для следующего открытия страницы.
  function saveWidths() {
    try {
      localStorage.setItem(storageKey, JSON.stringify(columnWidths.value))
    } catch {
      // Ошибки хранилища не должны ломать работу таблицы.
    }
  }

  // Запоминает старт drag и включает глобальные обработчики движения мыши.
  function startResize(event, columnKey) {
    const index = columns.findIndex((column) => column.key === columnKey)
    if (index < 0 || index >= columns.length - 1) return
    const width = tableRef.value?.getBoundingClientRect?.().width || 0
    if (width <= 0) return
    const leftKey = columns[index].key
    const rightKey = columns[index + 1].key
    resizeState.value = {
      startX: event.clientX,
      tableWidth: width,
      leftKey,
      rightKey,
      initialLeft: columnWidths.value[leftKey],
      initialRight: columnWidths.value[rightKey],
      minLeft: Number(columns[index].minWidth || 0),
      minRight: Number(columns[index + 1].minWidth || 0),
    }
    window.addEventListener('mousemove', onResizeMove)
    window.addEventListener('mouseup', stopResize)
  }

  // Двигает только две соседние колонки, чтобы общая ширина оставалась стабильной.
  function onResizeMove(event) {
    const state = resizeState.value
    if (!state) return
    const delta = ((event.clientX - state.startX) / state.tableWidth) * 100
    let left = state.initialLeft + delta
    let right = state.initialRight - delta
    if (left < state.minLeft) {
      right -= state.minLeft - left
      left = state.minLeft
    }
    if (right < state.minRight) {
      left -= state.minRight - right
      right = state.minRight
    }
    columnWidths.value = {
      ...columnWidths.value,
      [state.leftKey]: left,
      [state.rightKey]: right,
    }
  }

  // Завершает drag и фиксирует новые ширины в хранилище.
  function stopResize() {
    if (!resizeState.value) return
    resizeState.value = null
    saveWidths()
    window.removeEventListener('mousemove', onResizeMove)
    window.removeEventListener('mouseup', stopResize)
  }

  onMounted(() => {
    readWidths()
  })

  onBeforeUnmount(() => {
    stopResize()
  })

  return {
    columnWidths,
    getColumnStyle,
    startResize,
  }
}

// Строит стартовые ширины по конфигу и приводит их сумму к 100%.
function buildDefaultWidths(columns) {
  const raw = {}
  for (const column of columns) raw[column.key] = Number(column.defaultWidth || 0)
  return normalizeWidths(columns, raw)
}

// Приводит ширины к допустимым минимумам и нормализует сумму процентов.
function normalizeWidths(columns, rawInput) {
  const next = {}
  for (const column of columns) {
    const value = Number(rawInput?.[column.key] ?? column.defaultWidth ?? 0)
    const minWidth = Number(column.minWidth || 0)
    next[column.key] = Math.max(minWidth, value)
  }
  const total = columns.reduce((sum, column) => sum + next[column.key], 0)
  if (!total) {
    return columns.reduce((acc, column) => {
      acc[column.key] = Number(column.defaultWidth || 0)
      return acc
    }, {})
  }
  for (const column of columns) {
    next[column.key] = (next[column.key] / total) * 100
  }
  return next
}
