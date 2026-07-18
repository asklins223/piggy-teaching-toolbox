<template>
  <div class="step-audio">
    <div class="page-header">
      <h2 class="page-title">
        <el-icon class="title-icon"><Headset /></el-icon>
        生成音频
      </h2>
      <p class="page-subtitle">为所有分镜生成中英文双语配音</p>
    </div>

    <el-row :gutter="32" class="content-row">
      <!-- Left: Voice Selection -->
      <el-col :xs="24" :lg="14">
        <!-- Voice Selection Card -->
        <div class="card voice-card">
          <div class="card-header">
            <div class="header-left">
              <div class="header-icon voice-icon">
                <el-icon><Microphone /></el-icon>
              </div>
              <div class="header-text">
                <h3>音色选择</h3>
                <span>选择配音的声音风格</span>
              </div>
            </div>
          </div>
          
          <div class="card-body">
            <div class="voice-grid" v-loading="loadingVoices">
              <VoiceCard
                v-for="voice in voices"
                :key="voice.voice_id"
                :id="voice.voice_id"
                :name="voice.name"
                :preview-url="voice.preview_url || undefined"
                :selected="selectedVoiceId === voice.voice_id"
                @select="selectedVoiceId = voice.voice_id"
              />
              <div v-if="!loadingVoices && voices.length === 0" class="empty-voice">
                <el-icon :size="32"><Microphone /></el-icon>
                <span>暂无音色</span>
              </div>
            </div>
            
            <div class="voice-tip">
              <el-icon><InfoFilled /></el-icon>
              <span>系统将为所有分镜生成中英文双语配音，音频将自动与分镜时长匹配</span>
            </div>
          </div>
        </div>

        <!-- Audio Preview Card (when completed) -->
        <div class="card preview-card" v-if="hasExistingAudio">
          <div class="card-header">
            <div class="header-left">
              <div class="header-icon preview-icon">
                <el-icon><VideoPlay /></el-icon>
              </div>
              <div class="header-text">
                <h3>音频预览</h3>
                <span>试听生成的配音效果</span>
              </div>
            </div>
          </div>
          
          <div class="card-body">
            <div class="audio-preview-list">
              <div class="audio-item">
                <div class="audio-label">
                  <el-tag size="small" type="danger" effect="light" round>中文</el-tag>
                  完整配音
                </div>
                <AudioPlayer :src="fullAudioCn" :height="50" />
              </div>
              <div class="audio-item">
                <div class="audio-label">
                  <el-tag size="small" type="primary" effect="light" round>英文</el-tag>
                  完整配音
                </div>
                <AudioPlayer :src="fullAudioEn" :height="50" />
              </div>
            </div>
          </div>
        </div>
      </el-col>
      
      <!-- Right: Generation Progress -->
      <el-col :xs="24" :lg="10">
        <div class="card progress-card">
          <div class="card-header">
            <div class="header-left">
              <div class="header-icon progress-icon" :class="getProgressIconClass()">
                <el-icon><Headset /></el-icon>
              </div>
              <div class="header-text">
                <h3>生成进度</h3>
                <span>{{ getProgressSubtitle() }}</span>
              </div>
            </div>
            <el-tag v-if="taskStatus" :type="getStatusTagType(taskStatus)" effect="light" round>
              {{ getStatusText(taskStatus) }}
            </el-tag>
          </div>
          
          <div class="card-body progress-body">
            <!-- Not Started State -->
            <div v-if="!isGenerating && !taskStatus && !hasExistingAudio" class="state-container not-started">
              <div class="state-icon">
                <el-icon><Headset /></el-icon>
              </div>
              <h4>准备就绪</h4>
              <p>选择音色后点击下方按钮开始生成配音</p>
            </div>
            
            <!-- Generating State -->
            <div v-else-if="isGenerating || (taskStatus && taskStatus !== 'completed' && taskStatus !== 'failed')" class="state-container generating">
              <div class="progress-ring">
                <svg viewBox="0 0 100 100">
                  <circle class="progress-bg" cx="50" cy="50" r="45" />
                  <circle 
                    class="progress-bar" 
                    cx="50" cy="50" r="45"
                    :style="{ strokeDashoffset: progressOffset }"
                  />
                </svg>
                <div class="progress-text">
                  <span class="progress-value">{{ progress }}</span>
                  <span class="progress-unit">%</span>
                </div>
              </div>
              <div class="progress-info">
                <div class="progress-message">{{ progressMessage || '准备中...' }}</div>
                <div v-if="currentStep && totalSteps" class="progress-steps">
                  步骤 {{ currentStep }} / {{ totalSteps }}
                </div>
              </div>
            </div>
            
            <!-- Completed State -->
            <div v-else-if="taskStatus === 'completed' || hasExistingAudio" class="state-container completed">
              <div class="state-icon success">
                <el-icon><CircleCheck /></el-icon>
              </div>
              <h4>生成完成</h4>
              <p>所有分镜的中英文配音已生成完成</p>
            </div>
            
            <!-- Failed State -->
            <div v-else-if="taskStatus === 'failed'" class="state-container failed">
              <div class="state-icon error">
                <el-icon><CircleClose /></el-icon>
              </div>
              <h4>生成失败</h4>
              <p>{{ errorMessage || '生成过程中发生错误' }}</p>
              <el-button type="primary" @click="handleRetry" class="retry-btn">
                <el-icon><RefreshRight /></el-icon>
                重新生成
              </el-button>
            </div>
          </div>
        </div>

        <!-- Navigation Buttons -->
        <div class="navigation-buttons">
          <el-button @click="handlePrevStep" :disabled="isGenerating" size="large" class="nav-btn prev-btn">
            <el-icon><ArrowLeft /></el-icon>
            上一步
          </el-button>
          
          <el-button 
            v-if="!taskStatus && !hasExistingAudio"
            type="primary" 
            size="large"
            @click="handleStartGeneration"
            :loading="isGenerating"
            :disabled="!canGenerate"
            class="nav-btn generate-btn"
          >
            <el-icon><Headset /></el-icon>
            开始生成
          </el-button>
          
          <template v-else-if="taskStatus === 'completed' || hasExistingAudio">
            <el-button 
              @click="handleRegenerate"
              :disabled="isGenerating"
              size="large"
              class="nav-btn regen-btn"
            >
              <el-icon><RefreshRight /></el-icon>
              重新生成
            </el-button>
            <el-button 
              type="primary" 
              size="large"
              @click="handleNextStep"
              class="nav-btn next-btn"
            >
              下一步
              <el-icon><ArrowRight /></el-icon>
            </el-button>
          </template>
          
          <el-button 
            v-else-if="isGenerating || (taskStatus && !['completed', 'failed'].includes(taskStatus))"
            type="info" 
            size="large"
            disabled
            class="nav-btn"
          >
            <el-icon class="is-loading"><Loading /></el-icon>
            生成中...
          </el-button>
          
          <el-button 
            v-else-if="taskStatus === 'failed'"
            type="primary" 
            size="large"
            @click="handleRetry"
            class="nav-btn"
          >
            <el-icon><RefreshRight /></el-icon>
            重新生成
          </el-button>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  InfoFilled, 
  Headset, 
  Loading, 
  ArrowRight, 
  ArrowLeft,
  RefreshRight,
  Microphone,
  VideoPlay,
  CircleCheck,
  CircleClose
} from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'
import AudioPlayer from '@/components/AudioPlayer.vue'
import VoiceCard from '@/components/VoiceCard.vue'
import * as voicesApi from '@/api/voices'
import * as tasksApi from '@/api/tasks'
import type { VoiceInfo } from '@/api/voices'
import type { TaskStatus } from '@/api/tasks'

