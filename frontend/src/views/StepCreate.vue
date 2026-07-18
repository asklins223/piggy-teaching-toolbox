<template>
  <div class="step-create">
    <div class="page-header">
      <h2 class="page-title">
        <el-icon class="title-icon"><Edit /></el-icon>
        开始创作
      </h2>
      <p class="page-subtitle">创建新项目或继续已有项目</p>
    </div>
    
    <!-- 当前项目提示 -->
    <div v-if="hasCurrentProject" class="current-project-banner">
      <div class="banner-content">
        <el-icon class="banner-icon"><InfoFilled /></el-icon>
        <div class="banner-text">
          <span class="banner-title">当前有进行中的项目</span>
          <span class="banner-topic">{{ projectStore.projectData?.goal?.topic }}</span>
          <span v-if="currentProjectStyle" class="banner-style">
            <el-tag size="small" type="info" effect="plain">{{ currentProjectStyle }}</el-tag>
          </span>
        </div>
      </div>
      <div class="banner-actions">
        <el-button type="primary" @click="handleContinueProject">
          <el-icon><Right /></el-icon>
          继续编辑
        </el-button>
        <el-button @click="handleStartNew">
          <el-icon><Plus /></el-icon>
          创建新项目
        </el-button>
      </div>
    </div>

    <!-- Step 1: Choose Video Style -->
    <div v-if="currentStep === 1" class="step-content">
      <el-row :gutter="32" class="content-row">
        <!-- Left: Video Style Selection -->
        <el-col :xs="24" :lg="14">
          <div class="card style-card">
            <div class="card-header">
              <div class="header-icon style-icon">
                <el-icon><Film /></el-icon>
              </div>
              <div class="header-text">
                <h3>选择视频风格</h3>
                <span>不同风格适用于不同的教学场景和受众</span>
              </div>
            </div>
            <div class="style-content">
              <StyleSelector 
                v-model="form.style"
                v-model:custom-description="form.customStyleDescription"
              />
            </div>
          </div>
        </el-col>
        
        <!-- Right: Load Existing Project -->
        <el-col :xs="24" :lg="10">
          <div class="card projects-card">
            <div class="card-header">
              <div class="header-icon projects-icon">
                <el-icon><FolderOpened /></el-icon>
              </div>
              <div class="header-text">
                <h3>已有项目</h3>
                <span>选择一个项目继续编辑</span>
              </div>
              <el-button 
                text 
                class="refresh-btn"
                @click="handleRefreshProjects"
                :disabled="loadingProjects"
              >
                <el-icon :class="{ 'is-loading': loadingProjects }">
                  <Loading v-if="loadingProjects" />
                  <Refresh v-else />
                </el-icon>
              </el-button>
            </div>
            
            <div class="projects-content">
              <div v-if="loadingProjects" class="loading-container">
                <el-icon class="is-loading loading-icon"><Loading /></el-icon>
                <span>加载项目列表...</span>
              </div>
              
              <div v-else-if="projectList.length === 0" class="empty-container">
                <el-icon class="empty-icon"><Folder /></el-icon>
                <p>暂无项目</p>
                <span>创建你的第一个项目吧</span>
              </div>
              
              <div v-else class="project-list">
                <div 
                  v-for="project in projectList" 
                  :key="project.project_id"
                  class="project-item"
                  :class="{ 'is-selected': selectedProjectId === project.project_id }"
                  @click="selectedProjectId = project.project_id"
                >
                  <div class="project-checkbox">
                    <el-icon v-if="selectedProjectId === project.project_id" class="check-icon"><Select /></el-icon>
                  </div>
                  <div class="project-info">
                    <div class="project-topic">{{ project.topic }}</div>
                    <div class="project-meta">
                      <el-tag size="small" :type="getStatusType(project.status)" effect="light" round>
                        {{ getStatusText(project.status) }}
                      </el-tag>
                      <el-tag 
                        v-if="project.style" 
                        size="small" 
                        type="warning" 
                        effect="light" 
                        round
                        class="style-tag"
                      >
                        {{ getStyleDisplayName(project.style) }}
                      </el-tag>
                      <span class="project-date">
                        <el-icon><Clock /></el-icon>
                        {{ formatDate(project.created_at) }}
                      </span>
                    </div>
                  </div>
                  <el-button 
                    type="danger" 
                    size="small" 
                    text
                    class="delete-btn"
                    @click.stop="handleDeleteProject(project.project_id)"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </div>
            </div>
            
            <div class="load-button-container">
              <el-button 
                type="primary" 
                @click="handleLoadProject"
                :disabled="!selectedProjectId || loading || loadingProject"
                size="large"
                class="load-btn"
              >
                <el-icon :class="{ 'is-loading': loadingProject }">
                  <Loading v-if="loadingProject" />
                  <Upload v-else />
                </el-icon>
                {{ loadingProject ? '加载中...' : '加载选中项目' }}
              </el-button>
            </div>
          </div>
          
          <!-- Next Step Button -->
          <div class="create-project-section standalone">
            <el-button 
              type="primary" 
              @click="handleNextStep"
              :disabled="loading"
              size="large"
              class="create-project-btn standalone"
            >
              <el-icon><ArrowRight /></el-icon>
              下一步
            </el-button>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- Step 2: Create Project -->
    <div v-else-if="currentStep === 2" class="step-content">
      <el-row :gutter="32" class="content-row">
        <!-- Left: Create New Project -->
        <el-col :xs="24" :lg="14">
          <div class="card create-card">
            <div class="card-header">
              <div class="header-icon create-icon">
                <el-icon><Plus /></el-icon>
              </div>
              <div class="header-text">
                <h3>创建新项目</h3>
                <span>填写项目信息，AI 将帮助你生成教学视频</span>
              </div>
            </div>
            
            <el-form 
              ref="formRef"
              :model="form" 
              :rules="rules" 
              label-position="top"
              class="create-form"
            >
              <el-form-item label="教学主题" prop="topic" class="form-item-custom">
                <template #label>
                  <span class="form-label">
                    <el-icon><Document /></el-icon>
                    教学主题
                  </span>
                </template>
                <div class="input-wrapper">
                  <el-input 
                    v-model="form.topic" 
                    placeholder="例如：小学英语，厨房用品"
                    :disabled="loading"
                    size="large"
                  />
                  <el-button 
                    @click="handleOptimizeTopic"
                    :disabled="!form.topic.trim() || loading || optimizingTopic"
                    class="input-ai-btn"
                    link
                  >
                    <el-icon :class="{ 'is-loading': optimizingTopic }">
                      <Loading v-if="optimizingTopic" />
                      <MagicStick v-else />
                    </el-icon>
                    AI 优化
                  </el-button>
                </div>
              </el-form-item>
              
              <el-form-item label="目标受众" prop="targetAudience" class="form-item-custom">
                <template #label>
                  <span class="form-label">
                    <el-icon><User /></el-icon>
                    目标受众
                  </span>
                </template>
                <div class="input-wrapper">
                  <el-input 
                    v-model="form.targetAudience" 
                    placeholder="例如：小学生、大学生、职场人士"
                    :disabled="loading"
                    size="large"
                  />
                  <el-button 
                    @click="handleSuggestAudience"
                    :disabled="!form.topic.trim() || loading || suggestingAudience"
                    class="input-ai-btn"
                    link
                  >
                    <el-icon :class="{ 'is-loading': suggestingAudience }">
                      <Loading v-if="suggestingAudience" />
                      <Aim v-else />
                    </el-icon>
                    AI 推荐
                  </el-button>
                </div>
              </el-form-item>
              
              <el-form-item label="关键知识点" class="form-item-custom">
                <template #label>
                  <span class="form-label">
                    <el-icon><Collection /></el-icon>
                    关键知识点
                    <span class="label-hint">（可选）</span>
                  </span>
                </template>
                <div class="input-wrapper textarea">
                  <el-input 
                    v-model="form.keyPoints" 
                    type="textarea"
                    :rows="3"
                    placeholder="用逗号分隔，例如：变量定义, 数据类型, 条件语句"
                    :disabled="loading"
                  />
                  <el-button 
                    @click="handleSuggestKeyPoints"
                    :disabled="!form.topic.trim() || loading || suggestingKeyPoints"
                    class="input-ai-btn textarea-btn"
                    link
                  >
                    <el-icon :class="{ 'is-loading': suggestingKeyPoints }">
                      <Loading v-if="suggestingKeyPoints" />
                      <Promotion v-else />
                    </el-icon>
                    AI 推荐
                  </el-button>
                </div>
              </el-form-item>
              
              <div class="form-actions-top">
                <el-button 
                  @click="handleRandomTopic"
                  :disabled="loading || generatingRandom"
                  class="random-btn"
                  size="large"
                >
                  <el-icon :class="{ 'is-loading': generatingRandom }">
                    <Loading v-if="generatingRandom" />
                    <MagicStick v-else />
                  </el-icon>
                  {{ generatingRandom ? '想鬼点子中...' : '想不到要做啥了吗，点我点我！！' }}
                </el-button>
              </div>
            </el-form>
          </div>
        </el-col>
        
        <!-- Right: Selected Style and Create Button -->
        <el-col :xs="24" :lg="10">
          <div class="right-column">
            <!-- Selected Style Display -->
            <div class="card selected-style-card">
              <div class="card-header">
                <div class="header-icon style-icon">
                  <el-icon><Film /></el-icon>
                </div>
                <div class="header-text">
                  <h3>已选择风格</h3>
                  <span>{{ getStyleDisplayName(form.style) }}</span>
                </div>
                <el-button 
                  text 
                  class="refresh-btn"
                  @click="handleBackToStyleSelection"
                >
                  <el-icon><Edit /></el-icon>
                </el-button>
              </div>
              <div class="selected-style-content">
                <div class="style-preview">
                  <div class="style-name">{{ getStyleDisplayName(form.style) }}</div>
                  <div class="style-description">{{ getStyleDescription(form.style) }}</div>
                  <div v-if="form.style === 'custom' && form.customStyleDescription" class="custom-description">
                    <strong>自定义描述：</strong>{{ form.customStyleDescription }}
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Navigation Buttons -->
            <div class="step-navigation">
              <el-button 
                @click="handleBackToStyleSelection"
                size="large"
                class="back-btn"
              >
                <el-icon><ArrowLeft /></el-icon>
                返回上一步
              </el-button>
              
              <el-button 
                type="primary" 
                @click="handleNextStepOrCreate"
                :disabled="loading || creating"
                size="large"
                class="create-project-btn final"
              >
                <el-icon :class="{ 'is-loading': creating }">
                  <Loading v-if="creating" />
                  <ArrowRight v-else-if="hasCurrentProject" />
                  <VideoPlay v-else />
                </el-icon>
                {{ creating ? '创建中...' : (hasCurrentProject ? '下一步' : '创建项目') }}
              </el-button>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { 
  MagicStick, Promotion, Refresh, Delete, Loading, User, 
  Plus, FolderOpened, Edit, Document, Collection, VideoPlay,
  Folder, Clock, Select, Upload, Aim, InfoFilled, Right, Film,
  ArrowRight, ArrowLeft
} from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'
import * as projectsApi from '@/api/projects'
import type { ProjectSummary } from '@/api/projects'
import StyleSelector from '@/components/StyleSelector.vue'

