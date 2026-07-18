import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import * as projectsApi from '@/api/projects'
import type { ProjectDetail, ProjectSummary } from '@/api/projects'

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

export interface ImageInfo {
  scene_id: string
  path: string
}

export interface AudioInfo {
  scene_id: string
  path_cn: string
  path_en: string
}

export const useProjectStore = defineStore('project', () => {
  // State - 从 localStorage 恢复
  const currentProjectId = ref(localStorage.getItem('currentProjectId') || '')
  const currentStep = ref(parseInt(localStorage.getItem('currentStep') || '1', 10))
  const maxStep = ref(parseInt(localStorage.getItem('maxStep') || '1', 10))
  const projectData = ref<ProjectDetail | null>(null)
  const projectList = ref<ProjectSummary[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const initialized = ref(false)

  // 监听变化并持久化
  watch(currentProjectId, (val) => {
    if (val) {
      localStorage.setItem('currentProjectId', val)
    } else {
      localStorage.removeItem('currentProjectId')
    }
  })

  watch(currentStep, (val) => {
    localStorage.setItem('currentStep', String(val))
  })

  watch(maxStep, (val) => {
    localStorage.setItem('maxStep', String(val))
  })

  // Getters
  const hasProject = computed(() => !!currentProjectId.value)
  const scenes = computed(() => projectData.value?.storyboard?.scenes || [])
  const characters = computed(() => projectData.value?.characters || [])
  const projectStatus = computed(() => projectData.value?.status || '')

  // Actions
  function setProjectId(projectId: string) {
    currentProjectId.value = projectId
  }

  function setProjectData(data: ProjectDetail) {
    projectData.value = data
    updateStepFromStatus(data.status)
  }

  function updateStepFromStatus(status: string) {
    const statusToStep: Record<string, number> = {
      'initialized': 3,           // 项目创建后，可以进入生成分镜步骤
      'storyboard_ready': 4,      // 分镜生成后，可以进入编辑调整步骤
      'images_generating': 4,     // 图片生成中，仍在编辑调整步骤
      'images_ready': 4,          // 图片生成后，仍在编辑调整步骤
      'audio_generating': 5,      // 音频生成中，在音频生成步骤
      'audio_ready': 6,           // 音频生成后，可以进入导出步骤
      'subtitles_ready': 6,       // 字幕生成后，可以进入导出步骤
      'completed': 6              // 完成后，可以进入导出步骤
    }
    maxStep.value = statusToStep[status] || 1
  }

  function setStep(step: number) {
    if (step <= maxStep.value) {
      currentStep.value = step
    }
  }

  async function loadProjectList(): Promise<void> {
    loading.value = true
    error.value = null
    
    try {
      const response = await projectsApi.listProjects()
      projectList.value = response.projects
    } catch (err: any) {
      error.value = err.response?.data?.detail?.message || '加载项目列表失败'
    } finally {
      loading.value = false
    }
  }

  async function loadProject(projectId: string): Promise<boolean> {
    loading.value = true
    error.value = null
    
    try {
      const data = await projectsApi.getProject(projectId)
      currentProjectId.value = projectId
      projectData.value = data
      updateStepFromStatus(data.status)
      return true
    } catch (err: any) {
      error.value = err.response?.data?.detail?.message || '加载项目失败'
      return false
    } finally {
      loading.value = false
    }
  }

  async function createProject(
    topic: string,
    targetAudience: string,
    keyPoints: string[] = [],
    style: string = 'teaching',
    customStyleDescription?: string
  ): Promise<string | null> {
    loading.value = true
    error.value = null
    
    try {
      const response = await projectsApi.createProject({
        topic,
        target_audience: targetAudience,
        key_points: keyPoints,
        style,
        custom_style_description: customStyleDescription
      })
      currentProjectId.value = response.project_id
      // Load the full project data
      await loadProject(response.project_id)
      return response.project_id
    } catch (err: any) {
      error.value = err.response?.data?.detail?.message || '创建项目失败'
      return null
    } finally {
      loading.value = false
    }
  }

  async function deleteProject(projectId: string): Promise<boolean> {
    loading.value = true
    error.value = null
    
    try {
      await projectsApi.deleteProject(projectId)
      // Remove from list
      projectList.value = projectList.value.filter(p => p.project_id !== projectId)
      // Clear current project if it was deleted
      if (currentProjectId.value === projectId) {
        reset()
      }
      return true
    } catch (err: any) {
      error.value = err.response?.data?.detail?.message || '删除项目失败'
      return false
    } finally {
      loading.value = false
    }
  }

  async function refreshProject(): Promise<boolean> {
    if (!currentProjectId.value) {
      return false
    }
    return loadProject(currentProjectId.value)
  }

  // 初始化：如果有保存的项目ID，自动加载项目数据
  async function initFromStorage(): Promise<boolean> {
    if (initialized.value) {
      return true
    }
    
    initialized.value = true
    
    if (currentProjectId.value) {
      const success = await loadProject(currentProjectId.value)
      if (!success) {
        // 项目加载失败，清除存储
        reset()
      }
      return success
    }
    return false
  }

  function reset() {
    currentProjectId.value = ''
    currentStep.value = 1
    maxStep.value = 1
    projectData.value = null
    error.value = null
    localStorage.removeItem('currentProjectId')
    localStorage.removeItem('currentStep')
    localStorage.removeItem('maxStep')
  }

  function clearError() {
    error.value = null
  }

  return { 
    // State
    currentProjectId, 
    currentStep, 
    maxStep, 
    projectData,
    projectList,
    loading,
    error,
    initialized,
    // Getters
    hasProject,
    scenes,
    characters,
    projectStatus,
    // Actions
    setProjectId,
    setProjectData,
    setStep,
    loadProjectList,
    loadProject,
    createProject,
    deleteProject,
    refreshProject,
    initFromStorage,
    reset,
    clearError
  }
})
