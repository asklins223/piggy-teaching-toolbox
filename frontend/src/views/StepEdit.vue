<template>
  <div class="step-edit">
    <div class="page-header">
      <h2 class="page-title">
        <el-icon class="title-icon"><EditPen /></el-icon>
        编辑调整
      </h2>
      <p class="page-subtitle">预览和编辑所有分镜内容，可修改描述、旁白，或重新生成图片</p>
    </div>

    <!-- Summary Bar -->
    <div v-if="scenes.length > 0" class="summary-bar">
      <div class="summary-item">
        <div class="summary-icon scenes-icon">
          <el-icon><Film /></el-icon>
        </div>
        <div class="summary-info">
          <span class="summary-value">{{ scenes.length }}</span>
          <span class="summary-label">个分镜</span>
        </div>
      </div>
      <div class="summary-divider"></div>
      <div class="summary-item">
        <div class="summary-icon duration-icon">
          <el-icon><Clock /></el-icon>
        </div>
        <div class="summary-info">
          <span class="summary-value">{{ totalDuration }}</span>
          <span class="summary-label">秒总时长</span>
        </div>
      </div>
      <div class="summary-divider"></div>
      <div class="summary-item">
        <div class="summary-icon status-icon">
          <el-icon><CircleCheck /></el-icon>
        </div>
        <div class="summary-info">
          <span class="summary-value">{{ completedScenes }}</span>
          <span class="summary-label">已完成</span>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <div class="loading-animation">
        <div class="loading-dot"></div>
        <div class="loading-dot"></div>
        <div class="loading-dot"></div>
      </div>
      <p>加载分镜数据中...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="scenes.length === 0" class="empty-container">
      <div class="empty-icon">
        <el-icon><Film /></el-icon>
      </div>
      <h4>暂无分镜数据</h4>
      <p>请先生成分镜脚本和图片</p>
      <el-button type="primary" @click="goToStoryboard" class="empty-btn">
        <el-icon><VideoPlay /></el-icon>
        去生成分镜
      </el-button>
    </div>

    <!-- Scene Cards -->
    <template v-else>
      <div class="scenes-grid">
        <SceneCard
          v-for="scene in scenes"
          :key="scene.scene_id"
          :ref="(el) => setSceneCardRef(scene.scene_id, el)"
          :scene="scene"
          :project-id="projectStore.currentProjectId"
          @update="handleUpdateScene"
          @regenerate="handleRegenerateImage"
        />
      </div>
    </template>

    <!-- Navigation Buttons -->
    <div class="navigation-buttons">
      <el-button @click="handlePrevStep" size="large" class="nav-btn prev-btn">
        <el-icon><ArrowLeft /></el-icon>
        上一步
      </el-button>
      <el-button 
        type="primary" 
        @click="handleNextStep" 
        :disabled="scenes.length === 0"
        size="large"
        class="nav-btn next-btn"
      >
        下一步：生成音频
        <el-icon><ArrowRight /></el-icon>
      </el-button>
    </div>

    <!-- Regenerate Progress Dialog -->
    <el-dialog
      v-model="showRegenerateDialog"
      title=""
      width="420px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="regenerateStatus === 'completed' || regenerateStatus === 'failed'"
      class="regenerate-dialog"
    >
      <div class="dialog-content">
        <template v-if="regenerateStatus === 'running' || regenerateStatus === 'pending'">
          <div class="dialog-icon running">
            <el-icon class="is-loading"><Loading /></el-icon>
          </div>
          <h3>正在生成图片</h3>
          <el-progress
            :percentage="regenerateProgress"
            :stroke-width="10"
            :show-text="false"
            class="dialog-progress"
          />
          <p class="dialog-message">{{ regenerateMessage || '请稍候...' }}</p>
        </template>
        <template v-else-if="regenerateStatus === 'completed'">
          <div class="dialog-icon success">
            <el-icon><CircleCheck /></el-icon>
          </div>
          <h3>生成完成</h3>
          <p class="dialog-message">图片已重新生成</p>
        </template>
        <template v-else-if="regenerateStatus === 'failed'">
          <div class="dialog-icon error">
            <el-icon><CircleClose /></el-icon>
          </div>
          <h3>生成失败</h3>
          <p class="dialog-message error-text">{{ regenerateError }}</p>
        </template>
      </div>
      <template #footer v-if="regenerateStatus === 'completed' || regenerateStatus === 'failed'">
        <el-button type="primary" @click="closeRegenerateDialog" class="dialog-btn">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  Loading, 
  ArrowLeft, 
  ArrowRight, 
  EditPen, 
  Film, 
  Clock, 
  CircleCheck,
  CircleClose,
  VideoPlay
} from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'
import SceneCard from '@/components/SceneCard.vue'
import * as storyboardApi from '@/api/storyboard'
import * as tasksApi from '@/api/tasks'
import type { Scene, UpdateSceneRequest } from '@/api/storyboard'
import type { TaskStatus } from '@/api/tasks'

