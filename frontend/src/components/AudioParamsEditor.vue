<template>
  <div class="audio-params-editor">
    <!-- 情感选择 -->
    <div class="param-section">
      <div class="section-header">
        <el-icon><MagicStick /></el-icon>
        <span>情感设置</span>
      </div>
      <EmotionSelector
        :model-value="params.emotion"
        :grouped="false"
        @update:model-value="updateParam('emotion', $event)"
      />
    </div>

    <!-- 参数滑块 -->
    <div class="param-section">
      <div class="section-header">
        <el-icon><Setting /></el-icon>
        <span>音频参数</span>
      </div>
      
      <div class="params-grid">
        <!-- 情感强度 -->
        <div class="param-item">
          <div class="param-label">
            <span>情感强度</span>
            <span class="param-value">{{ params.emotion_strength.toFixed(1) }}</span>
          </div>
          <el-slider
            :model-value="params.emotion_strength"
            :min="0"
            :max="1"
            :step="0.1"
            @update:model-value="updateParam('emotion_strength', $event)"
          />
          <div class="param-hint">
            <span>弱</span>
            <span>强</span>
          </div>
        </div>

        <!-- 语速 -->
        <div class="param-item">
          <div class="param-label">
            <span>语速</span>
            <span class="param-value">{{ params.speed.toFixed(1) }}x</span>
          </div>
          <el-slider
            :model-value="params.speed"
            :min="0.5"
            :max="2"
            :step="0.1"
            @update:model-value="updateParam('speed', $event)"
          />
          <div class="param-hint">
            <span>慢</span>
            <span>快</span>
          </div>
        </div>

        <!-- 音量 -->
        <div class="param-item">
          <div class="param-label">
            <span>音量</span>
            <span class="param-value">{{ params.volume.toFixed(1) }}</span>
          </div>
          <el-slider
            :model-value="params.volume"
            :min="0.5"
            :max="1.5"
            :step="0.1"
            @update:model-value="updateParam('volume', $event)"
          />
          <div class="param-hint">
            <span>低</span>
            <span>高</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 重置按钮 -->
    <div v-if="showReset" class="action-section">
      <el-button size="small" @click="handleReset">
        <el-icon><RefreshRight /></el-icon>
        重置为默认值
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { MagicStick, Setting, RefreshRight } from '@element-plus/icons-vue'
import EmotionSelector from './EmotionSelector.vue'

// 音频参数类型
export interface AudioParams {
  emotion: string
  emotion_strength: number
  speed: number
  volume: number
}

// 默认参数
const DEFAULT_PARAMS: AudioParams = {
  emotion: 'calm',
  emotion_strength: 0.6,
  speed: 1.0,
  volume: 1.0
}

const props = withDefaults(defineProps<{
  modelValue: AudioParams
  showReset?: boolean
}>(), {
  showReset: true
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: AudioParams): void
}>()

const params = computed(() => ({
  ...DEFAULT_PARAMS,
  ...props.modelValue
}))

function updateParam<K extends keyof AudioParams>(key: K, value: AudioParams[K]) {
  emit('update:modelValue', {
    ...params.value,
    [key]: value
  })
}

function handleReset() {
  emit('update:modelValue', { ...DEFAULT_PARAMS })
}
</script>

<style scoped>
.audio-params-editor {
  width: 100%;
}

.param-section {
  margin-bottom: 20px;
}

.param-section:last-child {
  margin-bottom: 0;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.section-header .el-icon {
  color: #409eff;
}

.params-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.param-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: var(--text-secondary);
}

.param-value {
  color: #409eff;
  font-weight: 500;
  font-family: 'Monaco', 'Menlo', monospace;
}

.param-item :deep(.el-slider) {
  margin: 0;
}

.param-hint {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-muted);
}

.action-section {
  padding-top: 16px;
  border-top: 1px dashed var(--border-color);
}

/* 响应式 */
@media (max-width: 480px) {
  .params-grid {
    gap: 16px;
  }
}
</style>
