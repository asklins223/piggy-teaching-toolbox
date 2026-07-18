import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'
import { ElMessage, ElNotification } from 'element-plus'

// Error code to Chinese message mapping
const ERROR_MESSAGES: Record<string, string> = {
  UNAUTHORIZED: '未授权，请重新登录',
  FORBIDDEN: '没有权限访问',
  PROJECT_NOT_FOUND: '项目不存在',
  SCENE_NOT_FOUND: '分镜不存在',
  CHARACTER_NOT_FOUND: '角色不存在',
  TASK_NOT_FOUND: '任务不存在',
  RESOURCE_NOT_FOUND: '资源不存在',
  INVALID_REQUEST: '请求参数无效',
  VALIDATION_ERROR: '数据验证失败',
  GENERATION_FAILED: 'AI 生成失败',
  CHARACTER_GENERATION_FAILED: '角色生成失败',
  SCRIPT_PLANNING_FAILED: '分镜脚本生成失败',
  IMAGE_GENERATION_FAILED: '图片生成失败',
  AUDIO_GENERATION_FAILED: '音频生成失败',
  SUBTITLE_GENERATION_FAILED: '字幕生成失败',
  EXPORT_FAILED: '导出失败',
  PROJECT_STATE_ERROR: '项目状态错误',
  STORAGE_ERROR: '存储错误',
  RETRY_EXHAUSTED: '操作重试次数已耗尽',
  AI_ERROR: 'AI 服务调用失败',
  INTERNAL_ERROR: '服务器内部错误',
}

// Error response interface
interface ApiErrorDetail {
  code: string
  message: string
}

interface ApiErrorResponse {
  error: ApiErrorDetail
}

/**
 * Extract error message from API response
 */
function extractErrorMessage(error: AxiosError): string {
  const response = error.response
  
  if (!response) {
    // Network error
    if (error.code === 'ECONNABORTED') {
      return '请求超时，请检查网络连接'
    }
    return '网络连接失败，请检查网络'
  }
  
  const data = response.data as ApiErrorResponse | { detail?: string | ApiErrorDetail } | undefined
  
  // Try to extract from standardized error format
  if (data && typeof data === 'object') {
    // Format: { error: { code, message } }
    if ('error' in data && data.error) {
      const errorDetail = data.error as ApiErrorDetail
      // Use the message from response, or fallback to mapped message
      return errorDetail.message || ERROR_MESSAGES[errorDetail.code] || '请求失败'
    }
    
    // Format: { detail: { code, message } } (FastAPI HTTPException)
    if ('detail' in data && data.detail) {
      if (typeof data.detail === 'object' && 'message' in data.detail) {
        return (data.detail as ApiErrorDetail).message
      }
      if (typeof data.detail === 'string') {
        return data.detail
      }
    }
  }
  
  // Fallback based on status code
  const statusMessages: Record<number, string> = {
    400: '请求参数错误',
    401: '未授权，请重新登录',
    403: '没有权限访问',
    404: '请求的资源不存在',
    422: '数据验证失败',
    500: '服务器内部错误',
    502: '网关错误',
    503: '服务暂时不可用',
  }
  
  return statusMessages[response.status] || `请求失败 (${response.status})`
}

/**
 * Extract error code from API response
 */
function extractErrorCode(error: AxiosError): string | null {
  const response = error.response
  if (!response) return null
  
  const data = response.data as ApiErrorResponse | { detail?: ApiErrorDetail } | undefined
  
  if (data && typeof data === 'object') {
    if ('error' in data && data.error && 'code' in data.error) {
      return data.error.code
    }
    if ('detail' in data && data.detail && typeof data.detail === 'object' && 'code' in data.detail) {
      return data.detail.code
    }
  }
  
  return null
}

// 创建 Axios 实例
const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器：添加 Token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器：处理 401 和错误
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    const errorCode = extractErrorCode(error)
    const errorMessage = extractErrorMessage(error)
    
    if (error.response?.status === 401) {
      // 清除 token 并跳转登录页
      localStorage.removeItem('token')
      
      // Show notification for unauthorized
      ElNotification({
        title: '登录已过期',
        message: '请重新登录',
        type: 'warning',
        duration: 3000,
      })
      
      // Redirect to login page
      setTimeout(() => {
        window.location.href = '/login'
      }, 1000)
    } else {
      // Show error message based on severity
      const isServerError = error.response?.status && error.response.status >= 500
      
      if (isServerError) {
        // Use notification for server errors (more prominent)
        ElNotification({
          title: '服务器错误',
          message: errorMessage,
          type: 'error',
          duration: 5000,
        })
      } else {
        // Use message for client errors
        ElMessage.error(errorMessage)
      }
    }
    
    // Attach parsed error info to the error object for consumers
    ;(error as any).errorCode = errorCode
    ;(error as any).errorMessage = errorMessage
    
    return Promise.reject(error)
  }
)

export default api

// 导出类型和工具函数
export type { AxiosRequestConfig, AxiosResponse, ApiErrorDetail, ApiErrorResponse }
export { extractErrorMessage, extractErrorCode, ERROR_MESSAGES }
