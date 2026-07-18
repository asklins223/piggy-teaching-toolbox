<template>
  <div class="step-storyboard">
    <div class="page-header">
      <h2 class="page-title">
        <el-icon class="title-icon"><VideoCamera /></el-icon>
        生成分镜
      </h2>
      <p class="page-subtitle">AI 将根据教学内容自动生成分镜脚本和图片</p>
    </div>

    <el-row :gutter="32" class="content-row">
      <!-- Left: Project Info & Settings -->
      <el-col :xs="24" :lg="14">
        <!-- Project Info Card -->
        <div class="card info-card" v-if="projectStore.projectData">
          <div class="card-header">
            <div class="header-left">
              <div class="header-icon info-icon">
                <el-icon><Document /></el-icon>
              </div>
              <div class="header-text">
                <h3>项目信息</h3>
                <span>当前项目的基本设置</span>
              </div>
            </div>
          </div>
          
          <div class="card-body">
            <div class="info-grid">
              <div class="info-item">
                <div class="info-label">
                  <el-icon><Edit /></el-icon>
                  教学主题
                </div>
                <div class="info-value">{{ projectStore.projectData.goal?.topic || '-' }}</div>
              </div>
              
              <div class="info-item">
                <div class="info-label">
                  <el-icon><User /></el-icon>
                  目标受众
                </div>
                <div class="info-value">{{ projectStore.projectData.goal?.target_audience || '-' }}</div>
              </div>
              
              <div class="info-item">
                <div class="info-label">
                  <el-icon><Film /></el-icon>
                  视频风格
                </div>
                <div class="info-value">
                  <el-tag 
                    v-if="projectStore.projectData.goal?.style" 
                    size="small" 
                    type="warning" 
                    effect="light" 
                    round
                  >
                    {{ getStyleDisplayName(projectStore.projectData.goal.style) }}
                  </el-tag>
                  <span v-else class="empty-text">-</span>
                </div>
              </div>
              
              <div class="info-item full-width">
                <div class="info-label">
                  <el-icon><Collection /></el-icon>
                  关键知识点
                </div>
                <div class="info-value tags">
                  <el-tag 
                    v-for="(point, index) in (projectStore.projectData.goal?.key_points || [])" 
                    :key="index"
                    size="small"
                    effect="light"
                    round
                  >
                    {{ point }}
                  </el-tag>
                  <span v-if="!projectStore.projectData.goal?.key_points?.length" class="empty-text">-</span>
                </div>
              </div>
              
              <div class="info-item full-width">
                <div class="info-label">
                  <el-icon><UserFilled /></el-icon>
                  项目角色
                </div>
                <div class="info-value tags">
                  <el-tag 
                    v-for="char in projectCharacters" 
                    :key="char.character_id"
                    size="small"
                    type="success"
                    effect="light"
                    round
                  >
                    {{ char.name }}
                  </el-tag>
                  <span v-if="projectCharacters.length === 0" class="empty-text">未设置角色</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Generation Settings Card -->
        <div class="card settings-card">
          <div class="card-header">
            <div class="header-left">
              <div class="header-icon settings-icon">
                <el-icon><Setting /></el-icon>
              </div>
              <div class="header-text">
                <h3>生成设置</h3>
                <span>配置分镜生成参数</span>
              </div>
            </div>
          </div>
          
          <div class="card-body">
            <div class="setting-item">
              <div class="setting-label">
                <el-icon><Clock /></el-icon>
                默认分镜时长
              </div>
              <div class="duration-options">
                <div 
                  v-for="option in durationOptions" 
                  :key="option.value"
                  class="duration-option"
                  :class="{ 'is-active': selectedDuration === option.value }"
                  @click="!isGenerating && (selectedDuration = option.value)"
                >
                  <span class="duration-value">{{ option.value }}</span>
                  <span class="duration-unit">秒</span>
                </div>
              </div>
            </div>
            
            <div class="setting-item">
              <div class="setting-label">
                <el-icon><List /></el-icon>
                生成模式
              </div>
              <el-switch
                v-model="useStepwiseMode"
                :disabled="isGenerating"
                active-text="分步生成"
                inactive-text="一次生成"
              />
            </div>
            
            <div class="setting-tip">
              <el-icon><InfoFilled /></el-icon>
              <span v-if="useStepwiseMode">分步生成：先生成大纲，再逐个补充详情，描述更丰富准确</span>
              <span v-else>一次生成：快速生成所有分镜，适合简单内容</span>
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
                <el-icon><VideoPlay /></el-icon>
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
            <div v-if="!isGenerating && !taskStatus" class="state-container not-started">
              <div class="state-icon">
                <el-icon><VideoCamera /></el-icon>
              </div>
              <h4>准备就绪</h4>
              <p>点击下方按钮开始生成分镜脚本和图片</p>
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
            <div v-else-if="taskStatus === 'completed'" class="state-container completed">
              <div class="state-icon success">
                <el-icon><CircleCheck /></el-icon>
              </div>
              <h4>生成完成</h4>
              <p>分镜脚本和图片已生成完成</p>
              <div class="completed-actions">
                <el-button type="primary" @click="handleGoToEdit" class="view-btn">
                  查看并编辑分镜
                  <el-icon><ArrowRight /></el-icon>
                </el-button>
                <el-button @click="handleRegenerate" class="regenerate-btn">
                  <el-icon><RefreshRight /></el-icon>
                  重新生成
                </el-button>
              </div>
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
          
          <!-- Generation Log -->
          <div v-if="logs.length > 0" class="log-section">
            <div class="log-header">
              <span class="log-title">
                <el-icon><Document /></el-icon>
                生成日志
              </span>
              <el-button text size="small" @click="logs = []" class="clear-btn">
                <el-icon><Delete /></el-icon>
                清空
              </el-button>
            </div>
            <div class="log-content" ref="logContainer">
              <div v-for="(log, index) in logs" :key="index" class="log-item">
                <span class="log-time">{{ log.time }}</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
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
            v-if="!taskStatus || taskStatus === 'failed'"
            type="primary" 
            size="large"
            @click="handleStartGeneration"
            :loading="isGenerating"
            :disabled="!canGenerate"
            class="nav-btn generate-btn"
          >
            <el-icon><VideoPlay /></el-icon>
            开始生成
          </el-button>
          
          <el-button 
            v-else-if="taskStatus === 'completed'"
            type="primary" 
            size="large"
            @click="handleGoToEdit"
            class="nav-btn next-btn"
          >
            下一步
            <el-icon><ArrowRight /></el-icon>
          </el-button>
          
          <el-button 
            v-else
            type="info" 
            size="large"
            disabled
            class="nav-btn"
          >
            <el-icon class="is-loading"><Loading /></el-icon>
            生成中...
          </el-button>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  InfoFilled, 
  VideoCamera, 
  Loading, 
  ArrowRight, 
  ArrowLeft,
  RefreshRight,
  VideoPlay,
  Document,
  Edit,
  User,
  Collection,
  UserFilled,
  Setting,
  Clock,
  CircleCheck,
  CircleClose,
  Delete,
  Film,
  List
} from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'
import * as storyboardApi from '@/api/storyboard'
import * as tasksApi from '@/api/tasks'
import * as charactersApi from '@/api/characters'
import type { CharacterInfo } from '@/api/characters'
import type { TaskStatus } from '@/api/tasks'

