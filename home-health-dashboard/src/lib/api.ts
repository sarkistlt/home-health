/**
 * API utility for making authenticated requests to the backend.
 *
 * Uses NEXT_PUBLIC_API_URL environment variable.
 * Falls back to production URL or localhost based on environment.
 */

// Production API URL
const PRODUCTION_API_URL = 'https://backend-production-5b1d.up.railway.app'
const DEVELOPMENT_API_URL = 'http://localhost:8000'

/**
 * Get the base API URL.
 * Checks env var first, then detects production vs development.
 */
export function getApiUrl(): string {
  // First check for explicit env var
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL
  }

  // In browser, check if we're on production domain
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      return PRODUCTION_API_URL
    }
  }

  // Default to localhost for development
  return DEVELOPMENT_API_URL
}

/**
 * Make an authenticated API request.
 * Automatically includes the auth token from localStorage.
 */
export async function apiFetch(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const baseUrl = getApiUrl()
  const url = `${baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`

  // Get auth token if available (client-side only)
  let token: string | null = null
  if (typeof window !== 'undefined') {
    token = localStorage.getItem('auth_token')
  }

  const headers = new Headers(options.headers)

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json')
  }

  return fetch(url, {
    ...options,
    headers,
  })
}

export default apiFetch