const router = useRouter()
const projectStore = useProjectStore()

// Form
const formRef = ref<FormInstance>()
const form = reactive({
  topic: '',
  targetAudience: '',
  keyPoints: '',
  style: 'teaching',
  customStyleDescription: ''
})

const rules: FormRules = {
  topic: [
    { required: true, message: '请输入教学主题', trigger: 'blur' },
    { min: 2, message: '主题至少需要2个字符', trigger: 'blur' }
  ],
  targetAudience: [
    { required: true, message: '请输入目标受众', trigger: 'blur' }
  ]
}

// State
const loading = computed(() => creating.value || loadingProject.value)
const creating = ref(false)
const loadingProjects = ref(false)
const loadingProject = ref(false)
const optimizingTopic = ref(false)
const suggestingAudience = ref(false)
const suggestingKeyPoints = ref(false)
const generatingRandom = ref(false)

// Step control
const currentStep = ref(1) // 1: 选择风格, 2: 创建项目

// Project list
const projectList = ref<ProjectSummary[]>([])
const selectedProjectId = ref('')

// 是否有当前进行中的项目
const hasCurrentProject = computed(() => {
  return !!projectStore.currentProjectId && !!projectStore.projectData
})

// 当前项目的风格显示名称
const styleDisplayNames: Record<string, string> = {
  teaching: '教学',
  nursery_rhyme: '儿歌',
  storybook: '读绘本/故事',
  recitation: '朗诵',
  custom: '自定义'
}