const router = useRouter()
const projectStore = useProjectStore()

// Duration options
const durationOptions = [
  { value: '5', label: '5 秒' },
  { value: '8', label: '8 秒' },
  { value: '10', label: '10 秒' },
  { value: '12', label: '12 秒' },
  { value: '15', label: '15 秒' }
]

// State
const selectedDuration = ref('10')
const useStepwiseMode = ref(true)  // 默认使用分步生成模式
const isGenerating = ref(false)
const taskId = ref('')
const taskStatus = ref<TaskStatus | ''>('')
const progress = ref(0)
const progressMessage = ref('')
const currentStep = ref(0)
const totalSteps = ref(0)
const errorMessage = ref('')
const projectCharacters = ref<CharacterInfo[]>([])
const logContainer = ref<HTMLElement | null>(null)

interface LogEntry {
  time: string
  message: string
}
const logs = ref<LogEntry[]>([])

// Computed
const canGenerate = computed(() => {
  return projectStore.currentProjectId && !isGenerating.value
})

const progressOffset = computed(() => {
  const circumference = 2 * Math.PI * 45
  return circumference - (progress.value / 100) * circumference
})

// Load project characters on mount
onMounted(async () => {
  if (projectStore.currentProjectId) {
    await loadProjectCharacters()
    await checkActiveTask()
    await checkExistingStoryboard()
  }
})

// Watch for project changes
watch(() => projectStore.currentProjectId, async (newId) => {
  if (newId) {
    await loadProjectCharacters()
    await checkActiveTask()
    await checkExistingStoryboard()
  }
})

async function loadProjectCharacters() {
  if (!projectStore.currentProjectId) return
  
  try {
    const response = await charactersApi.getProjectCharacters(projectStore.currentProjectId)
    projectCharacters.value = response.characters
  } catch (error: any) {
    console.error('Failed to load project characters:', error)
  }
}

