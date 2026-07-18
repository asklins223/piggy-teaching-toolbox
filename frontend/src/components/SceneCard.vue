<template>
  <div class="scene-card" :class="{ 'is-editing': isEditing }">
    <!-- Scene Header -->
    <div class="scene-header">
      <div class="header-left">
        <div class="scene-badge">
          <span class="badge-number">{{ scene.step_number }}</span>
        </div>
        <h4 class="scene-title">分镜 {{ scene.step_number }}</h4>
      </div>
      <div class="header-actions">
        <el-button 
          v-if="!isEditing"
          type="primary" 
          text 
          @click="startEditing"
          class="edit-trigger"
        >
          <el-icon><Edit /></el-icon>
          编辑
        </el-button>
      </div>
    </div>

    <div class="scene-body">
      <!-- Image Section -->
      <div class="image-section">
      <div class="image-wrapper">
          <el-image
            v-if="scene.image_url"
            :src="scene.image_url"
            fit="cover"
            class="scene-image"
            :preview-src-list="[scene.image_url]"
            :initial-index="0"
            preview-teleported
            :close-on-press-escape="true"
            :hide-on-click-modal="true"
          >
            <template #error>
              <div class="image-fallback error">
                <el-icon><Picture /></el-icon>
                <span>加载失败</span>
              </div>
            </template>
            <template #placeholder>
              <div class="image-fallback loading">
                <el-icon class="is-loading"><Loading /></el-icon>
              </div>
            </template>
          </el-image>
          <div v-else class="image-fallback empty">
            <el-icon><Picture /></el-icon>
            <span>暂无图片</span>
          </div>
        </div>
        
        <el-button
          type="primary"
          :disabled="isRegenerating"
          @click="handleRegenerateImage"
          class="regenerate-btn"
        >
          <el-icon :class="{ 'is-loading': isRegenerating }"><Refresh /></el-icon>
          {{ isRegenerating ? '生成中...' : '重新生成' }}
        </el-button>
        
        <!-- Duration -->
        <div class="image-meta">
          <div class="meta-item" v-if="!isEditing">
            <el-icon><Clock /></el-icon>
            <span>{{ scene.duration }}秒</span>
          </div>
          <el-select
            v-else
            v-model="editForm.duration"
            size="default"
            class="meta-select-duration"
          >
            <template #prefix>
              <el-icon><Clock /></el-icon>
            </template>
            <el-option
              v-for="opt in durationOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </div>
      </div>

      <!-- Content Section -->
      <div class="content-section">
        <el-form
          ref="formRef"
          :model="editForm"
          label-position="top"
          class="edit-form"
        >
          <!-- Image Prompt (图片生成描述) -->
          <el-form-item class="form-item">
            <template #label>
              <span class="form-label">
                <el-icon><Picture /></el-icon>
                图片描述
                <el-tooltip content="用于AI图片生成，包含构图、光线、色调等" placement="top">
                  <el-icon class="help-icon"><QuestionFilled /></el-icon>
                </el-tooltip>
              </span>
            </template>
            <el-input
              v-model="editForm.image_prompt"
              type="textarea"
              :rows="3"
              placeholder="图片生成描述（构图、光线、色调等）..."
              :disabled="!isEditing"
            />
          </el-form-item>

          <!-- Video Prompt (视频生成描述) -->
          <el-form-item class="form-item">
            <template #label>
              <span class="form-label">
                <el-icon><VideoCamera /></el-icon>
                视频描述
                <el-tooltip content="用于视频生成，包含运镜、转场等" placement="top">
                  <el-icon class="help-icon"><QuestionFilled /></el-icon>
                </el-tooltip>
              </span>
            </template>
            <el-input
              v-model="editForm.video_prompt"
              type="textarea"
              :rows="2"
              placeholder="视频生成描述（运镜、转场等）..."
              :disabled="!isEditing"
            />
          </el-form-item>

          <!-- Legacy Description (hidden, for compatibility) -->
          <input type="hidden" v-model="editForm.description_cn" />

          <!-- Narrations Row -->
          <el-row :gutter="20">
            <el-col :xs="24" :sm="12">
              <el-form-item class="form-item">
                <template #label>
                  <span class="form-label">
                    <el-icon><ChatDotRound /></el-icon>
                    中文旁白
                  </span>
                </template>
                <el-input
                  v-model="editForm.narration_cn"
                  type="textarea"
                  :rows="4"
                  placeholder="中文旁白内容..."
                  :disabled="!isEditing"
                />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item class="form-item">
                <template #label>
                  <span class="form-label">
                    <el-icon><ChatDotRound /></el-icon>
                    英文旁白
                  </span>
                </template>
                <el-input
                  v-model="editForm.narration_en"
                  type="textarea"
                  :rows="4"
                  placeholder="English narration..."
                  :disabled="!isEditing"
                />
              </el-form-item>
            </el-col>
          </el-row>

          <!-- Audio Params Section -->
          <el-form-item v-if="isEditing" class="form-item audio-params-section">
            <template #label>
              <span class="form-label">
                <el-icon><Headset /></el-icon>
                音频参数
              </span>
            </template>
            <div class="audio-params-wrapper">
              <AudioParamsEditor
                v-model="editForm.audio_params"
                :show-reset="true"
              />
            </div>
          </el-form-item>
          
          <!-- Audio Params Display (non-editing mode) -->
          <div v-else-if="scene.audio_params" class="audio-params-display">
            <div class="params-header">
              <el-icon><Headset /></el-icon>
              <span>音频参数</span>
            </div>
            <div class="params-tags">
              <el-tag size="small" type="info">
                情感: {{ getEmotionDisplayName(scene.audio_params.emotion) }}
              </el-tag>
              <el-tag size="small" type="info">
                强度: {{ (scene.audio_params.emotion_strength ?? 0.6).toFixed(1) }}
              </el-tag>
              <el-tag size="small" type="info">
                语速: {{ (scene.audio_params.speed ?? 1.0).toFixed(1) }}x
              </el-tag>
              <el-tag size="small" type="info">
                音量: {{ (scene.audio_params.volume ?? 1.0).toFixed(1) }}
              </el-tag>
            </div>
          </div>
        </el-form>

        <!-- Edit Actions -->
        <div v-if="isEditing" class="edit-actions">
          <el-button @click="cancelEditing" class="cancel-btn">
            取消
          </el-button>
          <el-button type="primary" :loading="isSaving" @click="saveChanges" class="save-btn">
            <el-icon><Check /></el-icon>
            保存修改
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Picture, 
  Loading, 
  Refresh, 
  Edit, 
  Check, 
  Clock, 
  ChatDotRound,
  Headset,
  VideoCamera,
  QuestionFilled
} from '@element-plus/icons-vue'
import type { Scene, UpdateSceneRequest } from '@/api/storyboard'
import AudioParamsEditor from './AudioParamsEditor.vue'

