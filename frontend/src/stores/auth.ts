import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  // State - 从 localStorage 恢复
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!token.value)

  // Actions
  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  function setUsername(name: string) {
    username.value = name
    localStorage.setItem('username', name)
  }

  async function login(user: string, password: string): Promise<boolean> {
    loading.value = true
    error.value = null
    
    try {
      const response = await authApi.login(user, password)
      token.value = response.token
      username.value = user
      localStorage.setItem('token', response.token)
      localStorage.setItem('username', user)
      return true
    } catch (err: any) {
      error.value = err.response?.data?.detail?.message || '登录失败'
      return false
    } finally {
      loading.value = false
    }
  }

  async function logout(): Promise<void> {
    try {
      if (token.value) {
        await authApi.logout()
      }
    } catch {
      // Ignore logout errors
    } finally {
      token.value = ''
      username.value = ''
      localStorage.removeItem('token')
      localStorage.removeItem('username')
    }
  }

  async function fetchCurrentUser(): Promise<boolean> {
    if (!token.value) {
      return false
    }
    
    try {
      const response = await authApi.getCurrentUser()
      username.value = response.username
      localStorage.setItem('username', response.username)
      return true
    } catch {
      // Token might be invalid
      token.value = ''
      username.value = ''
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      return false
    }
  }

  function clearError() {
    error.value = null
  }

  return { 
    // State
    token, 
    username, 
    loading,
    error,
    // Getters
    isAuthenticated,
    // Actions
    setToken, 
    setUsername, 
    login,
    logout,
    fetchCurrentUser,
    clearError
  }
})
