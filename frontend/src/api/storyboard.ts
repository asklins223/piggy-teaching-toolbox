/**
 * Storyboard API module
 * Requirements: 3.3, 7.4
 */

import api from './index'

// Types

/**
 * Audio generation parameters (Requirements: 7.4)
 */
export interface AudioParams {
  emotion?: string
  emotion_strength?: number
  speed?: number
  volume?: number
}

export interface Scene {
  scene_id: string
  step_number: number
  description_cn: string
  // 新增：拆分场景描述
  image_prompt?: string
  video_prompt?: string
  narration_cn: string
  narration_en: string
  duration: number
  emotion: string
  image_url?: string | null
  character_ids: string[]
  // Audio params (Requirements: 7.4)
  audio_params?: AudioParams | null
}

export interface ScenesListResponse {
  scenes: Scene[]
}

export interface GenerateStoryboardRequest {
  duration?: string
  stepwise?: boolean  // 是否使用分步生成模式
}

export interface GenerateStoryboardResponse {
  task_id: string
}

export interface UpdateSceneRequest {
  description_cn?: string
  // 新增：拆分场景描述
  image_prompt?: string
  video_prompt?: string
  narration_cn?: string
  narration_en?: string
  duration?: number
  emotion?: string
  // Audio params (Requirements: 7.4)
  audio_params?: AudioParams
}

export interface UpdateSceneResponse {
  scene: Scene
}

export interface RegenerateImageResponse {
  task_id: string
}

// API functions

/**
 * Generate storyboard script and images for a project
 */
export async function generateStoryboard(
  projectId: string,
  duration: string = '10',
  stepwise: boolean = false
): Promise<GenerateStoryboardResponse> {
  const response = await api.post<GenerateStoryboardResponse>(
    `/projects/${projectId}/storyboard/generate`,
    { duration, stepwise }
  )
  return response.data
}

/**
 * Get list of scenes for a project
 */
export async function getScenes(projectId: string): Promise<ScenesListResponse> {
  const response = await api.get<ScenesListResponse>(`/projects/${projectId}/scenes`)
  return response.data
}

/**
 * Update a scene's content
 */
export async function updateScene(
  projectId: string,
  sceneId: string,
  data: UpdateSceneRequest
): Promise<UpdateSceneResponse> {
  const response = await api.put<UpdateSceneResponse>(
    `/projects/${projectId}/scenes/${sceneId}`,
    data
  )
  return response.data
}

/**
 * Regenerate the image for a specific scene
 */
export async function regenerateSceneImage(
  projectId: string,
  sceneId: string
): Promise<RegenerateImageResponse> {
  const response = await api.post<RegenerateImageResponse>(
    `/projects/${projectId}/scenes/${sceneId}/regenerate-image`
  )
  return response.data
}