const router = useRouter()
const projectStore = useProjectStore()

// State
const voices = ref<VoiceInfo[]>([])
const selectedVoiceId = ref('')
const loadingVoices = ref(false)
const hasExistingAudio = ref(false)
const fullAudioCn = ref('')
const fullAudioEn = ref('')

// Task state
const isGenerating = ref(false)
const taskId = ref('')
const taskStatus = ref<TaskStatus | ''>('')
const progress = ref(0)
const progressMessage = ref('')
const currentStep = ref(0)
const totalSteps = ref(0)
const errorMessage = ref('')

// Computed
const canGenerate = computed(() => {
  return projectStore.currentProjectId && !isGenerating.value
})

const progressOffset = computed(() => {
  const circumference = 2 * Math.PI * 45
  return circumference - (progress.value / 100) * circumference
})

// Load data on mount
onMounted(async () => {
  await loadVoices()
  if (projectStore.currentProjectId) {
    await checkActiveTask()
    await checkExistingAudio()
  }
})

// Watch for project changes
watch(() => projectStore.currentProjectId, async (newId) => {
  if (newId) {
    await checkActiveTask()
    await checkExistingAudio()
  }
})

async function loadVoices() {
  loadingVoices.value = true
  try {
    const response = await voicesApi.getVoices()
    voices.value = response.voices
    if (voices.value.length > 0 && voices.value[0]) {
      selectedVoiceId.value = voices.value[0].voice_id
    }
  } catch (error: any) {
    console.error('Failed to load voices:', error)
    ElMessage.error('加载音色列表失败')
  } finally {
    loadingVoices.value = false
  }
}

