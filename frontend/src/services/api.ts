const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

function readableErrorDetail(detail: unknown): string | null {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => {
      if (!item || typeof item !== 'object') return null
      const error = item as { loc?: unknown[]; msg?: unknown }
      const field = error.loc?.filter((part) => part !== 'body').at(-1)
      const message = typeof error.msg === 'string' ? error.msg : null
      if (!message) return null
      return field ? `${String(field).replaceAll('_', ' ')}: ${message}` : message
    }).filter((item): item is string => Boolean(item))
    return messages.length ? messages.join(' · ') : null
  }
  if (detail && typeof detail === 'object') {
    const value = detail as { message?: unknown; msg?: unknown }
    if (typeof value.message === 'string') return value.message
    if (typeof value.msg === 'string') return value.msg
  }
  return null
}

async function request<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(
    `${API_BASE_URL}${endpoint}`,
    {
      headers: {
        'Content-Type': 'application/json',
      },
      ...options,
    },
  )

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`

    try {
      const error = await response.json()

      const readable = readableErrorDetail(error.detail)
      if (readable) message = readable
    } catch {
      // Ignore invalid JSON responses
    }

    throw new Error(message)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export function apiGet<T>(
  endpoint: string,
) {
  return request<T>(endpoint)
}

export function apiPost<T>(
  endpoint: string,
  body: unknown,
) {
  return request<T>(endpoint, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function apiPut<T>(
  endpoint: string,
  body: unknown,
) {
  return request<T>(endpoint, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export function apiDelete(
  endpoint: string,
) {
  return request<void>(endpoint, {
    method: 'DELETE',
  })
}

export function apiPatch<T>(endpoint: string, body: unknown = {}) {
  return request<T>(endpoint, { method: 'PATCH', body: JSON.stringify(body) })
}
