/**
 * Tasks API module
 * Requirements: 3.3, 3.4, 3.5
 */

import api from './index'

// Types
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface TaskStatusResponse {
  task_id: string
  task_type: string
  status: TaskStatus
  progress: number
  current: number
  total: number
  message: string
  error?: string | null
  created_at: string
  updated_at: string
}

// API functions

/**
 * Get task status by ID
 */
export async function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const response = await api.get<TaskStatusResponse>(`/tasks/${taskId}`)
  return response.data
}

/**
 * Poll task status until completion or failure
 * @param taskId - The task ID to poll
 * @param onProgress - Callback for progress updates
 * @param interval - Polling interval in milliseconds (default: 1000)
 * @param maxRetries - Maximum number of consecutive errors before giving up (default: 3)
 * @returns Final task status
 */
export async function pollTaskStatus(
  taskId: string,
  onProgress?: (task: TaskStatusResponse) => void,
  interval: number = 1000,
  maxRetries: number = 3
): Promise<TaskStatusResponse> {
  let consecutiveErrors = 0
  
  while (true) {
    try {
      const task = await getTaskStatus(taskId)
      consecutiveErrors = 0  // Reset on success
      
      if (onProgress) {
        onProgress(task)
      }
      
      if (task.status === 'completed' || task.status === 'failed') {
        return task
      }
      
      // Wait before next poll
      await new Promise(resolve => setTimeout(resolve, interval))
    } catch (error: any) {
      consecutiveErrors++
      console.error(`Task polling error (attempt ${consecutiveErrors}/${maxRetries}):`, error)
      
      // If task not found, return a failed status
      if (error.response?.status === 404) {
        return {
          task_id: taskId,
          task_type: 'unknown',
          status: 'failed',
          progress: 0,
          current: 0,
          total: 0,
          message: '任务已丢失，可能是服务器重启导致',
          error: '任务不存在，请重新生成',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }
      }
      
      // If too many consecutive errors, give up
      if (consecutiveErrors >= maxRetries) {
        return {
          task_id: taskId,
          task_type: 'unknown',
          status: 'failed',
          progress: 0,
          current: 0,
          total: 0,
          message: '获取任务状态失败',
          error: error.message || '网络错误',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }
      }
      
      // Wait before retry
      await new Promise(resolve => setTimeout(resolve, interval))
    }
  }
}
