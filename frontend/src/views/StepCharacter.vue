<template>
  <div class="step-character">
    <div class="page-header">
      <h2 class="page-title">
        <el-icon class="title-icon"><UserFilled /></el-icon>
        角色设定
      </h2>
      <p class="page-subtitle">创建或选择视频中的角色形象</p>
    </div>

    <el-row :gutter="32" class="content-row">
      <!-- Left: Character Library -->
      <el-col :xs="24" :lg="14" class="left-col">
        <div class="card library-card" ref="libraryCardRef">
          <div class="card-header">
            <div class="header-left">
              <div class="header-icon library-icon">
                <el-icon><Grid /></el-icon>
              </div>
              <div class="header-text">
                <h3>角色库</h3>
                <span>{{ characterLibrary.length }} 个角色可用</span>
              </div>
            </div>
            <el-button 
              text 
              class="refresh-btn"
              @click="handleRefreshLibrary"
              :loading="loadingLibrary"
            >
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
          
          <div class="card-body">
            <div v-if="loadingLibrary" class="loading-container">
              <el-icon class="is-loading loading-icon"><Loading /></el-icon>
              <span>加载角色库...</span>
            </div>
            
            <div v-else-if="characterLibrary.length === 0" class="empty-container">
              <el-icon class="empty-icon"><Picture /></el-icon>
              <p>角色库为空</p>
              <span>在右侧创建你的第一个角色吧</span>
            </div>
            
            <div v-else class="character-grid">
              <div 
                v-for="character in characterLibrary" 
                :key="character.character_id"
                class="character-card"
                :class="{ 
                  'is-added': isCharacterInProject(character.character_id)
                }"
                @click="handleToggleCharacter(character)"
              >
                <div class="character-image">
                  <el-image 
                    :src="getImageUrl(character.image_url)" 
                    fit="cover"
                  >
                    <template #error>
                      <div class="image-placeholder">
                        <el-icon><Picture /></el-icon>
                      </div>
                    </template>
                  </el-image>
                  <div 
                    class="preview-badge" 
                    @click.stop="handlePreviewImage(character)"
                  >
                    <el-icon><ZoomIn /></el-icon>
                  </div>
                  <!-- 只有自己创建的角色才显示删除按钮 -->
                  <el-popconfirm
                    v-if="isOwnCharacter(character)"
                    title="确定删除此角色？"
                    confirm-button-text="删除"
                    cancel-button-text="取消"
                    @confirm="handleDeleteCharacter(character)"
                  >
                    <template #reference>
                      <div 
                        class="delete-badge" 
                        @click.stop
                      >
                        <el-icon><Delete /></el-icon>
                      </div>
                    </template>
                  </el-popconfirm>
                  <div v-if="isCharacterInProject(character.character_id)" class="added-badge">
                    <el-icon><Check /></el-icon>
                  </div>
                  <div v-if="togglingCharacterId === character.character_id || deletingCharacterId === character.character_id" class="loading-overlay">
                    <el-icon class="is-loading"><Loading /></el-icon>
                  </div>
                </div>
                <div class="character-name">{{ character.name }}</div>
              </div>
            </div>
          </div>
        </div>
      </el-col>
      
      <!-- Right: Create & Project Characters -->
      <el-col :xs="24" :lg="10" class="right-col" ref="rightColRef">
        <!-- Create Character Form -->
        <div class="card create-card">
          <div class="card-header">
            <div class="header-left">
              <div class="header-icon create-icon">
                <el-icon><MagicStick /></el-icon>
              </div>
              <div class="header-text">
                <h3>创建新角色</h3>
                <span>AI 生成独特的角色形象</span>
              </div>
            </div>
          </div>
          
          <div class="card-body">
            <el-form 
              ref="formRef"
              :model="form" 
              :rules="rules" 
              label-position="top"
              class="create-form"
            >
              <el-form-item label="角色名称" prop="name" class="form-item-custom">
                <template #label>
                  <span class="form-label">
                    <el-icon><User /></el-icon>
                    角色名称
                  </span>
                </template>
                <div class="input-with-action">
                  <el-input 
                    v-model="form.name" 
                    placeholder="例如：小橘猫、白兔老师"
                    :disabled="generating"
                    size="large"
                  />
                  <el-tooltip content="随机角色模板" placement="top">
                    <el-button 
                      @click="handleRandomTemplate"
                      :loading="loadingTemplate"
                      :disabled="generating"
                      class="action-icon-btn"
                      circle
                    >
                      <el-icon><RefreshRight /></el-icon>
                    </el-button>
                  </el-tooltip>
                </div>
              </el-form-item>
              
              <el-form-item label="角色描述" prop="description" class="form-item-custom">
                <template #label>
                  <span class="form-label">
                    <el-icon><Document /></el-icon>
                    角色描述
                  </span>
                </template>
                <el-input 
                  v-model="form.description" 
                  type="textarea"
                  :rows="4"
                  placeholder="详细描述角色的外观特征，例如：可爱卡通风格的拟人化橘色猫咪，圆圆的脸蛋，大大的眼睛..."
                  :disabled="generating"
                />
              </el-form-item>
              
              <div class="form-actions">
                <el-button 
                  @click="handleAIGenerate"
                  :loading="generatingAI"
                  :disabled="generating"
                  class="ai-btn"
                  size="large"
                >
                  <el-icon><MagicStick /></el-icon>
                  交给伟大的AI之神吧！
                </el-button>
                
                <el-button 
                  type="primary" 
                  @click="handleGenerateCharacter"
                  :loading="generating"Í
                  size="large"
                  class="generate-btn"
                >
                  <el-icon><Picture /></el-icon>
                  {{ generating ? '生成中...' : '生成角色' }}
                </el-button>
              </div>
            </el-form>
            
            <!-- Generation Progress -->
            <div v-if="generating" class="generation-progress">
              <div class="progress-animation">
                <div class="progress-dot"></div>
                <div class="progress-dot"></div>
                <div class="progress-dot"></div>
              </div>
              <p>AI 正在绘制角色，请稍候...</p>
            </div>
          </div>
        </div>
        
        <!-- Project Characters -->
        <div class="card project-card">
          <div class="card-header">
            <div class="header-left">
              <div class="header-icon project-icon">
                <el-icon><Folder /></el-icon>
              </div>
              <div class="header-text">
                <h3>当前项目角色</h3>
                <span>已添加 {{ projectCharacters.length }} 个角色</span>
              </div>
            </div>
          </div>
          
          <div class="card-body project-body">
            <div v-if="!projectStore.currentProjectId" class="empty-container small">
              <el-icon class="empty-icon"><Warning /></el-icon>
              <p>请先创建或加载项目</p>
            </div>
            
            <div v-else-if="loadingProjectCharacters" class="loading-container small">
              <el-icon class="is-loading loading-icon"><Loading /></el-icon>
              <span>加载中...</span>
            </div>
            
            <div v-else-if="projectCharacters.length === 0" class="empty-container small">
              <el-icon class="empty-icon"><UserFilled /></el-icon>
              <p>尚未添加角色</p>
              <span>从角色库选择或创建新角色</span>
            </div>
            
            <div v-else class="project-character-list">
              <div 
                v-for="character in projectCharacters" 
                :key="character.character_id"
                class="project-character-item"
                @click="handleToggleCharacterFromProject(character)"
              >
                <el-image 
                  :src="getImageUrl(character.image_url)" 
                  fit="cover"
                  class="project-character-image"
                >
                  <template #error>
                    <div class="image-placeholder small">
                      <el-icon><Picture /></el-icon>
                    </div>
                  </template>
                </el-image>
                <span class="project-character-name">{{ character.name }}</span>
                <el-icon class="remove-hint"><Close /></el-icon>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Navigation -->
        <div class="navigation-buttons">
          <el-button @click="handlePrevStep" size="large" class="nav-btn prev-btn">
            <el-icon><ArrowLeft /></el-icon>
            上一步
          </el-button>
          <el-button 
            type="primary" 
            @click="handleNextStep"
            :disabled="projectCharacters.length === 0"
            size="large"
            class="nav-btn next-btn"
          >
            下一步
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </el-col>
    </el-row>
    
    <!-- Image Preview Dialog -->
    <el-image-viewer
      v-if="showImagePreview"
      :url-list="[previewImageUrl]"
      :initial-index="0"
      @close="showImagePreview = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElImageViewer } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { 
  Refresh, 
  Loading, 
  Picture, 
  Check, 
  MagicStick, 
  ArrowLeft, 
  ArrowRight,
  User,
  Document,
  Grid,
  Folder,
  UserFilled,
  Close,
  Warning,
  ZoomIn,
  RefreshRight,
  Delete
} from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'
import { useAuthStore } from '@/stores/auth'
import * as charactersApi from '@/api/characters'
import type { CharacterInfo } from '@/api/characters'