async function checkActiveTask() {
  if (!projectStore.currentProjectId) return
  
  try {
    const { getProjectActiveTask } = await import('@/api/projects')
    const response = await getProjectActiveTask(projectStore.currentProjectId)
    
    if (response.has_active_task && response.task_type === 'audio') {
      // 恢复正在进行的任务状态
      taskId.value = response.task_id || ''
      taskStatus.value = response.status as any || ''
      progress.value = response.progress || 0
      progressMessage.value = response.message || ''
      isGenerating.value = true
      
      // 继续轮询任务状态
      await pollTaskStatus()
    }
  } catch (error: any) {
    console.error('Failed to check active task:', error)
  }
}

async function checkExistingAudio() {
  if (!projectStore.currentProjectId) return
  
  try {
    const project = projectStore.projectData
    if (project?.status === 'audio_ready' || project?.status === 'completed') {
      hasExistingAudio.value = true
      taskStatus.value = 'completed'
    }
    
    const response = await voicesApi.getFullAudio(projectStore.currentProjectId)
    if (response.full_cn_url || response.full_en_url) {
      hasExistingAudio.value = true
      taskStatus.value = 'completed'
      fullAudioCn.value = response.full_cn_url || ''
      fullAudioEn.value = response.full_en_url || ''
    }
  } catch (error: any) {
    hasExistingAudio.value = false
  }
}

async function handleStartGeneration() {
  if (!projectStore.currentProjectId) {
    ElMessage.warning('请先创建或加载项目')
    return
  }
  
  isGenerating.value = true
  taskStatus.value = 'pending'
  progress.value = 0
  progressMessage.value = '正在启动音频生成任务...'
  currentStep.value = 0
  totalSteps.value = 0
  errorMessage.value = ''
  
  try {
    const response = await voicesApi.generateAudio(
      projectStore.currentProjectId,
      selectedVoiceId.value || undefined
    )
    
    taskId.value = response.task_id
    await pollTaskStatus()
    
  } catch (error: any) {
    const errorDetail = error.response?.data?.detail
    
    // 处理任务冲突错误
    if (error.response?.status === 409 && errorDetail?.code === 'TASK_IN_PROGRESS') {
      // 恢复到正在进行的任务
      taskId.value = errorDetail.task_id
      isGenerating.value = true
      ElMessage.warning('项目有正在进行的任务，已自动恢复')
      await pollTaskStatus()
      return
    }
    
    isGenerating.value = false
    taskStatus.value = 'failed'
    errorMessage.value = errorDetail?.message || '启动生成任务失败'
    ElMessage.error(errorMessage.value)
  }
}

