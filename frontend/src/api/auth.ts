/**
 * Authentication API module
 * Requirements: 3.0
 */

import api from './index'

// Types
export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  token: string
  expires_at: string
}

export interface UserResponse {
  username: string
}

export interface LogoutResponse {
  success: boolean
}

// API functions

/**
 * Login with username and password
 */
export async function login(username: string, password: string): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>('/auth/login', {
    username,
    password
  })
  return response.data
}

/**
 * Logout current user
 */
export async function logout(): Promise<LogoutResponse> {
  const response = await api.post<LogoutResponse>('/auth/logout')
  return response.data
}

/**
 * Get current authenticated user info
 */
export async function getCurrentUser(): Promise<UserResponse> {
  const response = await api.get<UserResponse>('/auth/me')
  return response.data
}