const router = useRouter()
const projectStore = useProjectStore()
const authStore = useAuthStore()

// Form
const formRef = ref<FormInstance>()
const form = reactive({
  name: '',
  description: ''
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入角色名称', trigger: 'blur' },
    { min: 1, max: 50, message: '名称长度在 1 到 50 个字符', trigger: 'blur' }
  ],
  description: [
    { required: true, message: '请输入角色描述', trigger: 'blur' },
    { min: 1, max: 500, message: '描述长度在 1 到 500 个字符', trigger: 'blur' }
  ]
}

// Loading states
const loadingLibrary = ref(false)
const loadingProjectCharacters = ref(false)
const loadingTemplate = ref(false)
const generatingAI = ref(false)
const generating = ref(false)
const togglingCharacterId = ref('')
const deletingCharacterId = ref('')

// Data
const characterLibrary = ref<CharacterInfo[]>([])
const projectCharacters = ref<CharacterInfo[]>([])
const showImagePreview = ref(false)
const previewImageUrl = ref('')

// Computed
const projectCharacterIds = computed(() => 
  projectCharacters.value.map(c => c.character_id)
)

// Helper functions
function getImageUrl(url: string): string {
  // Handle relative URLs
  if (url.startsWith('/api/')) {
    return url
  }
  return url
}