const styleDescriptions: Record<string, string> = {
  teaching: '知识讲解、循序渐进、互动问答',
  nursery_rhyme: '韵律节奏、重复记忆、欢快氛围',
  storybook: '故事情节、角色对话、情感起伏',
  recitation: '情感表达、节奏把控、意境营造',
  custom: '根据您的描述自定义风格'
}

const currentProjectStyle = computed(() => {
  const style = projectStore.projectData?.goal?.style
  if (!style) return null
  return styleDisplayNames[style] || style
})

// Helper functions
function getStyleDisplayName(style: string): string {
  return styleDisplayNames[style] || style
}

function getStyleDescription(style: string): string {
  return styleDescriptions[style] || ''
}

// Step navigation
function handleNextStep() {
  currentStep.value = 2
}

function handleBackToStyleSelection() {
  currentStep.value = 1
}

// 继续当前项目
function handleContinueProject() {
  const step = projectStore.maxStep
  projectStore.setStep(step)
  router.push(`/step/${step}`)
}

// 开始新项目（清除当前项目）
function handleStartNew() {
  // 清除项目状态
  projectStore.reset()
  
  // 清空表单数据
  form.topic = ''
  form.targetAudience = ''
  form.keyPoints = ''
  form.style = 'teaching'
  form.customStyleDescription = ''
  
  // 跳转到第一步
  currentStep.value = 1
  
  ElMessage.info('已清除当前项目，可以创建新项目了')
}

