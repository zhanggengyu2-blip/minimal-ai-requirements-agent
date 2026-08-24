export const reorderVisibleIds = (
  visibleIds: string[],
  draggedId: string,
  targetId: string,
) => {
  const from = visibleIds.indexOf(draggedId)
  const to = visibleIds.indexOf(targetId)
  if (from < 0 || to < 0 || from === to) return [...visibleIds]
  const next = [...visibleIds]
  const [moved] = next.splice(from, 1)
  next.splice(to, 0, moved)
  return next
}

export const mergeVisibleTaskOrder = (fullIds: string[], orderedVisibleIds: string[]) => {
  const visible = new Set(orderedVisibleIds)
  let cursor = 0
  return fullIds.map((taskId) => {
    if (!visible.has(taskId)) return taskId
    return orderedVisibleIds[cursor++] ?? taskId
  })
}