function isCharacterInProject(characterId: string): boolean {
  return projectCharacterIds.value.includes(characterId)
}

function isOwnCharacter(character: CharacterInfo): boolean {
  // 比较角色的 user_id 和当前登录用户名
  return !!authStore.username && character.user_id === authStore.username
}

// Load data on mount
onMounted(async () => {
  // 确保获取当前用户信息
  if (!authStore.username) {
    await authStore.fetchCurrentUser()
  }
  
  await Promise.all([
    loadCharacterLibrary(),
    loadProjectCharacters()
  ])
})

async function loadCharacterLibrary() {
  loadingLibrary.value = true
  try {
    const response = await charactersApi.getCharacterLibrary()
    characterLibrary.value = response.characters
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail?.message || '加载角色库失败')
  } finally {
    loadingLibrary.value = false
  }
}

async function loadProjectCharacters() {
  if (!projectStore.currentProjectId) {
    projectCharacters.value = []
    return
  }
  
  loadingProjectCharacters.value = true
  try {
    const response = await charactersApi.getProjectCharacters(projectStore.currentProjectId)
    projectCharacters.value = response.characters
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail?.message || '加载项目角色失败')
  } finally {
    loadingProjectCharacters.value = false
  }
}

async function handleRefreshLibrary() {
  await loadCharacterLibrary()
}

async function handleToggleCharacter(character: CharacterInfo) {
  if (!projectStore.currentProjectId) {
    ElMessage.warning('请先创建或加载项目')
    return
  }
  
  if (togglingCharacterId.value) return // 防止重复点击
  
  togglingCharacterId.value = character.character_id
  
  try {
    if (isCharacterInProject(character.character_id)) {
      // 移除角色
      await charactersApi.removeCharacterFromProject(
        projectStore.currentProjectId,
        character.character_id
      )
      ElMessage.success(`已移除「${character.name}」`)
    } else {
      // 添加角色
      await charactersApi.addCharacterToProject(
        projectStore.currentProjectId,
        character.character_id
      )
      ElMessage.success(`已添加「${character.name}」`)
    }
    await loadProjectCharacters()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail?.message || '操作失败')
  } finally {
    togglingCharacterId.value = ''
  }
}

async function handleAIGenerate() {
  generatingAI.value = true
  try {
    const response = await charactersApi.generateCharacterIdea()
    form.name = response.name
    form.description = response.description
    ElMessage.success('AI 已生成角色创意')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail?.message || 'AI 生成失败')
  } finally {
    generatingAI.value = false
  }
}

async function handleToggleCharacterFromProject(character: CharacterInfo) {
  if (!projectStore.currentProjectId) return
  
  try {
    await charactersApi.removeCharacterFromProject(
      projectStore.currentProjectId,
      character.character_id
    )
    ElMessage.success(`已移除「${character.name}」`)
    await loadProjectCharacters()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail?.message || '移除失败')
  }
}

async function handleDeleteCharacter(character: CharacterInfo) {
  deletingCharacterId.value = character.character_id
  
  try {
    await charactersApi.deleteCharacter(character.character_id)
    ElMessage.success(`已删除「${character.name}」`)
    
    // Refresh both lists
    await Promise.all([
      loadCharacterLibrary(),
      loadProjectCharacters()
    ])
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail?.message || '删除失败')
  } finally {
    deletingCharacterId.value = ''
  }
}

