/**
 * Projects API module
 * Requirements: 3.1
 */

import api from './index'

// Types
export interface ProjectSummary {
  project_id: string
  topic: string
  status: string
  created_at: string
  style?: string
}

export interface ProjectListResponse {
  projects: ProjectSummary[]
}

export interface CreateProjectRequest {
  topic: string
  target_audience: string
  key_points?: string[]
  // Video style (Requirements: 7.1)
  style?: string
  custom_style_description?: string
}

export interface CreateProjectResponse {
  project_id: string
  status: string
}

export interface DeleteProjectResponse {
  success: boolean
}

export interface TeachingGoal {
  topic: string
  target_audience: string
  key_points: string[]
  // Video style (Requirements: 7.1)
  style?: string
  custom_style_description?: string
}

export interface Scene {
  scene_id: string
  step_number: number
  description_cn: string
  narration_cn: string
  narration_en: string
  duration: number
  emotion: string
  image_url?: string
}

export interface Storyboard {
  scenes: Scene[]
}

export interface ImageInfo {
  scene_id: string
  path: string
  status: string
}

export interface AudioInfo {
  scene_id: string
  audio_path?: string
  audio_path_en?: string
  status: string
  duration_seconds?: number
  duration_seconds_en?: number
}

export interface CharacterReference {
  character_id: string
  name: string
  image_path: string
  image_url?: string
}

export interface SubtitleSegment {
  scene_id: string
  start_time: number
  end_time: number
  text_cn: string
  text_en: string
}

export interface ExportPackage {
  project_id: string
  zip_path: string
  manifest_path: string
  subtitle_cn_path: string
  subtitle_en_path: string
}

export interface ProjectDetail {
  project_id: string
  created_at: string
  updated_at: string
  status: string
  goal: TeachingGoal
  storyboard?: Storyboard
  images: ImageInfo[]
  audios: AudioInfo[]
  subtitles: SubtitleSegment[]
  characters: CharacterReference[]
  export_package?: ExportPackage
}

// API functions

/**
 * Get list of all projects
 */
export async function listProjects(): Promise<ProjectListResponse> {
  const response = await api.get<ProjectListResponse>('/projects')
  return response.data
}

/**
 * Create a new project
 */
export async function createProject(data: CreateProjectRequest): Promise<CreateProjectResponse> {
  const response = await api.post<CreateProjectResponse>('/projects', data)
  return response.data
}

/**
 * Get project details by ID
 */
export async function getProject(projectId: string): Promise<ProjectDetail> {
  const response = await api.get<ProjectDetail>(`/projects/${projectId}`)
  return response.data
}

/**
 * Delete a project
 */
export async function deleteProject(projectId: string): Promise<DeleteProjectResponse> {
  const response = await api.delete<DeleteProjectResponse>(`/projects/${projectId}`)
  return response.data
}

// AI Optimization Types
export interface OptimizeTopicRequest {
  topic: string
}

export interface OptimizeTopicResponse {
  optimized_topic: string
  message: string
}

export interface SuggestKeyPointsRequest {
  topic: string
  target_audience?: string
}

export interface SuggestKeyPointsResponse {
  key_points: string[]
  message: string
}

/**
 * AI optimize teaching topic
 */
export async function optimizeTopic(topic: string): Promise<OptimizeTopicResponse> {
  const response = await api.post<OptimizeTopicResponse>('/projects/ai/optimize-topic', { topic })
  return response.data
}

/**
 * AI suggest key points for teaching topic
 */
export async function suggestKeyPoints(topic: string, targetAudience?: string): Promise<SuggestKeyPointsResponse> {
  const response = await api.post<SuggestKeyPointsResponse>('/projects/ai/suggest-keypoints', {
    topic,
    target_audience: targetAudience || ''
  })
  return response.data
}

// Suggest Audience Types
export interface SuggestAudienceResponse {
  target_audience: string
}

/**
 * AI suggest target audience for teaching topic
 */
export async function suggestAudience(topic: string): Promise<SuggestAudienceResponse> {
  const response = await api.post<SuggestAudienceResponse>('/projects/ai/suggest-audience', { topic })
  return response.data
}

// Random Topic Types
export interface RandomTopicResponse {
  topic: string
  target_audience: string
  key_points: string[]
}

/**
 * AI generate random teaching topic based on style
 */
export async function generateRandomTopic(
  style?: string,
  customStyleDescription?: string
): Promise<RandomTopicResponse> {
  const payload: any = {}
  
  if (style) {
    payload.style = style
  }
  
  if (customStyleDescription) {
    payload.custom_style_description = customStyleDescription
  }
  
  const response = await api.post<RandomTopicResponse>('/projects/ai/random-topic', payload)
  return response.data
}

// Active Task Types
export interface ActiveTaskResponse {
  has_active_task: boolean
  task_id?: string
  task_type?: string
  status?: string
  progress?: number
  message?: string
}

/**
 * Get project's active task (if any)
 */
export async function getProjectActiveTask(projectId: string): Promise<ActiveTaskResponse> {
  const response = await api.get<ActiveTaskResponse>(`/projects/${projectId}/active-task`)
  return response.data
}
