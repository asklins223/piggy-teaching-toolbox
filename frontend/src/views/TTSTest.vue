<template>
  <div class="tts-test">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <el-button @click="$router.push('/step/1')" class="back-btn" text>
          <el-icon><Back /></el-icon>
          返回
        </el-button>
        <div class="header-title">
          <el-icon class="title-icon"><Headset /></el-icon>
          <h1>IndexTTS2 语音合成</h1>
        </div>
      </div>
      <div class="header-right">
        <ThemeToggle />
        <el-tag type="info" effect="plain">参数自动保存</el-tag>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <el-tabs v-model="activeTab" class="custom-tabs">
        <!-- 语音合成 Tab -->
        <el-tab-pane label="语音合成" name="synthesis">
          <div class="synthesis-layout">
            <!-- 左侧：参数设置 -->
            <div class="settings-panel">
              <!-- 文本输入区 -->
              <div class="panel-section">
                <div class="section-header">
                  <el-icon><Edit /></el-icon>
                  <span>合成文本</span>
                </div>
                <el-input
                  v-model="form.text"
                  type="textarea"
                  :rows="5"
                  placeholder="输入要合成的文本内容..."
                  resize="none"
                  class="text-input"
                />
              </div>

              <!-- 音色选择区 -->
              <div class="panel-section">
                <div class="section-header">
                  <el-icon><User /></el-icon>
                  <span>选择音色</span>
                  <el-button 
                    type="primary" 
                    link 
                    size="small" 
                    @click="activeTab = 'voices'"
                  >
                    管理音色
                  </el-button>
                </div>
                <div class="voice-grid" v-loading="loadingVoices">
                  <VoiceCard
                    v-for="voice in voices"
                    :key="voice.id"
                    :id="voice.id"
                    :name="voice.name"
                    :preview-url="voice.preview_url"
                    :selected="form.customVoice === voice.id"
                    @select="form.customVoice = voice.id"
                  />
                  <div v-if="!loadingVoices && voices.length === 0" class="empty-voice">
                    <el-icon :size="32"><Microphone /></el-icon>
                    <span>暂无音色</span>
                    <el-button type="primary" size="small" @click="activeTab = 'voices'">
                      上传音色
                    </el-button>
                  </div>
                </div>
              </div>

              <!-- 情感设置 -->
              <div class="panel-section">
                <div class="section-header">
                  <el-icon><MagicStick /></el-icon>
                  <span>情感设置</span>
                </div>
                
                <!-- 情感选择器 -->
                <div class="emotion-selector-wrapper">
                  <EmotionSelector
                    v-model="form.emotion"
                    :grouped="true"
                  />
                </div>
                
                <!-- 情感强度滑块 -->
                <div class="params-grid one-col" style="margin-top: 16px;">
                  <div class="param-item">
                    <label>情感强度 <span class="param-value">{{ form.emotionStrength }}</span></label>
                    <el-slider
                      v-model="form.emotionStrength"
                      :min="0"
                      :max="1"
                      :step="0.05"
                    />
                    <div class="param-hint-row">
                      <span>弱</span>
                      <span>强</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 基础参数 -->
              <div class="panel-section">
                <div class="section-header">
                  <el-icon><Setting /></el-icon>
                  <span>基础参数</span>
                </div>
                <div class="params-grid two-cols">
                  <div class="param-item">
                    <label>语速 <span class="param-value">{{ form.speed }}x</span></label>
                    <el-slider v-model="form.speed" :min="0.25" :max="4" :step="0.05" />
                  </div>
                  <div class="param-item">
                    <label>音量增益 <span class="param-value">{{ form.gain }}</span></label>
                    <el-slider v-model="form.gain" :min="0.1" :max="10" :step="0.1" />
                  </div>
                </div>
                <div class="params-grid three-cols" style="margin-top: 16px;">
                  <div class="param-item">
                    <label>采样率</label>
                    <el-select v-model="form.sampleRate">
                      <el-option :value="16000" label="16000 Hz" />
                      <el-option :value="22050" label="22050 Hz (默认)" />
                      <el-option :value="24000" label="24000 Hz" />
                    </el-select>
                  </div>
                  <div class="param-item">
                    <label>输出格式</label>
                    <el-select v-model="form.format">
                      <el-option value="mp3" label="MP3" />
                      <el-option value="wav" label="WAV" />
                      <el-option value="flac" label="FLAC" />
                      <el-option value="opus" label="OPUS" />
                    </el-select>
                  </div>
                  <div class="param-item">
                    <label>随机种子</label>
                    <el-input-number v-model="form.seed" :min="-1" controls-position="right" />
                  </div>
                </div>
              </div>

              <!-- 高级参数 -->
              <el-collapse class="advanced-collapse">
                <el-collapse-item>
                  <template #title>
                    <div class="collapse-title">
                      <el-icon><Operation /></el-icon>
                      <span>高级参数</span>
                    </div>
                  </template>
                  <div class="params-grid two-cols">
                    <div class="param-item">
                      <label>句间静音 <span class="param-value">{{ form.intervalSilence }}ms</span></label>
                      <el-slider v-model="form.intervalSilence" :min="0" :max="1000" :step="50" />
                    </div>
                    <div class="param-item">
                      <label>单句最大Token <span class="param-value">{{ form.maxTokens }}</span></label>
                      <el-slider v-model="form.maxTokens" :min="50" :max="300" :step="10" />
                    </div>
                  </div>
                  <div class="checkbox-item">
                    <el-checkbox v-model="form.emoRandom">情感随机性</el-checkbox>
                    <span class="param-hint">增加情感表达多样性</span>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>

            <!-- 右侧：结果预览 -->
            <div class="result-panel">
              <div class="result-card">
                <div class="result-header">
                  <el-icon><Headset /></el-icon>
                  <span>试听结果</span>
                </div>
                
                <div class="result-content">
                  <div v-if="audioUrl" class="audio-result">
                    <AudioPlayer :src="audioUrl" :height="100" show-volume />
                    <div class="result-info">
                      <el-tag type="success" size="small">生成成功</el-tag>
                      <span class="info-text">{{ statusMessage }}</span>
                    </div>
                    <el-button 
                      type="primary" 
                      :icon="Download" 
                      @click="handleDownload"
                      class="download-btn"
                    >
                      下载音频
                    </el-button>
                  </div>
                  
                  <div v-else class="empty-result">
                    <div class="empty-icon">
                      <el-icon :size="48"><Headset /></el-icon>
                    </div>
                    <p>点击下方按钮生成语音</p>
                  </div>
                  
                  <el-alert
                    v-if="errorMessage"
                    :title="errorMessage"
                    type="error"
                    show-icon
                    class="error-alert"
                  />
                </div>

                <!-- 操作按钮 -->
                <div class="action-buttons">
                  <el-button
                    type="primary"
                    size="large"
                    :loading="generating"
                    @click="handleGenerate"
                    class="generate-btn"
                  >
                    <el-icon><Microphone /></el-icon>
                    {{ generating ? '生成中...' : '生成语音' }}
                  </el-button>
                  <el-button size="large" @click="resetSettings" class="reset-btn">
                    <el-icon><RefreshRight /></el-icon>
                    重置参数
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 音色管理 Tab -->
        <el-tab-pane label="音色管理" name="voices">
          <div class="voices-layout">
            <!-- 上传区域 -->
            <div class="upload-panel">
              <div class="panel-section">
                <div class="section-header">
                  <el-icon><Upload /></el-icon>
                  <span>上传自定义音色</span>
                </div>
                
                <el-upload
                  ref="uploadRef"
                  drag
                  :auto-upload="false"
                  :limit="1"
                  accept=".wav,.mp3"
                  :on-change="handleFileChange"
                  :on-remove="handleFileRemove"
                  class="voice-upload"
                >
                  <div class="upload-content">
                    <el-icon class="upload-icon"><Upload /></el-icon>
                    <div class="upload-text">
                      <p>拖拽文件到此处，或 <em>点击上传</em></p>
                      <span>支持 WAV/MP3 格式，5-30 秒清晰语音</span>
                    </div>
                  </div>
                </el-upload>

                <div class="upload-form">
                  <el-input 
                    v-model="uploadForm.name" 
                    placeholder="输入音色名称，例如：小猪"
                    :prefix-icon="Edit"
                  />
                  <el-button
                    type="primary"
                    :loading="uploading"
                    @click="handleUpload"
                    :disabled="!uploadForm.file || !uploadForm.name.trim()"
                  >
                    <el-icon><Upload /></el-icon>
                    上传音色
                  </el-button>
                </div>

                <el-alert
                  v-if="uploadStatus"
                  :title="uploadStatus"
                  :type="uploadSuccess ? 'success' : 'error'"
                  show-icon
                  class="upload-alert"
                />
                
                <el-alert
                  title="自定义音色有效期为 7 天"
                  type="info"
                  show-icon
                  :closable="false"
                  class="info-alert"
                />
              </div>
            </div>

            <!-- 音色列表 -->
            <div class="voice-list-panel">
              <div class="panel-section">
                <div class="section-header">
                  <el-icon><List /></el-icon>
                  <span>可用音色列表</span>
                  <el-button 
                    type="primary" 
                    link 
                    :loading="loadingVoices"
                    @click="loadVoices"
                  >
                    <el-icon><Refresh /></el-icon>
                    刷新
                  </el-button>
                </div>

                <div class="voice-list" v-loading="loadingVoices">
                  <VoiceCard
                    v-for="voice in voices"
                    :key="voice.id"
                    :id="voice.id"
                    :name="voice.name"
                    :preview-url="voice.preview_url"
                    :show-delete="true"
                    @delete="handleDeleteVoice(voice.id)"
                  />
                  <div v-if="!loadingVoices && voices.length === 0" class="empty-list">
                    <el-icon :size="48"><Microphone /></el-icon>
                    <p>暂无音色，请先上传</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Back, Microphone, Upload, Download, Headset, Edit, User, 
  MagicStick, Setting, Operation, RefreshRight, List, Refresh
} from '@element-plus/icons-vue'
import AudioPlayer from '@/components/AudioPlayer.vue'
import VoiceCard from '@/components/VoiceCard.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import EmotionSelector from '@/components/EmotionSelector.vue'
import { useThemeStore } from '@/stores/theme'
import * as ttsApi from '@/api/tts'
import type { VoiceInfo } from '@/api/tts'