function handlePreviewImage(character: CharacterInfo) {
  previewImageUrl.value = getImageUrl(character.image_url)
  showImagePreview.value = true
}

async function handleRandomTemplate() {
  loadingTemplate.value = true
  try {
    const response = await charactersApi.getRandomTemplate()
    form.name = response.name
    form.description = response.description
    ElMessage.success('已填充随机角色模板')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail?.message || '获取随机模板失败')
  } finally {
    loadingTemplate.value = false
  }
}

async function handleGenerateCharacter() {
  if (!formRef.value) return
  
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  generating.value = true
  try {
    const response = await charactersApi.generateCharacter({
      name: form.name,
      description: form.description
    })
    
    // Select the new character and add to project
    if (projectStore.currentProjectId) {
      await charactersApi.addCharacterToProject(
        projectStore.currentProjectId,
        response.character_id
      )
      await loadProjectCharacters()
      ElMessage.success('角色已生成并添加到项目')
    } else {
      ElMessage.success('角色生成成功')
    }
    
    // Refresh library
    await loadCharacterLibrary()
    
    // Clear form
    form.name = ''
    form.description = ''
    formRef.value?.resetFields()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail?.message || '生成角色失败')
  } finally {
    generating.value = false
  }
}

function handlePrevStep() {
  projectStore.setStep(1)
  router.push('/step/1')
}

function handleNextStep() {
  if (projectCharacters.value.length === 0) {
    ElMessage.warning('请至少添加一个角色到项目')
    return
  }
  
  projectStore.setStep(3)
  router.push('/step/3')
}
</script>

<style scoped>
.step-character {
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
  align-items: stretch;
}

.left-col {
  display: flex;
  flex-direction: column;
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

.library-card {
  display: flex;
  flex-direction: column;
  flex: 1;
  margin-bottom: 0;
}

.library-card .card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  max-height: calc(100vh - 300px);
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
}

.library-icon {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: #fff;
}

.create-icon {
  background: linear-gradient(135deg, #e6a23c 0%, #f0b85a 100%);
  color: #fff;
}

.project-icon {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
  color: #fff;
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

.refresh-btn {
  color: var(--text-muted);
  font-size: 18px;
}

.refresh-btn:hover {
  color: #409eff;
}

/* Card Body */
.card-body {
  padding: 24px;
}

.project-body {
  padding: 16px 24px;
  min-height: 80px;
}

/* Loading & Empty States */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--text-muted);
}

.loading-container.small {
  padding: 30px 20px;
}

.loading-icon {
  font-size: 36px;
  color: #409eff;
  margin-bottom: 12px;
}

.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--text-muted);
}

.empty-container.small {
  padding: 24px 20px;
}

.empty-icon {
  font-size: 48px;
  color: var(--text-muted);
  margin-bottom: 12px;
}

.empty-container.small .empty-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.empty-container p {
  margin: 0 0 4px 0;
  font-size: 14px;
  color: var(--text-secondary);
}

.empty-container span {
  font-size: 12px;
  color: var(--text-muted);
}

/* Character Grid */
.character-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 20px;
  padding: 4px;
  flex: 1;
  align-content: start;
}

/* Loading & Empty in library */
.library-card .loading-container,
.library-card .empty-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.character-grid::-webkit-scrollbar {
  width: 6px;
}

.character-grid::-webkit-scrollbar-track {
  background: var(--bg-secondary);
  border-radius: 3px;
}

.character-grid::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}

.character-card {
  cursor: pointer;
  border: 3px solid transparent;
  border-radius: 16px;
  padding: 12px;
  transition: all 0.3s ease;
  background: var(--bg-secondary);
}

.character-card:hover {
  border-color: #c6e2ff;
  background: rgba(64, 158, 255, 0.05);
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(64, 158, 255, 0.15);
}

.character-card.is-selected {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.1);
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.25);
}

.character-card.is-added {
  border-color: #67c23a;
  background: rgba(103, 194, 58, 0.1);
}

.character-card.is-added:hover {
  border-color: #67c23a;
  background: rgba(103, 194, 58, 0.15);
}

.character-image {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.character-image .el-image {
  width: 100%;
  height: 100%;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-secondary);
  color: var(--text-muted);
  font-size: 36px;
}

.image-placeholder.small {
  font-size: 20px;
}

.added-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
}

.preview-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  width: 26px;
  height: 26px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 14px;
  background: rgba(0, 0, 0, 0.5);
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s ease;
}

.character-card:hover .preview-badge {
  opacity: 1;
}

