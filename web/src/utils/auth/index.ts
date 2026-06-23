/**
 * Auth cache utilities — localStorage wrappers with JSON parse/stringify
 */
export function getCache<T = any>(key: string): T | null {
  const raw = localStorage.getItem(key)
  if (!raw) return null
  try {
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

export function setCache(key: string, value: any): void {
  localStorage.setItem(key, JSON.stringify(value))
}

export function removeCache(key: string): void {
  localStorage.removeItem(key)
}