const router = useRouter()
const projectStore = useProjectStore()

// State
const loading = ref(false)
const scenes = ref<Scene[]>([])
const sceneCardRefs = ref<Record<string, any>>({})

// Regenerate dialog state
const showRegenerateDialog = ref(false)
const regenerateTaskId = ref('')
const regenerateSceneId = ref('')
const regenerateStatus = ref<TaskStatus | ''>('')
const regenerateProgress = ref(0)
const regenerateMessage = ref('')
const regenerateError = ref('')

// Computed
const totalDuration = computed(() => {
  return scenes.value.reduce((sum, scene) => sum + (scene.duration || 0), 0)
})

const completedScenes = computed(() => {
  return scenes.value.filter(s => s.image_url).length
})

// Methods
function setSceneCardRef(sceneId: string, el: any) {
  if (el) {
    sceneCardRefs.value[sceneId] = el
  }
}

async function loadScenes(preserveScroll = false) {
  if (!projectStore.currentProjectId) {
    return
  }

  // 保存当前滚动位置
  const scrollTop = preserveScroll ? window.scrollY : 0

  loading.value = !preserveScroll // 只在非保持滚动时显示loading
  try {
    const response = await storyboardApi.getScenes(projectStore.currentProjectId)
    scenes.value = response.scenes
    
    // 恢复滚动位置
    if (preserveScroll) {
      requestAnimationFrame(() => {
        window.scrollTo(0, scrollTop)
      })
    }
  } catch (error: any) {
    ElMessage.error('加载分镜数据失败')
  } finally {
    loading.value = false
  }
}

async function handleUpdateScene(sceneId: string, data: UpdateSceneRequest) {
  if (!projectStore.currentProjectId) return

  try {
    const response = await storyboardApi.updateScene(
      projectStore.currentProjectId,
      sceneId,
      data
    )
    const index = scenes.value.findIndex(s => s.scene_id === sceneId)
    if (index !== -1) {
      scenes.value[index] = response.scene
    }
  } catch (error: any) {
    ElMessage.error('更新分镜失败')
  }
}

async function handleRegenerateImage(sceneId: string) {
  if (!projectStore.currentProjectId) return

  regenerateSceneId.value = sceneId
  regenerateStatus.value = 'pending'
  regenerateProgress.value = 0
  regenerateMessage.value = '正在启动图片生成任务...'
  regenerateError.value = ''
  showRegenerateDialog.value = true

  try {
    const response = await storyboardApi.regenerateSceneImage(
      projectStore.currentProjectId,
      sceneId
    )
    regenerateTaskId.value = response.task_id
    await pollRegenerateTask()
  } catch (error: any) {
    regenerateStatus.value = 'failed'
    regenerateError.value = error.response?.data?.detail?.message || '启动任务失败'
    resetSceneCardState(sceneId)
  }
}