.preview-badge:hover {
  background: rgba(64, 158, 255, 0.9);
  transform: scale(1.1);
}

.delete-badge {
  position: absolute;
  bottom: 8px;
  right: 8px;
  width: 26px;
  height: 26px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 14px;
  background: rgba(0, 0, 0, 0.5);
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s ease;
}

.character-card:hover .delete-badge {
  opacity: 1;
}

.delete-badge:hover {
  background: rgba(245, 108, 108, 0.9);
  transform: scale(1.1);
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--bg-card);
  opacity: 0.9;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
}

.loading-overlay .el-icon {
  font-size: 28px;
  color: #409eff;
}

.character-name {
  margin-top: 10px;
  text-align: center;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Card Footer */
.card-footer {
  padding: 16px 24px;
  border-top: 1px solid #f0f2f5;
  background: #fafbfc;
}

.add-btn {
  width: 100%;
  border-radius: 10px;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  border: none;
  font-weight: 600;
}

.add-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #337ecc 0%, #409eff 100%);
}

/* Create Form */
.create-form {
  padding: 0;
}

.form-item-custom {
  margin-bottom: 20px;
}

.form-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  color: var(--text-primary);
}

.form-label .el-icon {
  color: #e6a23c;
}

.create-form :deep(.el-input__wrapper),
.create-form :deep(.el-textarea__inner) {
  border-radius: 10px;
}

/* Input with action button */
.input-with-action {
  display: flex;
  gap: 8px;
  align-items: center;
}

.input-with-action .el-input {
  flex: 1;
}

.action-icon-btn {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  background: rgba(230, 162, 60, 0.1);
  border: 1px solid rgba(230, 162, 60, 0.3);
  color: #e6a23c;
}

.action-icon-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #e6a23c 0%, #f0b85a 100%);
  border-color: #e6a23c;
  color: #fff;
}

/* Form Actions */
.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.random-btn {
  flex: 1;
  border-radius: 10px;
  background: linear-gradient(135deg, #fdf6ec 0%, #faecd8 100%);
  border: 1px solid #f5dab1;
  color: #e6a23c;
  font-weight: 500;
}

.random-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #e6a23c 0%, #f0b85a 100%);
  border-color: #e6a23c;
  color: #fff;
}

.ai-btn {
  flex: 1;
  border-radius: 10px;
  background: rgba(64, 158, 255, 0.1);
  border: 1px solid rgba(64, 158, 255, 0.3);
  color: #409eff;
  font-weight: 500;
}

.ai-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  border-color: #409eff;
  color: #fff;
}

.generate-btn {
  flex: 1.5;
  border-radius: 10px;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  border: none;
  font-weight: 600;
}

.generate-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #337ecc 0%, #409eff 100%);
}

/* Generation Progress */
.generation-progress {
  margin-top: 24px;
  padding: 20px;
  background: rgba(64, 158, 255, 0.1);
  border-radius: 12px;
  text-align: center;
}

.progress-animation {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 12px;
}

.progress-dot {
  width: 12px;
  height: 12px;
  background: #409eff;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.progress-dot:nth-child(1) { animation-delay: -0.32s; }
.progress-dot:nth-child(2) { animation-delay: -0.16s; }
.progress-dot:nth-child(3) { animation-delay: 0s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.generation-progress p {
  margin: 0;
  color: #409eff;
  font-size: 14px;
  font-weight: 500;
}

/* Project Character List */
.project-character-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.project-character-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border-radius: 12px;
  border: 2px solid transparent;
  transition: all 0.2s ease;
  cursor: pointer;
}

.project-character-item:hover {
  border-color: #f56c6c;
  background: rgba(245, 108, 108, 0.1);
}

.project-character-image {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.project-character-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  flex: 1;
}

.remove-hint {
  color: var(--text-muted);
  font-size: 14px;
  opacity: 0;
  transition: all 0.2s ease;
}

.project-character-item:hover .remove-hint {
  opacity: 1;
  color: #f56c6c;
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
}

.next-btn:disabled {
  background: var(--bg-secondary);
  color: var(--text-muted);
}

/* Responsive */
@media (max-width: 1199px) {
  .step-character {
    padding: 24px;
  }
  
  .content-row {
    flex-direction: column;
  }
}

@media (max-width: 768px) {
  .step-character {
    padding: 16px;
  }
  
  .page-title {
    font-size: 22px;
  }
  
  .character-grid {
    grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
    gap: 12px;
  }
  
  .form-actions {
    flex-direction: column;
  }
  
  .generate-btn {
    flex: 1;
  }
}
</style>