// 监听项目数据变化，自动填充表单
watch(() => projectStore.projectData, (newData) => {
  // 只有当有项目数据且不是刚刚清空的情况下才填充表单
  if (newData && newData.goal && projectStore.currentProjectId) {
    form.topic = newData.goal.topic || ''
    form.targetAudience = newData.goal.target_audience || ''
    form.keyPoints = newData.goal.key_points?.join(', ') || ''
    form.style = newData.goal.style || 'teaching'
    form.customStyleDescription = newData.goal.custom_style_description || ''
    
    // 如果有项目数据，显示第二步
    if (currentStep.value === 1) {
      currentStep.value = 2
    }
  }
}, { immediate: true, deep: true })

// Load project list on mount
onMounted(async () => {
  resetAllLoadingStates() // 确保所有loading状态都是false
  
  // 只有当有当前项目且项目数据存在时，才显示第二步并预填充数据
  if (hasCurrentProject.value && projectStore.projectData && projectStore.currentProjectId) {
    currentStep.value = 2
    // 预填充表单数据
    const projectData = projectStore.projectData
    form.topic = projectData.goal?.topic || ''
    form.targetAudience = projectData.goal?.target_audience || ''
    form.keyPoints = projectData.goal?.key_points?.join(', ') || ''
    form.style = projectData.goal?.style || 'teaching'
    form.customStyleDescription = projectData.goal?.custom_style_description || ''
  } else {
    // 没有项目时，确保显示第一步并清空表单
    currentStep.value = 1
    form.topic = ''
    form.targetAudience = ''
    form.keyPoints = ''
    form.style = 'teaching'
    form.customStyleDescription = ''
  }
  
  await loadProjectList()
})

