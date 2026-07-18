<template>
  <div class="emotion-selector">
    <!-- 分组显示模式 -->
    <template v-if="grouped">
      <div v-for="category in categories" :key="category.id" class="emotion-category">
        <div class="category-label">
          <el-icon><component :is="getCategoryIcon(category.id)" /></el-icon>
          <span>{{ category.name }}</span>
        </div>
        <div class="emotion-grid">
          <div
            v-for="emotion in category.emotions"
            :key="emotion.id"
            class="emotion-item"
            :class="{ selected: isSelected(emotion) }"
            @click="handleSelect(emotion.id)"
          >
            <span class="emotion-name">{{ emotion.name }}</span>
          </div>
        </div>
      </div>
    </template>

    <!-- 平铺显示模式 -->
    <template v-else>
      <div class="emotion-grid flat">
        <div
          v-for="emotion in allEmotions"
          :key="emotion.id"
          class="emotion-item"
          :class="{ selected: isSelected(emotion) }"
          @click="handleSelect(emotion.id)"
        >
          <span class="emotion-name">{{ emotion.name }}</span>
        </div>
      </div>
    </template>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载情感列表...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Loading, Sunny, Cloudy, PartlyCloudy } from '@element-plus/icons-vue'
import { getEmotions, type EmotionInfo, type EmotionCategoryInfo } from '@/api/emotions'

const props = withDefaults(defineProps<{
  modelValue: string
  grouped?: boolean
}>(), {
  grouped: true
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const allEmotions = ref<EmotionInfo[]>([])
const categories = ref<EmotionCategoryInfo[]>([])
const loading = ref(false)

// 分类图标映射
function getCategoryIcon(categoryId: string) {
  const iconMap: Record<string, any> = {
    positive: Sunny,
    negative: Cloudy,
    neutral: PartlyCloudy
  }
  return iconMap[categoryId] || PartlyCloudy
}

// 判断是否选中 - 同时支持英文 ID 和中文 value 匹配
function isSelected(emotion: EmotionInfo): boolean {
  const value = props.modelValue
  if (!value) return false
  // 匹配英文 ID (如 "lively") 或中文 value (如 "活泼") 或中文 name (如 "活泼")
  return value === emotion.id || value === emotion.value || value === emotion.name
}

function handleSelect(emotionId: string) {
  emit('update:modelValue', emotionId)
}

async function loadEmotions() {
  loading.value = true
  try {
    const response = await getEmotions()
    allEmotions.value = response.emotions
    categories.value = response.categories
  } catch (error) {
    console.error('Failed to load emotions:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadEmotions()
})
</script>

<style scoped>
.emotion-selector {
  width: 100%;
}

.emotion-category {
  margin-bottom: 16px;
}

.emotion-category:last-child {
  margin-bottom: 0;
}

.category-label {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.category-label .el-icon {
  font-size: 16px;
}

.emotion-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.emotion-grid.flat {
  gap: 10px;
}

.emotion-item {
  padding: 8px 16px;
  border: 1px solid var(--border-color);
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--bg-card);
}

.emotion-item:hover {
  border-color: #c6e2ff;
  background: rgba(64, 158, 255, 0.05);
}

.emotion-item.selected {
  border-color: #409eff;
  background: #409eff;
  color: #fff;
}

.emotion-name {
  font-size: 13px;
  white-space: nowrap;
}

.loading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
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
@media (max-width: 480px) {
  .emotion-item {
    padding: 6px 12px;
    font-size: 12px;
  }
}
</style>