async function checkActiveTask() {
  if (!projectStore.currentProjectId) return
  
  try {
    const { getProjectActiveTask } = await import('@/api/projects')
    const response = await getProjectActiveTask(projectStore.currentProjectId)
    
    if (response.has_active_task && response.task_type === 'storyboard') {
      // 恢复正在进行的任务状态
      taskId.value = response.task_id || ''
      taskStatus.value = response.status as any || ''
      progress.value = response.progress || 0
      progressMessage.value = response.message || ''
      isGenerating.value = true
      addLog(`恢复正在进行的分镜生成任务: ${response.task_id}`)
      
      // 继续轮询任务状态
      await pollTaskStatus()
    }
  } catch (error: any) {
    console.error('Failed to check active task:', error)
  }
}

async function checkExistingStoryboard() {
  if (!projectStore.currentProjectId) return
  
  // 如果正在生成，不检查已有分镜
  if (isGenerating.value) return
  
  try {
    const response = await storyboardApi.getScenes(projectStore.currentProjectId)
    if (response.scenes && response.scenes.length > 0) {
      taskStatus.value = 'completed'
      addLog('检测到已有分镜数据')
    }
  } catch (error: any) {
    // No existing storyboard found
  }
}

function addLog(message: string) {
  const now = new Date()
  const time = now.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit' 
  })
  logs.value.push({ time, message })
  
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

async function handleStartGeneration() {
  if (!projectStore.currentProjectId) {
    ElMessage.warning('请先创建或加载项目')
    return
  }
  
  isGenerating.value = true
  taskStatus.value = 'pending'
  progress.value = 0
  progressMessage.value = '正在启动生成任务...'
  currentStep.value = 0
  totalSteps.value = 0
  errorMessage.value = ''
  logs.value = []
  
  addLog(`开始生成分镜，默认时长: ${selectedDuration.value} 秒，模式: ${useStepwiseMode.value ? '分步生成' : '一次生成'}`)
  
  try {
    const response = await storyboardApi.generateStoryboard(
      projectStore.currentProjectId,
      selectedDuration.value,
      useStepwiseMode.value
    )
    
    taskId.value = response.task_id
    addLog(`任务已创建: ${response.task_id}`)
    
    await pollTaskStatus()
    
  } catch (error: any) {
    const errorDetail = error.response?.data?.detail
    
    // 处理任务冲突错误
    if (error.response?.status === 409 && errorDetail?.code === 'TASK_IN_PROGRESS') {
      // 恢复到正在进行的任务
      taskId.value = errorDetail.task_id
      isGenerating.value = true
      addLog(`检测到正在进行的${errorDetail.task_type}任务，正在恢复...`)
      ElMessage.warning('项目有正在进行的任务，已自动恢复')
      await pollTaskStatus()
      return
    }
    
    isGenerating.value = false
    taskStatus.value = 'failed'
    errorMessage.value = errorDetail?.message || '启动生成任务失败'
    addLog(`错误: ${errorMessage.value}`)
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
        
        if (task.message && task.message !== logs.value[logs.value.length - 1]?.message) {
          addLog(task.message)
        }
      },
      1000
    )
    
    isGenerating.value = false
    
    if (finalTask.status === 'completed') {
      addLog('分镜生成完成！')
      ElMessage.success('分镜生成完成')
      
      await projectStore.refreshProject()
      
      setTimeout(() => {
        handleGoToEdit()
      }, 1500)
      
    } else if (finalTask.status === 'failed') {
      errorMessage.value = finalTask.error || '生成过程中发生未知错误'
      addLog(`生成失败: ${errorMessage.value}`)
      ElMessage.error('分镜生成失败')
    }
    
  } catch (error: any) {
    isGenerating.value = false
    taskStatus.value = 'failed'
    errorMessage.value = error.response?.data?.detail?.message || '获取任务状态失败'
    addLog(`错误: ${errorMessage.value}`)
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
  // 重置状态，允许重新生成
  taskStatus.value = ''
  taskId.value = ''
  progress.value = 0
  progressMessage.value = ''
  errorMessage.value = ''
  logs.value = []
}

function handlePrevStep() {
  projectStore.setStep(2)
  router.push('/step/2')
}

function handleGoToEdit() {
  projectStore.setStep(4)
  router.push('/step/4')
}

