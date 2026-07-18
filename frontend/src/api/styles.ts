/**
 * Styles API module
 * Requirements: 7.2
 */

import api from './index'

// Types
export interface StyleInfo {
  id: string
  name: string
  description: string
  icon?: string | null
}

export interface StyleListResponse {
  styles: StyleInfo[]
}

// API functions

/**
 * Get all available video styles
 */
export async function getStyles(): Promise<StyleListResponse> {
  const response = await api.get<StyleListResponse>('/styles')
  return response.data
}