async function pollRegenerateTask() {
  try {
    const finalTask = await tasksApi.pollTaskStatus(
      regenerateTaskId.value,
      (task) => {
        regenerateStatus.value = task.status
        regenerateProgress.value = task.progress
        regenerateMessage.value = task.message
      },
      1000
    )

    if (finalTask.status === 'completed') {
      await loadScenes(true) // 保持滚动位置
      ElMessage.success('图片重新生成完成')
    } else if (finalTask.status === 'failed') {
      regenerateError.value = finalTask.error || '生成失败'
    }
  } catch (error: any) {
    regenerateStatus.value = 'failed'
    regenerateError.value = error.response?.data?.detail?.message || '获取任务状态失败'
  } finally {
    resetSceneCardState(regenerateSceneId.value)
  }
}

function resetSceneCardState(sceneId: string) {
  const cardRef = sceneCardRefs.value[sceneId]
  if (cardRef && cardRef.resetRegeneratingState) {
    cardRef.resetRegeneratingState()
  }
}

function closeRegenerateDialog() {
  showRegenerateDialog.value = false
  regenerateTaskId.value = ''
  regenerateSceneId.value = ''
  regenerateStatus.value = ''
  regenerateProgress.value = 0
  regenerateMessage.value = ''
  regenerateError.value = ''
}

function goToStoryboard() {
  projectStore.setStep(3)
  router.push('/step/3')
}

function handlePrevStep() {
  projectStore.setStep(3)
  router.push('/step/3')
}

function handleNextStep() {
  projectStore.setStep(5)
  router.push('/step/5')
}

// Lifecycle
onMounted(() => {
  loadScenes()
})

watch(() => projectStore.currentProjectId, (newId) => {
  if (newId) {
    loadScenes()
  }
})
</script>

<style scoped>
.step-edit {
  padding: 32px;
  max-width: 1200px;
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
  color: #67c23a;
  font-size: 32px;
}

.page-subtitle {
  color: var(--text-muted);
  font-size: 15px;
  margin: 0;
}

/* Summary Bar */
.summary-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 32px;
  padding: 20px 32px;
  background: var(--bg-card);
  border-radius: 16px;
  box-shadow: var(--shadow-md);
  margin-bottom: 32px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.summary-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.scenes-icon {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: #fff;
}

.duration-icon {
  background: linear-gradient(135deg, #e6a23c 0%, #f0b85a 100%);
  color: #fff;
}

.status-icon {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
  color: #fff;
}

.summary-info {
  display: flex;
  flex-direction: column;
}

.summary-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.summary-label {
  font-size: 13px;
  color: var(--text-muted);
}

.summary-divider {
  width: 1px;
  height: 40px;
  background: var(--border-color);
}

/* Loading State */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: var(--text-muted);
}