async function loadProjectList() {
  loadingProjects.value = true
  try {
    const response = await projectsApi.listProjects()
    projectList.value = response.projects.sort((a, b) => 
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail?.message || '加载项目列表失败')
  } finally {
    loadingProjects.value = false
  }
}

async function handleRefreshProjects() {
  await loadProjectList()
}

async function handleOptimizeTopic() {
  if (!form.topic.trim()) {
    ElMessage.warning('请先输入主题')
    return
  }
  
  optimizingTopic.value = true
  try {
    const response = await projectsApi.optimizeTopic(form.topic)
    form.topic = response.optimized_topic
    ElMessage.success(response.message)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail?.message || '优化主题失败')
  } finally {
    optimizingTopic.value = false
  }
}

async function handleSuggestAudience() {
  if (!form.topic.trim()) {
    ElMessage.warning('请先输入主题')
    return
  }
  
  suggestingAudience.value = true
  try {
    const response = await projectsApi.suggestAudience(form.topic)
    form.targetAudience = response.target_audience
    ElMessage.success('已推荐目标受众')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail?.message || '推荐受众失败')
  } finally {
    suggestingAudience.value = false
  }
}

async function handleSuggestKeyPoints() {
  if (!form.topic.trim()) {
    ElMessage.warning('请先输入主题')
    return
  }
  
  suggestingKeyPoints.value = true
  try {
    const response = await projectsApi.suggestKeyPoints(form.topic, form.targetAudience)
    form.keyPoints = response.key_points.join(', ')
    ElMessage.success(response.message)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail?.message || '推荐知识点失败')
  } finally {
    suggestingKeyPoints.value = false
  }
}

async function handleRandomTopic() {
  if (generatingRandom.value) return // 防止重复点击
  
  generatingRandom.value = true
  
  try {
    // 传递当前选择的风格和自定义描述
    const response = await projectsApi.generateRandomTopic(
      form.style,
      form.style === 'custom' ? form.customStyleDescription : undefined
    )
    form.topic = response.topic
    form.targetAudience = response.target_audience
    form.keyPoints = response.key_points.join(', ')
    ElMessage.success(`已生成${getStyleDisplayName(form.style)}风格的随机主题`)
  } catch (error: any) {
    console.error('Random topic generation failed:', error)
    ElMessage.error(error.response?.data?.detail?.message || '生成随机主题失败')
  }
  
  // 确保状态重置
  generatingRandom.value = false
}

// 重置所有loading状态的辅助函数
function resetAllLoadingStates() {
  creating.value = false
  loadingProject.value = false
  optimizingTopic.value = false
  suggestingAudience.value = false
  suggestingKeyPoints.value = false
  generatingRandom.value = false
}

async function handleCreateProject() {
  if (!formRef.value) return
  
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  creating.value = true
  try {
    // Parse key points from comma-separated string
    const keyPoints = form.keyPoints
      .split(/[,，]/)
      .map(kp => kp.trim())
      .filter(kp => kp.length > 0)
    
    const projectId = await projectStore.createProject(
      form.topic,
      form.targetAudience,
      keyPoints,
      form.style,
      form.style === 'custom' ? form.customStyleDescription : undefined
    )
    
    if (projectId) {
      ElMessage.success('项目创建成功')
      // Navigate to step 2
      projectStore.setStep(2)
      router.push('/step/2')
    } else {
      ElMessage.error(projectStore.error || '创建项目失败')
    }
  } finally {
    creating.value = false
  }
}