async function pollTaskStatus() {
  try {
    const finalTask = await tasksApi.pollTaskStatus(
      taskId.value,
      (task) => {
        taskStatus.value = task.status
        progress.value = task.progress
        progressMessage.value = task.message
        currentStep.value = task.current
        totalSteps.value = task.total
      },
      1000
    )
    
    isGenerating.value = false
    
    if (finalTask.status === 'completed') {
      ElMessage.success('音频生成完成')
      await projectStore.refreshProject()
      await checkExistingAudio()
      
      setTimeout(() => {
        handleNextStep()
      }, 1500)
      
    } else if (finalTask.status === 'failed') {
      errorMessage.value = finalTask.error || '生成过程中发生未知错误'
      ElMessage.error('音频生成失败')
    }
    
  } catch (error: any) {
    isGenerating.value = false
    taskStatus.value = 'failed'
    errorMessage.value = error.response?.data?.detail?.message || '获取任务状态失败'
    ElMessage.error(errorMessage.value)
  }
}

function handleRetry() {
  taskStatus.value = ''
  taskId.value = ''
  progress.value = 0
  progressMessage.value = ''
  errorMessage.value = ''
}

function handleRegenerate() {
  hasExistingAudio.value = false
  fullAudioCn.value = ''
  fullAudioEn.value = ''
  taskStatus.value = ''
  taskId.value = ''
  progress.value = 0
  progressMessage.value = ''
  errorMessage.value = ''
}

function handlePrevStep() {
  projectStore.setStep(4)
  router.push('/step/4')
}

function handleNextStep() {
  projectStore.setStep(6)
  router.push('/step/6')
}