const themeStore = useThemeStore()

const TTS_SETTINGS_KEY = 'tts-test-settings'

const activeTab = ref('synthesis')

// Default form values
const defaultForm = {
  text: '',
  customVoice: '',
  emotion: 'calm',
  emotionStrength: 0.6,
  speed: 1.0,
  gain: 1.0,
  sampleRate: 22050,
  format: 'mp3',
  seed: -1,
  intervalSilence: 200,
  maxTokens: 120,
  emoRandom: false,
}

// Load saved settings from localStorage
function loadSettings() {
  try {
    const saved = localStorage.getItem(TTS_SETTINGS_KEY)
    if (saved) {
      return { ...defaultForm, ...JSON.parse(saved) }
    }
  } catch (e) {
    console.error('Failed to load TTS settings:', e)
  }
  return { ...defaultForm }
}

// Form state
const form = reactive(loadSettings())

// Save settings to localStorage (exclude text)
function saveSettings() {
  try {
    const { text, ...settings } = form
    localStorage.setItem(TTS_SETTINGS_KEY, JSON.stringify(settings))
  } catch (e) {
    console.error('Failed to save TTS settings:', e)
  }
}

// Watch form changes and save (debounced)
let saveTimeout: ReturnType<typeof setTimeout> | null = null
watch(form, () => {
  if (saveTimeout) clearTimeout(saveTimeout)
  saveTimeout = setTimeout(saveSettings, 500)
}, { deep: true })