function handleNextStepOrCreate() {
  if (hasCurrentProject.value) {
    // 如果已有项目，直接跳转到下一步
    const nextStep = projectStore.maxStep
    projectStore.setStep(nextStep)
    router.push(`/step/${nextStep}`)
  } else {
    // 如果没有项目，创建新项目
    handleCreateProject()
  }
}

async function handleLoadProject() {
  if (!selectedProjectId.value) {
    ElMessage.warning('请先选择一个项目')
    return
  }
  
  loadingProject.value = true
  try {
    const success = await projectStore.loadProject(selectedProjectId.value)
    if (success) {
      ElMessage.success('项目加载成功')
      // 直接跳转到项目对应的步骤，而不是停留在创建页面
      const step = projectStore.maxStep
      projectStore.setStep(step)
      router.push(`/step/${step}`)
    } else {
      ElMessage.error(projectStore.error || '加载项目失败')
    }
  } finally {
    loadingProject.value = false
  }
}

async function handleDeleteProject(projectId: string) {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个项目吗？此操作不可恢复。',
      '删除确认',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const success = await projectStore.deleteProject(projectId)
    if (success) {
      ElMessage.success('项目已删除')
      // Remove from local list
      projectList.value = projectList.value.filter(p => p.project_id !== projectId)
      if (selectedProjectId.value === projectId) {
        selectedProjectId.value = ''
      }
    } else {
      ElMessage.error(projectStore.error || '删除项目失败')
    }
  } catch {
    // User cancelled
  }
}

// Helper functions
function getStatusType(status: string): 'success' | 'warning' | 'info' | 'primary' | 'danger' {
  const statusMap: Record<string, 'success' | 'warning' | 'info' | 'primary' | 'danger'> = {
    'initialized': 'info',
    'storyboard_ready': 'warning',
    'images_generating': 'warning',
    'images_ready': 'warning',
    'audio_generating': 'primary',
    'audio_ready': 'primary',
    'subtitles_ready': 'primary',
    'completed': 'success'
  }
  return statusMap[status] || 'info'
}

function getStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    'initialized': '已创建',
    'storyboard_ready': '分镜就绪',
    'images_generating': '图片生成中',
    'images_ready': '图片就绪',
    'audio_generating': '音频生成中',
    'audio_ready': '音频就绪',
    'subtitles_ready': '字幕就绪',
    'completed': '已完成'
  }
  return statusMap[status] || status
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>
<style scoped>
.step-create {
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
  align-items: stretch;
}

.content-row .el-col {
  display: flex;
  flex-direction: column;
}

/* Current Project Banner */
.current-project-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  margin-bottom: 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.banner-icon {
  font-size: 24px;
  color: #409eff;
}

.banner-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.banner-title {
  font-size: 14px;
  color: var(--text-secondary);
}

.banner-topic {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.banner-style {
  margin-top: 4px;
}

.banner-actions {
  display: flex;
  gap: 12px;
}

/* Card Styles */
.card {
  background: var(--bg-card);
  border-radius: 16px;
  box-shadow: var(--shadow-md);
  overflow: hidden;
  transition: box-shadow 0.3s ease, background-color 0.3s ease;
}

.card:hover {
  box-shadow: var(--shadow-lg);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px 28px;
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-secondary);
}

.header-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.create-icon {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: #fff;
}