function getStatusTagType(status: TaskStatus | ''): 'success' | 'warning' | 'info' | 'danger' {
  const map: Record<string, 'success' | 'warning' | 'info' | 'danger'> = {
    'pending': 'info',
    'running': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return map[status] || 'info'
}

function getStatusText(status: TaskStatus | ''): string {
  const map: Record<string, string> = {
    'pending': '等待中',
    'running': '生成中',
    'completed': '已完成',
    'failed': '失败'
  }
  return map[status] || status
}

function getProgressIconClass(): string {
  if (taskStatus.value === 'completed' || hasExistingAudio.value) return 'success'
  if (taskStatus.value === 'failed') return 'error'
  if (isGenerating.value || taskStatus.value === 'running') return 'running'
  return ''
}

function getProgressSubtitle(): string {
  if (taskStatus.value === 'completed' || hasExistingAudio.value) return '音频已生成完成'
  if (taskStatus.value === 'failed') return '生成过程中出现问题'
  if (isGenerating.value || taskStatus.value === 'running') return '正在生成中...'
  return '等待开始生成'
}
</script>


<style scoped>
.step-audio {
  padding: 32px;
  max-width: 1400px;
  margin: 0 auto;
}

/* Page Header */
.page-header {
  margin-bottom: 32px;
  text-align: center;
}

.page-title {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.title-icon {
  color: #e6a23c;
  font-size: 32px;
}

.page-subtitle {
  color: var(--text-muted);
  font-size: 15px;
  margin: 0;
}

/* Content Row */
.content-row {
  display: flex;
  align-items: flex-start;
}

/* Card Styles */
.card {
  background: var(--bg-card);
  border-radius: 16px;
  box-shadow: var(--shadow-md);
  overflow: hidden;
  transition: box-shadow 0.3s ease, background-color 0.3s ease;
  margin-bottom: 24px;
}

.card:hover {
  box-shadow: var(--shadow-lg);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-secondary);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.header-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  transition: all 0.3s ease;
}

.voice-icon {
  background: linear-gradient(135deg, #e6a23c 0%, #f0b85a 100%);
  color: #fff;
}

.preview-icon {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
  color: #fff;
}

.progress-icon {
  background: linear-gradient(135deg, #909399 0%, #b1b3b8 100%);
  color: #fff;
}

.progress-icon.running {
  background: linear-gradient(135deg, #e6a23c 0%, #f0b85a 100%);
  animation: pulse 2s infinite;
}

.progress-icon.success {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
}

.progress-icon.error {
  background: linear-gradient(135deg, #f56c6c 0%, #f89898 100%);
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.header-text h3 {
  margin: 0 0 2px 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-text span {
  font-size: 12px;
  color: var(--text-muted);
}

/* Card Body */
.card-body {
  padding: 24px;
}

/* Voice Grid */
.voice-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  min-height: 100px;
  margin-bottom: 20px;
}

.empty-voice {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px;
  background: var(--bg-secondary);
  border-radius: 12px;
  color: var(--text-muted);
}

.voice-tip {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 14px 16px;
  background: rgba(230, 162, 60, 0.1);
  border: 1px solid rgba(230, 162, 60, 0.3);
  border-radius: 10px;
  font-size: 13px;
  color: #e6a23c;
}

.voice-tip .el-icon {
  font-size: 16px;
  flex-shrink: 0;
  margin-top: 1px;
}

/* Audio Preview */
.audio-preview-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.audio-item {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 12px;
}

.audio-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.no-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 40px;
  color: var(--text-muted);
}

.no-preview .el-icon {
  font-size: 32px;
}

/* Progress Card */
.progress-card {
  position: sticky;
  top: 24px;
}

.progress-body {
  min-height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* State Containers */
.state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 20px;
}

.state-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  margin-bottom: 20px;
  background: var(--bg-secondary);
  color: var(--text-muted);
}

.state-icon.success {
  background: rgba(103, 194, 58, 0.15);
  color: #67c23a;
}

.state-icon.error {
  background: rgba(245, 108, 108, 0.15);
  color: #f56c6c;
}

.state-container h4 {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.state-container p {
  margin: 0 0 20px 0;
  font-size: 14px;
  color: var(--text-muted);
}

/* Progress Ring */
.progress-ring {
  position: relative;
  width: 140px;
  height: 140px;
  margin-bottom: 24px;
}

.progress-ring svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.progress-bg {
  fill: none;
  stroke: var(--border-color);
  stroke-width: 8;
}

.progress-bar {
  fill: none;
  stroke: #e6a23c;
  stroke-width: 8;
  stroke-linecap: round;
  stroke-dasharray: 283;
  transition: stroke-dashoffset 0.5s ease;
}

.progress-ring svg {
  filter: drop-shadow(0 4px 12px rgba(230, 162, 60, 0.2));
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.progress-value {
  font-size: 36px;
  font-weight: 700;
  color: #e6a23c;
  line-height: 1;
}

.progress-unit {
  font-size: 16px;
  color: var(--text-muted);
}

.progress-info {
  text-align: center;
}

.progress-message {
  font-size: 15px;
  color: var(--text-primary);
  font-weight: 500;
  margin-bottom: 8px;
}

.progress-steps {
  font-size: 13px;
  color: var(--text-muted);
}

/* Buttons */
.retry-btn {
  border-radius: 10px;
  background: linear-gradient(135deg, #e6a23c 0%, #f0b85a 100%);
  border: none;
  font-weight: 500;
}

.retry-btn:hover {
  background: linear-gradient(135deg, #cf9236 0%, #e6a23c 100%);
}

/* Navigation */
.navigation-buttons {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.nav-btn {
  border-radius: 12px;
  font-weight: 500;
  height: 48px;
}

.prev-btn {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.prev-btn:hover:not(:disabled) {
  background: var(--hover-bg);
  border-color: var(--border-color);
}

.generate-btn {
  flex: 1;
  background: linear-gradient(135deg, #e6a23c 0%, #f0b85a 100%);
  border: none;
}

.generate-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #cf9236 0%, #e6a23c 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(230, 162, 60, 0.4);
}

.regen-btn {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.regen-btn:hover:not(:disabled) {
  background: var(--hover-bg);
  border-color: var(--border-color);
}

.next-btn {
  flex: 1;
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
  border: none;
}

.next-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #529b2e 0%, #67c23a 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.4);
}

/* Loading animation */
.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 1199px) {
  .step-audio {
    padding: 24px;
  }
  
  .content-row {
    flex-direction: column;
  }
  
  .progress-card {
    position: static;
  }
}

@media (max-width: 768px) {
  .step-audio {
    padding: 16px;
  }
  
  .page-title {
    font-size: 22px;
  }
  
  .progress-ring {
    width: 120px;
    height: 120px;
  }
  
  .progress-value {
    font-size: 28px;
  }
  
  .navigation-buttons {
    flex-direction: column;
  }
  
  .nav-btn {
    width: 100%;
  }
}
</style>