function getStatusTagType(status: TaskStatus | ''): 'success' | 'warning' | 'info' | 'danger' {
  const statusMap: Record<string, 'success' | 'warning' | 'info' | 'danger'> = {
    'pending': 'info',
    'running': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return statusMap[status] || 'info'
}

function getStatusText(status: TaskStatus | ''): string {
  const statusMap: Record<string, string> = {
    'pending': '等待中',
    'running': '生成中',
    'completed': '已完成',
    'failed': '失败'
  }
  return statusMap[status] || status
}

function getProgressIconClass(): string {
  if (taskStatus.value === 'completed') return 'success'
  if (taskStatus.value === 'failed') return 'error'
  if (isGenerating.value || taskStatus.value === 'running') return 'running'
  return ''
}

function getProgressSubtitle(): string {
  if (taskStatus.value === 'completed') return '分镜已生成完成'
  if (taskStatus.value === 'failed') return '生成过程中出现问题'
  if (isGenerating.value || taskStatus.value === 'running') return '正在生成中...'
  return '等待开始生成'
}

// Style display names
const styleDisplayNames: Record<string, string> = {
  teaching: '教学',
  nursery_rhyme: '儿歌',
  storybook: '读绘本/故事',
  recitation: '朗诵',
  custom: '自定义'
}

function getStyleDisplayName(style: string): string {
  return styleDisplayNames[style] || style
}
</script>


<style scoped>
.step-storyboard {
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
  color: #409eff;
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

.info-icon {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: #fff;
}

.settings-icon {
  background: linear-gradient(135deg, #e6a23c 0%, #f0b85a 100%);
  color: #fff;
}

.progress-icon {
  background: linear-gradient(135deg, #909399 0%, #b1b3b8 100%);
  color: #fff;
}

.progress-icon.running {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
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

/* Info Grid */
.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-item.full-width {
  grid-column: 1 / -1;
}

.info-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
}

.info-label .el-icon {
  font-size: 14px;
  color: #409eff;
}

.info-value {
  font-size: 15px;
  color: var(--text-primary);
  font-weight: 500;
  padding-left: 20px;
}

.info-value.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.info-value .el-tag {
  border-radius: 20px;
}

.empty-text {
  color: var(--text-muted);
  font-weight: 400;
}

/* Settings */
.setting-item {
  margin-bottom: 20px;
}

.setting-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
  margin-bottom: 16px;
}

.setting-label .el-icon {
  color: #e6a23c;
}

.duration-options {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.duration-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border: 2px solid var(--border-color);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: var(--bg-secondary);
}

.duration-option:hover {
  border-color: #c6e2ff;
  background: rgba(64, 158, 255, 0.05);
  transform: translateY(-2px);
}

.duration-option.is-active {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.1);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.duration-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1;
}

.duration-option.is-active .duration-value {
  color: #409eff;
}

.duration-unit {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.setting-tip {
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

.setting-tip .el-icon {
  font-size: 16px;
  flex-shrink: 0;
  margin-top: 1px;
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
  stroke: url(#progressGradient);
  stroke-width: 8;
  stroke-linecap: round;
  stroke-dasharray: 283;
  transition: stroke-dashoffset 0.5s ease;
}

.progress-ring::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.progress-ring svg {
  filter: drop-shadow(0 4px 12px rgba(64, 158, 255, 0.2));
}

.progress-ring .progress-bar {
  stroke: #409eff;
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
  color: #409eff;
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

/* Buttons in state */
.view-btn,
.retry-btn {
  border-radius: 10px;
  font-weight: 500;
}

.completed-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  max-width: 220px;
}

.completed-actions .el-button {
  width: 100%;
  margin: 0;
}

.regenerate-btn {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.regenerate-btn:hover {
  background: var(--hover-bg);
  border-color: #e6a23c;
  color: #e6a23c;
}

.view-btn {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
  border: none;
}

.view-btn:hover {
  background: linear-gradient(135deg, #529b2e 0%, #67c23a 100%);
}

.retry-btn {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  border: none;
}

.retry-btn:hover {
  background: linear-gradient(135deg, #337ecc 0%, #409eff 100%);
}

/* Log Section */
.log-section {
  border-top: 1px solid var(--border-light);
  padding: 16px 24px 24px;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.log-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.log-title .el-icon {
  color: var(--text-muted);
}

.clear-btn {
  color: var(--text-muted);
  font-size: 12px;
}

.clear-btn:hover {
  color: #f56c6c;
}

.log-content {
  max-height: 160px;
  overflow-y: auto;
  background: var(--bg-secondary);
  border-radius: 10px;
  padding: 14px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
}

.log-content::-webkit-scrollbar {
  width: 6px;
}

.log-content::-webkit-scrollbar-track {
  background: transparent;
}

.log-content::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}

.log-item {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
  line-height: 1.6;
}

.log-item:last-child {
  margin-bottom: 0;
}

.log-time {
  color: var(--text-muted);
  flex-shrink: 0;
}

.log-message {
  color: var(--text-primary);
  word-break: break-all;
}

/* Navigation */
.navigation-buttons {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.nav-btn {
  flex: 1;
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
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  border: none;
}

.generate-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #337ecc 0%, #409eff 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
}

.next-btn {
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
  .step-storyboard {
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
  .step-storyboard {
    padding: 16px;
  }
  
  .page-title {
    font-size: 22px;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .duration-options {
    justify-content: center;
  }
  
  .duration-option {
    width: 60px;
    height: 60px;
  }
  
  .duration-value {
    font-size: 20px;
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
}
</style>
