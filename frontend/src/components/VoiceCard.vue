<template>
  <div
    class="voice-card"
    :class="{ selected, playing: isPlaying, 'show-delete': showDelete, 'loading': isLoading }"
    @click="handleCardClick"
  >
    <!-- 删除按钮 - 选择音色页面右上角显示 -->
    <div v-if="!showDelete && selected && !isPlaying" class="selected-mark">
      <el-icon><Check /></el-icon>
    </div>
    
    <!-- 默认状态：显示音色信息 -->
    <div v-if="!isPlaying" class="voice-info">
      <div class="voice-icon" @click.stop="handlePlayClick">
        <el-icon v-if="!isLoading" :size="24"><VideoPlay /></el-icon>
        <el-icon v-else :size="24" class="is-loading"><Loading /></el-icon>
      </div>
      <div class="voice-details">
        <span class="voice-name">{{ name }}</span>
        <span class="voice-id">{{ showDelete ? id : displayId }}</span>
      </div>
      <div v-if="showDelete" class="delete-btn-inline" @click.stop>
        <el-popconfirm
          title="确定删除此音色？"
          confirm-button-text="删除"
          cancel-button-text="取消"
          @confirm="$emit('delete')"
        >
          <template #reference>
            <el-button circle size="small" type="danger" :icon="Delete" />
          </template>
        </el-popconfirm>
      </div>
    </div>
    
    <!-- 播放状态：显示波形图 -->
    <div v-else class="voice-playing">
      <div ref="waveformRef" class="waveform-container"></div>
      <div class="playing-footer">
        <span class="voice-name">{{ name }}</span>
        <el-button
          circle
          size="small"
          type="danger"
          :icon="VideoPause"
          @click.stop="stopPlay"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onBeforeUnmount } from 'vue'
import { VideoPlay, VideoPause, Check, Delete, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import WaveSurfer from 'wavesurfer.js'
import * as ttsApi from '@/api/tts'

const props = defineProps<{
  id: string
  name: string
  previewUrl?: string
  selected?: boolean
  showDelete?: boolean
}>()

const emit = defineEmits<{
  (e: 'select'): void
  (e: 'delete'): void
}>()

const isPlaying = ref(false)
const isLoading = ref(false)
const waveformRef = ref<HTMLElement | null>(null)
let wavesurfer: WaveSurfer | null = null
let blobUrl: string | null = null

const displayId = computed(() => {
  if (props.id.length > 16) {
    return props.id.slice(0, 16) + '...'
  }
  return props.id
})

async function handleCardClick() {
  if (isLoading.value || isPlaying.value) return
  emit('select')
}

async function handlePlayClick() {
  if (isLoading.value || isPlaying.value) return
  if (props.previewUrl) {
    await startPlay()
  }
}

async function startPlay() {
  if (!props.previewUrl) return
  
  isLoading.value = true
  
  try {
    // Get audio URL
    if (props.previewUrl.startsWith('/api/')) {
      blobUrl = await ttsApi.getVoicePreviewUrl(props.id)
    } else {
      blobUrl = props.previewUrl
    }
    
    isPlaying.value = true
    isLoading.value = false
    
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))
    
    if (waveformRef.value) {
      wavesurfer = WaveSurfer.create({
        container: waveformRef.value,
        waveColor: '#a0cfff',
        progressColor: '#409eff',
        cursorColor: '#409eff',
        height: 80,
        barWidth: 3,
        barGap: 2,
        barRadius: 3,
      })
      
      wavesurfer.on('finish', () => {
        setTimeout(() => stopPlay(), 100)
      })
      
      wavesurfer.on('error', (err) => {
        console.error('WaveSurfer error:', err)
        ElMessage.error('播放失败')
        stopPlay()
      })
      
      await wavesurfer.load(blobUrl)
      wavesurfer.play()
    }
  } catch (err) {
    console.error('Failed to play:', err)
    ElMessage.error('播放失败')
    isLoading.value = false
    stopPlay()
  }
}

function stopPlay() {
  if (wavesurfer) {
    try {
      wavesurfer.destroy()
    } catch (e) {}
    wavesurfer = null
  }
  
  if (blobUrl && blobUrl.startsWith('blob:')) {
    URL.revokeObjectURL(blobUrl)
    blobUrl = null
  }
  
  isPlaying.value = false
}

onBeforeUnmount(() => {
  stopPlay()
})
</script>

<style scoped>
.voice-card {
  position: relative;
  padding: 16px;
  border: 2px solid var(--border-color);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: var(--bg-card);
  min-width: 200px;
  overflow: hidden;
}

.voice-card:hover {
  border-color: #c6e2ff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
  transform: translateY(-2px);
}

.voice-card.loading {
  cursor: wait;
}

.voice-card.selected {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.1);
}

.voice-card.playing {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.1);
}

.voice-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.voice-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  cursor: pointer;
  transition: all 0.2s;
}

.voice-icon:hover {
  transform: scale(1.05);
}

.voice-icon .is-loading {
  animation: rotating 1s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.voice-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.voice-name {
  font-weight: 600;
  font-size: 15px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.voice-id {
  font-size: 12px;
  color: var(--text-muted);
  word-break: break-all;
}

.delete-btn-inline {
  flex-shrink: 0;
  margin-left: 8px;
}

.voice-playing {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.playing-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.playing-footer .voice-name {
  font-weight: 600;
  color: #409eff;
}

.waveform-container {
  width: 100%;
  min-height: 80px;
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
</style>
