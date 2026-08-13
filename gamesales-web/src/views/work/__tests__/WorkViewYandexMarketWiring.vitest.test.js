import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const workViewPath = resolve(process.cwd(), 'src/views/WorkView.vue')

function blockBefore(source, endMarker) {
  // Выделяет ближайший объект перед маркером, чтобы проверить передачу обработчика между слоями формы.
  const end = source.indexOf(endMarker)
  const start = source.lastIndexOf('const {', end)
  return source.slice(start, end)
}

describe('WorkView Yandex Market wiring', () => {
  it('passes the daily limit action from the catalog composable into the products section', () => {
    const source = readFileSync(workViewPath, 'utf8')
    const catalogBindings = blockBefore(source, '} = useYandexMarketCatalog(')
    const productsStart = source.indexOf('const productsSectionCtx = asCtx({')
    const productsEnd = source.indexOf('\n})', productsStart)
    const productsContext = source.slice(productsStart, productsEnd)

    expect(catalogBindings).toContain('addYandexMarketDailyLimitUnits')
    expect(productsContext).toContain('addYandexMarketDailyLimitUnits')
  })
})
