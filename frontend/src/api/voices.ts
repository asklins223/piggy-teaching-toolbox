/**
 * Voices and Audio API module
 * Requirements: 3.4
 */

import api from './index'

// Types
export interface VoiceInfo {
  voice_id: string
  name: string
  preview_url?: string | null
}

export interface VoicesListResponse {
  voices: VoiceInfo[]
}

export interface GenerateAudioRequest {
  voice_id?: string | null
}

export interface GenerateAudioResponse {
  task_id: string
}

export interface SceneAudioResponse {
  scene_id: string
  audio_cn_url?: string | null
  audio_en_url?: string | null
  duration_cn?: number | null
  duration_en?: number | null
}

export interface FullAudioResponse {
  full_cn_url?: string | null
  full_en_url?: string | null
}

// API functions

/**
 * Get list of available voices
 */
export async function getVoices(): Promise<VoicesListResponse> {
  const response = await api.get<VoicesListResponse>('/voices')
  return response.data
}

/**
 * Generate audio for all scenes in a project
 */
export async function generateAudio(
  projectId: string,
  voiceId?: string
): Promise<GenerateAudioResponse> {
  const response = await api.post<GenerateAudioResponse>(
    `/projects/${projectId}/audio/generate`,
    { voice_id: voiceId }
  )
  return response.data
}

/**
 * Get audio URLs for a specific scene
 */
export async function getSceneAudio(
  projectId: string,
  sceneId: string
): Promise<SceneAudioResponse> {
  const response = await api.get<SceneAudioResponse>(
    `/projects/${projectId}/scenes/${sceneId}/audio`
  )
  return response.data
}

/**
 * Get full merged audio URLs for a project
 */
export async function getFullAudio(projectId: string): Promise<FullAudioResponse> {
  const response = await api.get<FullAudioResponse>(`/projects/${projectId}/audio/full`)
  return response.data
}
