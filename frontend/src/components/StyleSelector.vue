<template>
  <div class="style-selector">
    <div class="style-grid">
      <div
        v-for="style in styles"
        :key="style.id"
        class="style-card"
        :class="{ selected: modelValue === style.id }"
        @click="handleSelect(style.id)"
      >
        <div class="style-icon">
          <el-icon :size="24">
            <component :is="getStyleIcon(style.id)" />
          </el-icon>
        </div>
        <div class="style-info">
          <span class="style-name">{{ style.name }}</span>
          <span class="style-desc">{{ style.description }}</span>
        </div>
        <div v-if="modelValue === style.id" class="selected-mark">
          <el-icon><Check /></el-icon>
        </div>
      </div>
    </div>

    <!-- 自定义风格输入 -->
    <div v-if="modelValue === 'custom'" class="custom-input">
      <el-input
        :model-value="customDescription"
        type="textarea"
        :rows="3"
        placeholder="请描述您想要的视频风格，例如：轻松幽默的科普风格，适合年轻人观看..."
        @update:model-value="$emit('update:customDescription', $event)"
      />
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载风格列表...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Check, Loading, Reading, Microphone, VideoCamera, Headset, Edit } from '@element-plus/icons-vue'
import { getStyles, type StyleInfo } from '@/api/styles'

const props = defineProps<{
  modelValue: string
  customDescription?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'update:customDescription', value: string): void
}>()

const styles = ref<StyleInfo[]>([])
const loading = ref(false)

// 风格图标映射
function getStyleIcon(styleId: string) {
  const iconMap: Record<string, any> = {
    teaching: Reading,
    nursery_rhyme: Microphone,
    storybook: VideoCamera,
    recitation: Headset,
    custom: Edit
  }
  return iconMap[styleId] || Edit
}

function handleSelect(styleId: string) {
  emit('update:modelValue', styleId)
}

async function loadStyles() {
  loading.value = true
  try {
    const response = await getStyles()
    styles.value = response.styles
  } catch (error) {
    console.error('Failed to load styles:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStyles()
})
</script>

<style scoped>
.style-selector {
  width: 100%;
}

.style-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.style-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 16px;
  border: 2px solid var(--border-color);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: var(--bg-card);
}

.style-card:hover {
  border-color: #c6e2ff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
  transform: translateY(-2px);
}

.style-card.selected {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.1);
}

.style-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  margin-bottom: 12px;
}

.style-card.selected .style-icon {
  background: linear-gradient(135deg, #337ecc 0%, #409eff 100%);
}

.style-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  text-align: center;
}

.style-name {
  font-weight: 600;
  font-size: 15px;
  color: var(--text-primary);
}

.style-desc {
  font-size: 12px;
  color: var(--text-muted);
}

.selected-mark {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.custom-input {
  margin-top: 16px;
}

.custom-input :deep(.el-textarea__inner) {
  border-radius: 10px;
  padding: 12px;
  font-size: 14px;
  line-height: 1.6;
}

.loading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 32px;
  color: var(--text-muted);
}

.loading-container .is-loading {
  animation: rotating 1s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 响应式 */
@media (max-width: 768px) {
  .style-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .style-grid {
    grid-template-columns: 1fr;
  }
}
</style>