.style-icon {
  background: linear-gradient(135deg, #e6a23c 0%, #f0b85a 100%);
  color: #fff;
}

.projects-icon {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
  color: #fff;
}

.header-text {
  flex: 1;
}

.header-text h3 {
  margin: 0 0 4px 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-text span {
  font-size: 13px;
  color: var(--text-muted);
}

.refresh-btn {
  color: var(--text-muted);
  font-size: 18px;
}

.refresh-btn:hover {
  color: #409eff;
}

/* Style Card */
.style-card {
  height: fit-content;
}

.style-content {
  padding: 20px 24px;
}

/* Selected Style Card */
.selected-style-card {
  height: fit-content;
  margin-bottom: 20px;
}

.selected-style-content {
  padding: 20px 24px;
}

.style-preview {
  text-align: center;
}

.style-name {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.style-description {
  font-size: 14px;
  color: var(--text-muted);
  margin-bottom: 12px;
}

.custom-description {
  font-size: 13px;
  color: var(--text-secondary);
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
  text-align: left;
}

/* Create Form */
.create-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.create-form {
  padding: 28px;
  flex: 1;
}

.form-item-custom {
  margin-bottom: 24px;
}

.form-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  color: var(--text-primary);
}

.form-label .el-icon {
  color: #409eff;
}

.label-hint {
  font-weight: 400;
  color: var(--text-muted);
  font-size: 12px;
}

.input-wrapper {
  position: relative;
  width: 100%;
}

.input-wrapper :deep(.el-input),
.input-wrapper :deep(.el-textarea) {
  width: 100%;
}

.input-wrapper :deep(.el-input__wrapper),
.input-wrapper :deep(.el-textarea__inner) {
  border-radius: 10px;
  box-shadow: 0 0 0 1px #dcdfe6 inset;
  transition: all 0.3s ease;
}

.input-wrapper :deep(.el-input__wrapper:hover),
.input-wrapper :deep(.el-textarea__inner:hover) {
  box-shadow: 0 0 0 1px #c0c4cc inset;
}

.input-wrapper :deep(.el-input__wrapper:focus-within),
.input-wrapper :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px #409eff inset;
}

/* AI Button inside input */
.input-ai-btn {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #409eff;
  font-size: 13px;
  font-weight: 500;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 6px;
  z-index: 1;
}

.input-ai-btn:hover:not(:disabled) {
  color: #66b1ff;
  background: rgba(64, 158, 255, 0.1);
}

.input-ai-btn:disabled {
  color: #c0c4cc;
}

.input-ai-btn .el-icon {
  margin-right: 2px;
}

/* Textarea AI button position */
.input-wrapper.textarea .input-ai-btn {
  top: auto;
  bottom: 10px;
  transform: none;
}

.input-ai-btn.textarea-btn {
  top: auto;
  bottom: 10px;
  transform: none;
}

/* Form Actions */
.form-actions-top {
  display: flex;
  justify-content: center;
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px dashed var(--border-color);
}

.random-btn {
  border-radius: 12px;
  background: rgba(230, 162, 60, 0.1);
  border: 1px solid rgba(230, 162, 60, 0.3);
  color: #e6a23c;
  font-weight: 500;
  transition: all 0.3s ease;
  min-width: 280px;
}

.random-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #e6a23c 0%, #f0b85a 100%);
  border-color: #e6a23c;
  color: #fff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(230, 162, 60, 0.3);
}

/* Create Project Section */
.create-project-section.standalone {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 20px 0 0 0;
  padding: 0;
  border: none;
}

.create-project-btn {
  border-radius: 12px;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  border: none;
  font-weight: 600;
  transition: all 0.3s ease;
  min-width: 200px;
  height: 48px;
  font-size: 16px;
}

.create-project-btn.standalone {
  min-width: 280px;
  height: 56px;
  font-size: 18px;
  box-shadow: 0 4px 20px rgba(64, 158, 255, 0.3);
}

.create-project-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #337ecc 0%, #409eff 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
}

.create-project-btn.standalone:hover:not(:disabled) {
  transform: translateY(-3px);
  box-shadow: 0 6px 25px rgba(64, 158, 255, 0.5);
}

/* Step Navigation */
.right-column {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.step-navigation {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 20px;
}

.step-navigation .el-button {
  margin: 0 !important;
}

.back-btn {
  width: 100%;
  border-radius: 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-weight: 500;
}

.back-btn:hover {
  background: var(--hover-bg);
  border-color: var(--border-color);
}

.create-project-btn.final {
  width: 100%;
}

/* Projects Card */
.projects-card {
  display: flex;
  flex-direction: column;
  height: fit-content;
}

.projects-content {
  padding: 20px 28px;
  min-height: 200px;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--text-muted);
}

