import { computed, reactive, ref } from 'vue'

export function useModalDrag() {
  const modalRef = ref(null)
  const modalPos = reactive({ x: 0, y: 0 })
  const modalDragging = ref(false)
  const modalDragStart = reactive({ x: 0, y: 0 })
  const modalBase = reactive({ left: 0, top: 0, width: 0, height: 0 })
  const modalPadding = 16

  const modalStyle = computed(() => ({
    transform: `translate(${modalPos.x}px, ${modalPos.y}px)`,
  }))

  const resetModalPos = () => {
    modalPos.x = 0
    modalPos.y = 0
  }

  const onModalDrag = (event) => {
    if (!modalDragging.value) return
    const nextX = event.clientX - modalDragStart.x
    const nextY = event.clientY - modalDragStart.y
    const minX = modalPadding - modalBase.left
    const maxX = window.innerWidth - modalPadding - (modalBase.left + modalBase.width)
    const minY = modalPadding - modalBase.top
    const maxY = window.innerHeight - modalPadding - (modalBase.top + modalBase.height)
    modalPos.x = Math.min(Math.max(nextX, minX), maxX)
    modalPos.y = Math.min(Math.max(nextY, minY), maxY)
  }

  const stopModalDrag = () => {
    modalDragging.value = false
    window.removeEventListener('mousemove', onModalDrag)
    window.removeEventListener('mouseup', stopModalDrag)
  }

  const startModalDrag = (event) => {
    if (event.button !== 0) return
    const rect = modalRef.value?.getBoundingClientRect()
    if (!rect) return
    modalBase.left = rect.left - modalPos.x
    modalBase.top = rect.top - modalPos.y
    modalBase.width = rect.width
    modalBase.height = rect.height
    modalDragging.value = true
    modalDragStart.x = event.clientX - modalPos.x
    modalDragStart.y = event.clientY - modalPos.y
    window.addEventListener('mousemove', onModalDrag)
    window.addEventListener('mouseup', stopModalDrag)
  }

  return {
    modalRef,
    modalStyle,
    resetModalPos,
    startModalDrag,
    onModalDrag,
    stopModalDrag,
  }
}
