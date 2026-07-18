/**
 * Export API module
 * Requirements: 3.5
 */

import api from './index'

// Types
export interface ExportResponse {
  task_id: string
}

export interface ExportStatusResponse {
  project_id: string
  has_export: boolean
  download_url?: string | null
  file_count?: number | null
  zip_size?: number | null
}

// API functions

/**
 * Export all assets for a project
 */
export async function exportProject(projectId: string): Promise<ExportResponse> {
  const response = await api.post<ExportResponse>(`/projects/${projectId}/export`)
  return response.data
}

/**
 * Get export status for a project
 */
export async function getExportStatus(projectId: string): Promise<ExportStatusResponse> {
  const response = await api.get<ExportStatusResponse>(`/projects/${projectId}/export/status`)
  return response.data
}

/**
 * Download the exported ZIP file
 */
export async function downloadExport(projectId: string): Promise<void> {
  const status = await getExportStatus(projectId)
  
  if (status.download_url) {
    window.open(status.download_url, '_blank')
  } else {
    throw new Error('导出文件不存在')
  }
}
