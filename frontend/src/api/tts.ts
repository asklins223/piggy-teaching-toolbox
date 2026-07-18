/**
 * TTS API module for IndexTTS2 testing
 */

import api from './index'

// Types
export interface TTSRequest {
  text: string
  voice: string
  emotion?: string
  emotion_strength?: number
  speed?: number
  gain?: number
  sample_rate?: number
  response_format?: string
  seed?: number
  interval_silence?: number
  max_text_tokens_per_sentence?: number
  emo_random?: boolean
}

export interface VoiceInfo {
  id: string
  name: string
  preview_url?: string
  audio_url?: string
}

export interface VoiceListResponse {
  list: VoiceInfo[]
}

export interface UploadVoiceResponse {
  id: string
  name: string
}

/**
 * Generate TTS audio
 */
export async function generateTTS(request: TTSRequest): Promise<Blob> {
  const response = await api.post('/tts/generate', request, {
    responseType: 'blob'
  })
  return response.data
}

/**
 * Get available voices
 */
export async function getVoices(): Promise<VoiceListResponse> {
  const response = await api.get<VoiceListResponse>('/tts/voices')
  return response.data
}

/**
 * Upload custom voice
 */
export async function uploadVoice(file: File, name: string): Promise<UploadVoiceResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('name', name)
  
  const response = await api.post<UploadVoiceResponse>('/tts/voices/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return response.data
}

/**
 * Delete custom voice
 */
export async function deleteVoice(voiceId: string): Promise<{ success: boolean; message: string }> {
  const response = await api.delete<{ success: boolean; message: string }>(`/tts/voices/${voiceId}`)
  return response.data
}

/**
 * Get voice preview audio as blob URL
 */
export async function getVoicePreviewUrl(voiceId: string): Promise<string> {
  const response = await api.get(`/tts/voices/${voiceId}/preview`, {
    responseType: 'blob'
  })
  return URL.createObjectURL(response.data)
}