.loading-animation {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.loading-dot {
  width: 12px;
  height: 12px;
  background: #409eff;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.loading-dot:nth-child(1) { animation-delay: -0.32s; }
.loading-dot:nth-child(2) { animation-delay: -0.16s; }
.loading-dot:nth-child(3) { animation-delay: 0s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.loading-container p {
  margin: 0;
  font-size: 15px;
}

/* Empty State */
.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  background: var(--bg-secondary);
  border-radius: 16px;
  margin-bottom: 32px;
}

.empty-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  background: var(--bg-card);
  color: var(--text-muted);
  margin-bottom: 20px;
}

.empty-container h4 {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.empty-container p {
  margin: 0 0 24px 0;
  font-size: 14px;
  color: var(--text-muted);
}

.empty-btn {
  border-radius: 10px;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  border: none;
  font-weight: 500;
}

.empty-btn:hover {
  background: linear-gradient(135deg, #337ecc 0%, #409eff 100%);
}

/* Scenes Grid */
.scenes-grid {
  display: flex;
  flex-direction: column;
  gap: 24px;
  margin-bottom: 32px;
}

/* Navigation */
.navigation-buttons {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding-top: 24px;
  border-top: 1px solid var(--border-light);
}

.nav-btn {
  min-width: 160px;
  border-radius: 12px;
  font-weight: 500;
  height: 48px;
}

.prev-btn {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.prev-btn:hover {
  background: var(--hover-bg);
  border-color: var(--border-color);
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

.next-btn:disabled {
  background: var(--bg-secondary);
  color: var(--text-muted);
}

/* Dialog */
.regenerate-dialog :deep(.el-dialog) {
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.regenerate-dialog :deep(.el-dialog__header) {
  display: none;
}

.regenerate-dialog :deep(.el-dialog__body) {
  padding: 48px 40px 32px;
  background: linear-gradient(180deg, #f8faff 0%, #ffffff 100%);
}

.regenerate-dialog :deep(.el-dialog__footer) {
  padding: 0 40px 40px;
  border-top: none;
  background: #ffffff;
}

.dialog-content {
  text-align: center;
}

.dialog-icon {
  width: 88px;
  height: 88px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  margin: 0 auto 24px;
  position: relative;
}

.dialog-icon.running {
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.15) 0%, rgba(102, 177, 255, 0.25) 100%);
  color: #409eff;
  box-shadow: 0 8px 24px rgba(64, 158, 255, 0.2);
}

.dialog-icon.running::before {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 2px solid transparent;
  border-top-color: #409eff;
  animation: spin-ring 1.5s linear infinite;
}

@keyframes spin-ring {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.dialog-icon.success {
  background: linear-gradient(135deg, rgba(103, 194, 58, 0.15) 0%, rgba(149, 212, 117, 0.25) 100%);
  color: #67c23a;
  box-shadow: 0 8px 24px rgba(103, 194, 58, 0.2);
}

.dialog-icon.error {
  background: linear-gradient(135deg, rgba(245, 108, 108, 0.15) 0%, rgba(250, 152, 152, 0.25) 100%);
  color: #f56c6c;
  box-shadow: 0 8px 24px rgba(245, 108, 108, 0.2);
}

.dialog-content h3 {
  margin: 0 0 20px 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.5px;
}

.dialog-progress {
  margin-bottom: 20px;
  padding: 0 20px;
}

.dialog-progress :deep(.el-progress-bar__outer) {
  border-radius: 12px;
  background: rgba(64, 158, 255, 0.1);
  height: 8px !important;
}

.dialog-progress :deep(.el-progress-bar__inner) {
  border-radius: 12px;
  background: linear-gradient(90deg, #409eff 0%, #66b1ff 50%, #409eff 100%);
  background-size: 200% 100%;
  animation: progress-shine 2s ease-in-out infinite;
}

@keyframes progress-shine {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.dialog-message {
  margin: 0;
  font-size: 14px;
  color: var(--text-muted);
  line-height: 1.6;
}

.dialog-message.error-text {
  color: #f56c6c;
}

.dialog-btn {
  width: 100%;
  border-radius: 12px;
  height: 48px;
  font-size: 15px;
  font-weight: 500;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  border: none;
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.3);
  transition: all 0.3s ease;
}

.dialog-btn:hover {
  background: linear-gradient(135deg, #337ecc 0%, #409eff 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(64, 158, 255, 0.4);
}

/* Loading animation */
.is-loading {
  animation: rotating 1.5s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .step-edit {
    padding: 16px;
  }
  
  .page-title {
    font-size: 22px;
  }
  
  .summary-bar {
    flex-direction: column;
    gap: 16px;
    padding: 20px;
  }
  
  .summary-divider {
    width: 60px;
    height: 1px;
  }
  
  .navigation-buttons {
    flex-direction: column;
  }
  
  .nav-btn {
    width: 100%;
  }
}
</style>
