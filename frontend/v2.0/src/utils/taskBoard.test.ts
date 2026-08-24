import { describe, expect, it } from 'vitest'
import { mergeVisibleTaskOrder, reorderVisibleIds } from './taskBoard'

describe('task board ordering', () => {
  it('reorders only the visible subset', () => {
    expect(reorderVisibleIds(['a', 'c', 'e'], 'e', 'a')).toEqual(['e', 'a', 'c'])
  })

  it('merges filtered task order back without moving hidden tasks', () => {
    expect(mergeVisibleTaskOrder(
      ['a', 'b-hidden', 'c', 'd-hidden', 'e'],
      ['e', 'a', 'c'],
    )).toEqual(['e', 'b-hidden', 'a', 'd-hidden', 'c'])
  })

  it('keeps the order unchanged for unknown drag targets', () => {
    expect(reorderVisibleIds(['a', 'b'], 'a', 'missing')).toEqual(['a', 'b'])
  })
})