.loading-icon {
  font-size: 36px;
  color: #409eff;
  margin-bottom: 16px;
}

.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 48px;
  color: var(--text-muted);
  margin-bottom: 16px;
}

.empty-container p {
  margin: 0 0 4px 0;
  font-size: 15px;
  color: var(--text-secondary);
}

.empty-container span {
  font-size: 13px;
  color: var(--text-muted);
}

/* Project List */
.project-list {
  max-height: 380px;
  overflow-y: auto;
  padding-right: 4px;
}

.project-list::-webkit-scrollbar {
  width: 6px;
}

.project-list::-webkit-scrollbar-track {
  background: var(--bg-secondary);
  border-radius: 3px;
}

.project-list::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}

.project-list::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}

.project-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border: 2px solid var(--border-light);
  border-radius: 12px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.25s ease;
  background: var(--bg-card);
}

.project-item:last-child {
  margin-bottom: 0;
}

.project-item:hover {
  border-color: #c6e2ff;
  background: rgba(64, 158, 255, 0.05);
}

.project-item.is-selected {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.1);
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.15);
}

.project-checkbox {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.25s ease;
}

.project-item.is-selected .project-checkbox {
  background: #409eff;
  border-color: #409eff;
}

.check-icon {
  color: #fff;
  font-size: 14px;
}

.project-info {
  flex: 1;
  min-width: 0;
}

.project-topic {
  font-weight: 600;
  font-size: 15px;
  color: var(--text-primary);
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.project-meta .style-tag {
  background: rgba(230, 162, 60, 0.1);
  border-color: rgba(230, 162, 60, 0.3);
  color: #e6a23c;
}

.project-meta :deep(.el-tag) {
  border-radius: 20px;
  font-size: 12px;
}

.project-date {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-muted);
}

.project-date .el-icon {
  font-size: 14px;
}

.delete-btn {
  opacity: 0;
  transition: opacity 0.2s ease;
}

.project-item:hover .delete-btn {
  opacity: 1;
}

/* Load Button */
.load-button-container {
  padding: 20px 28px;
  border-top: 1px solid var(--border-light);
  background: var(--bg-secondary);
}

.load-btn {
  width: 100%;
  border-radius: 12px;
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
  border: none;
  font-weight: 600;
  transition: all 0.3s ease;
}

.load-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #529b2e 0%, #67c23a 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.4);
}

.load-btn:disabled {
  background: var(--bg-secondary);
  color: var(--text-muted);
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
  .step-create {
    padding: 24px;
  }
  
  .content-row {
    flex-direction: column;
  }
  
  .content-row .el-col {
    margin-bottom: 20px;
  }
  
  .content-row .el-col:last-child {
    margin-bottom: 0;
  }
  
  .create-project-section.standalone {
    min-height: auto;
    padding: 20px 0;
  }
}

@media (max-width: 768px) {
  .step-create {
    padding: 16px;
  }
  
  .page-title {
    font-size: 22px;
  }
  
  .card-header {
    padding: 20px;
  }
  
  .style-content,
  .selected-style-content {
    padding: 20px;
  }
  
  .create-form {
    padding: 20px;
  }
  
  .form-actions-top {
    flex-direction: column;
  }
  
  .step-navigation {
    flex-direction: column;
  }
  
  .create-project-section.standalone {
    align-items: center;
    padding: 24px 0;
  }
  
  .create-project-btn.standalone {
    width: 100%;
    max-width: 300px;
  }
  
  .input-ai-btn {
    position: static;
    transform: none;
    margin-top: 8px;
    width: 100%;
  }
  
  .input-wrapper.textarea .input-ai-btn,
  .input-ai-btn.textarea-btn {
    position: static;
    margin-top: 8px;
  }
}
</style>