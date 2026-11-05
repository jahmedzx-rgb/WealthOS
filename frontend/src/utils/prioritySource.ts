// A failed refresh must not erase a source's last successfully loaded data.
export function prioritySource<T>(result: PromiseSettledResult<T>, previous: T): T {
  return result.status === 'fulfilled' ? result.value : previous
}