// Upload form
const uploadForm = reactive({
  file: null as File | null,
  name: '',
})

// State
const generating = ref(false)
const audioUrl = ref('')
const statusMessage = ref('')
const errorMessage = ref('')

const voices = ref<VoiceInfo[]>([])
const loadingVoices = ref(false)

const uploading = ref(false)
const uploadStatus = ref('')
const uploadSuccess = ref(false)

// Methods
async function handleGenerate() {
  if (!form.text.trim()) {
    ElMessage.warning('请输入要合成的文本')
    return
  }

  generating.value = true
  errorMessage.value = ''
  audioUrl.value = ''

  try {
    const blob = await ttsApi.generateTTS({
      text: form.text,
      voice: form.customVoice,
      emotion: form.emotion,
      emotion_strength: form.emotionStrength,
      speed: form.speed,
      gain: form.gain,
      sample_rate: form.sampleRate,
      response_format: form.format,
      seed: form.seed,
      interval_silence: form.intervalSilence,
      max_text_tokens_per_sentence: form.maxTokens,
      emo_random: form.emoRandom,
    })

    audioUrl.value = URL.createObjectURL(blob)
    statusMessage.value = `音色: ${form.customVoice || '默认'}, 情感: ${form.emotion}, 语速: ${form.speed}x`
  } catch (error: any) {
    errorMessage.value = error.errorMessage || '生成失败'
  } finally {
    generating.value = false
  }
}

