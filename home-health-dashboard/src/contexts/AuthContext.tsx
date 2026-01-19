'use client'

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { getApiUrl } from '@/lib/api'

const API_URL = getApiUrl()

interface AuthContextType {
  isAuthenticated: boolean
  isLoading: boolean
  username: string | null
  login: (username: string, password: string) => Promise<{ success: boolean; error?: string }>
  logout: () => void
  getAuthToken: () => string | null
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [username, setUsername] = useState<string | null>(null)

  // Check for existing auth on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('auth_token')

      if (!token) {
        setIsLoading(false)
        return
      }

      try {
        const response = await fetch(`${API_URL}/auth/verify`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })

        if (response.ok) {
          const data = await response.json()
          setIsAuthenticated(true)
          setUsername(data.username)
        } else {
          // Token is invalid, clear it
          localStorage.removeItem('auth_token')
          localStorage.removeItem('auth_username')
        }
      } catch {
        // Server unreachable, keep token for retry
        console.error('Auth verification failed')
      }

      setIsLoading(false)
    }

    checkAuth()
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      })

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Login failed' }))
        return { success: false, error: error.detail || 'Invalid credentials' }
      }

      const data = await response.json()

      // Store token and username
      localStorage.setItem('auth_token', data.access_token)
      localStorage.setItem('auth_username', username)

      setIsAuthenticated(true)
      setUsername(username)

      return { success: true }
    } catch (error) {
      console.error('Login error:', error)
      return { success: false, error: 'Unable to connect to server' }
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_username')
    setIsAuthenticated(false)
    setUsername(null)
  }, [])

  const getAuthToken = useCallback(() => {
    return localStorage.getItem('auth_token')
  }, [])

  return (
    <AuthContext.Provider value={{
      isAuthenticated,
      isLoading,
      username,
      login,
      logout,
      getAuthToken
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

// Utility function for making authenticated API calls
export function useAuthFetch() {
  const { getAuthToken, logout } = useAuth()

  const authFetch = useCallback(async (url: string, options: RequestInit = {}) => {
    const token = getAuthToken()

    const headers = new Headers(options.headers)
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }

    const response = await fetch(url, {
      ...options,
      headers,
    })

    // If unauthorized, log the user out
    if (response.status === 401) {
      logout()
      throw new Error('Session expired. Please log in again.')
    }

    return response
  }, [getAuthToken, logout])

  return authFetch
}
