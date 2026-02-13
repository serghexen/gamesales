import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, nextTick, ref } from 'vue'

import { useResizableTableColumns } from '../useResizableTableColumns'

const TestTable = defineComponent({
  setup() {
    const tableEl = ref(null)
    const { getColumnStyle, startResize } = useResizableTableColumns({
      tableRef: tableEl,
      storageKey: 'test.columns.v1',
      columns: [
        { key: 'left', defaultWidth: 40, minWidth: 20 },
        { key: 'right', defaultWidth: 60, minWidth: 20 },
      ],
    })

    // Рендерим простую таблицу, чтобы проверить стили и drag ресайзера.
    return () => h('table', { ref: tableEl }, [
      h('colgroup', [
        h('col', { style: getColumnStyle('left') }),
        h('col', { style: getColumnStyle('right') }),
      ]),
      h('thead', [
        h('tr', [
          h('th', [
            'Left',
            h('button', {
              class: 'table-col-resizer',
              onMousedown: (event) => startResize(event, 'left'),
            }),
          ]),
          h('th', 'Right'),
        ]),
      ]),
    ])
  },
})

describe('useResizableTableColumns', () => {
  it('reads saved widths from localStorage', async () => {
    localStorage.setItem('test.columns.v1', JSON.stringify({ left: 30, right: 70 }))
    const wrapper = mount(TestTable)
    await nextTick()

    const widths = wrapper.findAll('col').map((col) => col.attributes('style') || '')
    expect(widths[0]).toContain('30%')
    expect(widths[1]).toContain('70%')
  })

  it('resizes adjacent columns and saves values', async () => {
    localStorage.clear()
    const wrapper = mount(TestTable)
    await nextTick()

    const table = wrapper.find('table').element
    table.getBoundingClientRect = () => ({ width: 1000 })

    await wrapper.find('.table-col-resizer').trigger('mousedown', { clientX: 200 })
    window.dispatchEvent(new MouseEvent('mousemove', { clientX: 300 }))
    window.dispatchEvent(new MouseEvent('mouseup', { clientX: 300 }))
    await nextTick()

    const widths = wrapper.findAll('col').map((col) => col.attributes('style') || '')
    expect(widths[0]).toContain('50%')
    expect(widths[1]).toContain('50%')

    const saved = JSON.parse(localStorage.getItem('test.columns.v1') || '{}')
    expect(saved.left).toBeCloseTo(50, 5)
    expect(saved.right).toBeCloseTo(50, 5)
  })
})