async function loadVoices() {
  loadingVoices.value = true
  try {
    const response = await ttsApi.getVoices()
    voices.value = response.list
  } catch (error: any) {
    ElMessage.error('获取音色列表失败')
  } finally {
    loadingVoices.value = false
  }
}

function handleFileChange(file: any) {
  uploadForm.file = file.raw
}

function handleFileRemove() {
  uploadForm.file = null
}

async function handleUpload() {
  if (!uploadForm.file) {
    ElMessage.warning('请选择音频文件')
    return
  }
  if (!uploadForm.name.trim()) {
    ElMessage.warning('请输入音色名称')
    return
  }

  uploading.value = true
  uploadStatus.value = ''

  try {
    const response = await ttsApi.uploadVoice(uploadForm.file, uploadForm.name)
    uploadStatus.value = `上传成功！音色 ID: ${response.id}`
    uploadSuccess.value = true
    
    // Refresh voice list
    await loadVoices()
    
    // Clear form
    uploadForm.file = null
    uploadForm.name = ''
  } catch (error: any) {
    uploadStatus.value = error.errorMessage || '上传失败'
    uploadSuccess.value = false
  } finally {
    uploading.value = false
  }
}

async function handleDeleteVoice(voiceId: string) {
  try {
    await ttsApi.deleteVoice(voiceId)
    ElMessage.success('音色删除成功')
    await loadVoices()
  } catch (error: any) {
    ElMessage.error(error.errorMessage || '删除失败')
  }
}

function resetSettings() {
  Object.assign(form, { ...defaultForm, text: form.text })
  ElMessage.success('参数已重置')
}

function handleDownload() {
  if (!audioUrl.value) return
  
  const link = document.createElement('a')
  link.href = audioUrl.value
  link.download = `tts_${Date.now()}.${form.format}`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

onMounted(() => {
  themeStore.init()
  loadVoices()
})
</script>


<style scoped>
.tts-test {
  min-height: 100vh;
  background: var(--bg-primary);
  padding: 24px;
}

/* 页面头部 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 16px 24px;
  background: var(--bg-card);
  border-radius: 16px;
  box-shadow: var(--shadow-sm);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn {
  color: var(--text-secondary);
  font-size: 14px;
}

.back-btn:hover {
  color: #409eff;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-icon {
  font-size: 28px;
  color: #409eff;
}

.header-title h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
}

/* 主内容区 */
.main-content {
  background: var(--bg-card);
  border-radius: 16px;
  box-shadow: var(--shadow-sm);
  padding: 24px;
}

/* 自定义 Tabs */
.custom-tabs :deep(.el-tabs__header) {
  margin-bottom: 24px;
}

.custom-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background: var(--border-color);
}

.custom-tabs :deep(.el-tabs__item) {
  font-size: 15px;
  font-weight: 500;
  padding: 0 24px;
  height: 48px;
  line-height: 48px;
}

.custom-tabs :deep(.el-tabs__active-bar) {
  height: 3px;
  border-radius: 2px;
}

/* 语音合成布局 */
.synthesis-layout {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 24px;
}

/* 面板区块 */
.panel-section {
  margin-bottom: 24px;
}

