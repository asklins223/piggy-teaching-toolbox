/**
 * Emotions API module
 * Requirements: 7.3
 */

import api from './index'

// Types
export interface EmotionInfo {
  id: string
  value: string
  name: string
  category: string
}

export interface EmotionCategoryInfo {
  id: string
  name: string
  emotions: EmotionInfo[]
}

export interface EmotionListResponse {
  emotions: EmotionInfo[]
  categories: EmotionCategoryInfo[]
}

// API functions

/**
 * Get all available emotions with their categories
 */
export async function getEmotions(): Promise<EmotionListResponse> {
  const response = await api.get<EmotionListResponse>('/emotions')
  return response.data
}
