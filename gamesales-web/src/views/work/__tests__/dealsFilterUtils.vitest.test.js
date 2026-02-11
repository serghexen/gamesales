import { describe, it, expect } from 'vitest'

import { parseResponsibleFilterQuery, stringifyResponsibleFilterQuery } from '../dealsFilterUtils.js'

describe('dealsFilterUtils', () => {
  it('parseResponsibleFilterQuery splits and trims values', () => {
    expect(parseResponsibleFilterQuery(' Иван , Петр,  ,Ольга ')).toEqual(['Иван', 'Петр', 'Ольга'])
    expect(parseResponsibleFilterQuery('')).toEqual([])
  })

  it('stringifyResponsibleFilterQuery joins unique normalized values', () => {
    expect(stringifyResponsibleFilterQuery([' Иван ', 'Петр', 'Иван', '', null])).toBe('Иван,Петр')
    expect(stringifyResponsibleFilterQuery([])).toBe('')
  })
})