const props = defineProps<{
  scene: Scene
  projectId: string
}>()

const emit = defineEmits<{
  (e: 'update', sceneId: string, data: UpdateSceneRequest): void
  (e: 'regenerate', sceneId: string): void
}>()

// Options
const durationOptions = [
  { value: 5, label: '5 秒' },
  { value: 8, label: '8 秒' },
  { value: 10, label: '10 秒' },
  { value: 12, label: '12 秒' },
  { value: 15, label: '15 秒' }
]



// State
const isEditing = ref(false)
const isSaving = ref(false)
const isRegenerating = ref(false)

const editForm = reactive({
  description_cn: '',
  image_prompt: '',
  video_prompt: '',
  narration_cn: '',
  narration_en: '',
  duration: 10,
  audio_params: {
    emotion: 'calm',
    emotion_strength: 0.6,
    speed: 1.0,
    volume: 1.0
  }
})

function initForm() {
  editForm.description_cn = props.scene.description_cn || ''
  editForm.image_prompt = props.scene.image_prompt || props.scene.description_cn || ''
  editForm.video_prompt = props.scene.video_prompt || ''
  editForm.narration_cn = props.scene.narration_cn || ''
  editForm.narration_en = props.scene.narration_en || ''
  editForm.duration = props.scene.duration || 10
  editForm.audio_params = {
    emotion: props.scene.audio_params?.emotion || 'calm',
    emotion_strength: props.scene.audio_params?.emotion_strength ?? 0.6,
    speed: props.scene.audio_params?.speed ?? 1.0,
    volume: props.scene.audio_params?.volume ?? 1.0
  }
}

watch(() => props.scene, () => {
  if (!isEditing.value) {
    initForm()
  }
}, { immediate: true, deep: true })

function startEditing() {
  initForm()
  isEditing.value = true
}

function cancelEditing() {
  initForm()
  isEditing.value = false
}

async function saveChanges() {
  isSaving.value = true
  
  try {
    const updateData: UpdateSceneRequest = {
      description_cn: editForm.image_prompt,  // 兼容：使用 image_prompt 作为 description_cn
      image_prompt: editForm.image_prompt,
      video_prompt: editForm.video_prompt,
      narration_cn: editForm.narration_cn,
      narration_en: editForm.narration_en,
      duration: editForm.duration,
      audio_params: editForm.audio_params
    }
    
    emit('update', props.scene.scene_id, updateData)
    isEditing.value = false
    ElMessage.success('保存成功')
  } catch (error: any) {
    ElMessage.error('保存失败')
  } finally {
    isSaving.value = false
  }
}

function handleRegenerateImage() {
  isRegenerating.value = true
  emit('regenerate', props.scene.scene_id)
}