.panel-section:last-child {
  margin-bottom: 0;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.section-header .el-icon {
  color: #409eff;
}

.section-header .el-button {
  margin-left: auto;
}

/* 文本输入 */
.text-input :deep(.el-textarea__inner) {
  border-radius: 12px;
  padding: 16px;
  font-size: 14px;
  line-height: 1.6;
  border-color: var(--border-color);
  transition: all 0.3s;
}

.text-input :deep(.el-textarea__inner:focus) {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
}

/* 音色网格 */
.voice-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  min-height: 100px;
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

/* 参数网格 */
.params-grid {
  display: grid;
  gap: 20px;
}

.params-grid.one-col {
  grid-template-columns: 1fr;
}

.params-grid.two-cols {
  grid-template-columns: repeat(2, 1fr);
}

.params-grid.three-cols {
  grid-template-columns: repeat(3, 1fr);
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.param-item label {
  font-size: 13px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.param-value {
  color: #409eff;
  font-weight: 500;
  font-family: 'Monaco', 'Menlo', monospace;
}

.param-item :deep(.el-select),
.param-item :deep(.el-input-number) {
  width: 100%;
}

/* 暗黑模式下的输入组件样式 */
.param-item :deep(.el-select .el-input__wrapper),
.param-item :deep(.el-input-number .el-input__wrapper) {
  background-color: var(--input-bg);
  box-shadow: 0 0 0 1px var(--border-color) inset;
}

.param-item :deep(.el-input-number__decrease),
.param-item :deep(.el-input-number__increase) {
  background-color: var(--bg-secondary);
  border-color: var(--border-color);
}

.param-item :deep(.el-slider) {
  margin: 0;
}

/* 情感选项样式 */
.emotion-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.emotion-option .el-icon {
  color: #409eff;
}

.param-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: 8px;
}

.param-hint-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
}

.emotion-selector-wrapper {
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 12px;
  border: 1px solid var(--border-light);
}

.checkbox-item {
  display: flex;
  align-items: center;
  margin-top: 16px;
}

.checkbox-item :deep(.el-checkbox__label) {
  color: var(--text-primary);
}

/* 高级参数折叠 */
.advanced-collapse {
  border: none;
  margin-top: 16px;
}

.advanced-collapse :deep(.el-collapse-item__header) {
  border: none;
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 0 16px;
  height: 44px;
  color: var(--text-secondary);
}

.advanced-collapse :deep(.el-collapse-item__wrap) {
  border: none;
  background: transparent;
}

.advanced-collapse :deep(.el-collapse-item__content) {
  padding: 16px 0 0;
  background: transparent;
}

.collapse-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-secondary);
}

/* 结果面板 */
.result-panel {
  position: sticky;
  top: 24px;
}

.result-card {
  background: var(--bg-secondary);
  border-radius: 16px;
  padding: 24px;
  border: 1px solid var(--border-color);
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.result-header .el-icon {
  color: #409eff;
  font-size: 20px;
}

.result-content {
  min-height: 200px;
  display: flex;
  flex-direction: column;
}

.audio-result {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.info-text {
  font-size: 12px;
  color: var(--text-muted);
}

.download-btn {
  width: 100%;
}

.empty-result {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-muted);
}

.empty-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-result p {
  margin: 0;
  font-size: 14px;
}

.error-alert {
  margin-top: 16px;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.generate-btn {
  flex: 1;
  height: 48px;
  font-size: 15px;
  border-radius: 12px;
}

.reset-btn {
  height: 48px;
  border-radius: 12px;
}

/* 音色管理布局 */
.voices-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

/* 上传面板 */
.voice-upload {
  width: 100%;
}

.voice-upload :deep(.el-upload-dragger) {
  border-radius: 12px;
  border: 2px dashed var(--border-color);
  padding: 32px 20px;
  transition: all 0.3s;
}

.voice-upload :deep(.el-upload-dragger:hover) {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.05);
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.upload-icon {
  font-size: 40px;
  color: var(--text-muted);
}

.upload-text {
  text-align: center;
}

.upload-text p {
  margin: 0 0 4px;
  font-size: 14px;
  color: var(--text-secondary);
}

.upload-text em {
  color: #409eff;
  font-style: normal;
}

.upload-text span {
  font-size: 12px;
  color: var(--text-muted);
}

.upload-form {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.upload-form .el-input {
  flex: 1;
}

.upload-alert {
  margin-top: 16px;
}

.info-alert {
  margin-top: 12px;
}

/* 音色列表 */
.voice-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 500px;
  overflow-y: auto;
  padding: 4px;
  margin: -4px;
}

.empty-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 48px;
  color: var(--text-muted);
}

.empty-list p {
  margin: 0;
  font-size: 14px;
}

/* 响应式 */
@media (max-width: 1200px) {
  .synthesis-layout {
    grid-template-columns: 1fr;
  }
  
  .result-panel {
    position: static;
  }
  
  .params-grid.three-cols {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .tts-test {
    padding: 16px;
  }
  
  .page-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .voices-layout {
    grid-template-columns: 1fr;
  }
  
  .params-grid.two-cols,
  .params-grid.three-cols {
    grid-template-columns: 1fr;
  }
  
  .voice-grid {
    grid-template-columns: 1fr;
  }
}
</style>