function resetRegeneratingState() {
  isRegenerating.value = false
}



// Emotion display name mapping for audio params
const emotionDisplayMap: Record<string, string> = {
  'calm': '平静',
  'happy': '喜',
  'angry': '怒',
  'sad': '哀',
  'fear': '惧',
  'disgust': '厌恶',
  'depressed': '低落',
  'surprised': '惊喜',
  'lively': '活泼',
  'healing': '治愈',
  'aggrieved': '委屈',
  'embarrassed': '尴尬',
  'proud': '自豪',
  'conflicted': '纠结',
  'lost': '失落',
  'shy': '害羞',
  'irritated': '烦躁'
}

function getEmotionDisplayName(emotion: string | undefined | null): string {
  if (!emotion) return '平静'
  return emotionDisplayMap[emotion] || emotion
}

defineExpose({
  resetRegeneratingState
})
</script>

<style scoped>
.scene-card {
  background: var(--bg-card);
  border-radius: 16px;
  box-shadow: var(--shadow-md);
  overflow: hidden;
  transition: all 0.3s ease;
}

.scene-card:hover {
  box-shadow: var(--shadow-lg);
}

.scene-card.is-editing {
  box-shadow: 0 8px 30px rgba(64, 158, 255, 0.15);
  border: 2px solid #409eff;
}

/* Header */
.scene-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-light);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.scene-badge {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}

.badge-number {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
}

.scene-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.edit-trigger {
  font-weight: 500;
}

.edit-trigger:hover {
  background: rgba(64, 158, 255, 0.1);
}

/* Body */
.scene-body {
  display: flex;
  padding: 20px;
  gap: 24px;
  align-items: flex-start;
}

/* Image Section */
.image-section {
  flex-shrink: 0;
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.image-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 12px;
  overflow: hidden;
  background: var(--bg-secondary);
}

.scene-image {
  width: 100%;
  height: 100%;
  cursor: pointer;
}

.image-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--text-muted);
}

.image-fallback .el-icon {
  font-size: 40px;
}

.image-fallback span {
  font-size: 13px;
}

.image-fallback.error {
  color: #f56c6c;
}

.regenerate-btn {
  width: 100%;
  border-radius: 10px;
  background: rgba(64, 158, 255, 0.1);
  border: 1px solid rgba(64, 158, 255, 0.3);
  color: #409eff;
  font-weight: 500;
  transition: all 0.3s ease;
}

.regenerate-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  border-color: #409eff;
  color: #fff;
}

/* Image Meta */
.image-meta {
  display: flex;
}

.meta-item {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.meta-item .el-icon {
  font-size: 14px;
  color: var(--text-muted);
}

.meta-select-duration {
  flex: 1;
}

.meta-select-duration :deep(.el-input__wrapper) {
  border-radius: 8px;
}

.meta-select-duration :deep(.el-input__prefix) {
  color: #909399;
}

/* Content Section */
.content-section {
  flex: 1;
  min-width: 0;
}

.edit-form {
  margin-bottom: 0;
}

.form-item {
  margin-bottom: 16px;
}

.form-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.form-label .el-icon {
  color: #409eff;
  font-size: 14px;
}

.edit-form :deep(.el-textarea__inner) {
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.6;
  transition: all 0.3s ease;
}

.edit-form :deep(.el-textarea__inner:disabled) {
  background: var(--bg-secondary);
  color: var(--text-primary);
  cursor: default;
}

.edit-form :deep(.el-select) {
  width: 100%;
}

.edit-form :deep(.el-input__wrapper) {
  border-radius: 10px;
}

/* Edit Actions */
.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px dashed var(--border-color);
}

/* Audio Params Section */
.audio-params-section {
  margin-top: 16px;
}

.audio-params-wrapper {
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 12px;
  border: 1px solid var(--border-light);
}

.audio-params-display {
  margin-top: 16px;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-radius: 10px;
}

.params-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.params-header .el-icon {
  color: #409eff;
}

.params-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.params-tags :deep(.el-tag) {
  border-radius: 6px;
}

.cancel-btn {
  border-radius: 10px;
  min-width: 80px;
}

.save-btn {
  border-radius: 10px;
  min-width: 120px;
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
  border: none;
  font-weight: 500;
}

.save-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #529b2e 0%, #67c23a 100%);
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
@media (max-width: 768px) {
  .scene-body {
    flex-direction: column;
  }
  
  .image-section {
    width: 100%;
  }
  
  .image-wrapper {
    aspect-ratio: 16 / 9;
  }
  
  .edit-actions {
    flex-direction: column;
  }
  
  .cancel-btn,
  .save-btn {
    width: 100%;
  }
}

/* Help icon for tooltips */
.help-icon {
  font-size: 12px;
  color: var(--text-muted);
  cursor: help;
  margin-left: 2px;
}
</style>
