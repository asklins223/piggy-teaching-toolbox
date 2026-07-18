<template>
  <div class="audio-player" :class="{ 'is-disabled': !src, 'is-mini': mini }">
    <!-- Mini Mode -->
    <template v-if="mini">
      <div class="mini-player">
        <el-button
          :icon="isPlaying ? VideoPause : VideoPlay"
          circle
          size="small"
          :type="isPlaying ? 'primary' : 'default'"
          :disabled="!src || isLoading || hasError"
          @click="togglePlay"
        />
        <div ref="waveformRef" class="mini-waveform"></div>
        <span class="mini-time">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>
      </div>
      <div v-if="isLoading && src" class="mini-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
      </div>
      <div v-if="!src" class="mini-empty">
        <el-icon><Mute /></el-icon>
      </div>
    </template>

    <!-- Normal Mode -->
    <template v-else>
      <!-- Waveform Container -->
      <div ref="waveformRef" class="waveform-container"></div>

      <!-- Player Controls -->
      <div class="player-controls">
        <!-- Play/Pause Button -->
        <el-button
          :icon="isPlaying ? VideoPause : VideoPlay"
          circle
          :type="isPlaying ? 'primary' : 'default'"
          :disabled="!src || isLoading || hasError"
          @click="togglePlay"
          class="play-btn"
        />

        <!-- Time Display -->
        <div class="time-section">
          <span class="time-display">{{ formatTime(currentTime) }}</span>
          <span class="time-separator">/</span>
          <span class="time-display">{{ formatTime(duration) }}</span>
        </div>

        <!-- Volume Control -->
        <div v-if="showVolume" class="volume-section">
          <el-button
            :icon="isMuted ? Mute : Microphone"
            circle
            size="small"
            @click="toggleMute"
          />
          <el-slider
            v-model="volume"
            :min="0"
            :max="100"
            :show-tooltip="false"
            @change="handleVolumeChange"
            class="volume-slider"
          />
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading && src" class="loading-overlay">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <!-- Error State -->
      <div v-if="hasError" class="error-overlay">
        <el-icon><WarningFilled /></el-icon>
        <span>{{ errorMessage || '音频加载失败' }}</span>
      </div>

      <!-- No Source State -->
      <div v-if="!src" class="no-source-overlay">
        <el-icon><Headset /></el-icon>
        <span>{{ placeholder || '暂无音频' }}</span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import WaveSurfer from 'wavesurfer.js'
import { 
  VideoPlay, 
  VideoPause, 
  Loading, 
  WarningFilled,
  Headset,
  Microphone,
  Mute
} from '@element-plus/icons-vue'

// Props
const props = withDefaults(defineProps<{
  src?: string | null
  autoplay?: boolean
  showVolume?: boolean
  placeholder?: string
  waveColor?: string
  progressColor?: string
  height?: number
  mini?: boolean
}>(), {
  src: null,
  autoplay: false,
  showVolume: false,
  placeholder: '暂无音频',
  waveColor: '#c0c4cc',
  progressColor: '#409eff',
  height: 48,
  mini: false
})

// Emits
const emit = defineEmits<{
  (e: 'play'): void
  (e: 'pause'): void
  (e: 'ended'): void
  (e: 'error', error: Error): void
  (e: 'timeupdate', currentTime: number): void
}>()

// Refs
const waveformRef = ref<HTMLElement | null>(null)
let wavesurfer: WaveSurfer | null = null

// State
const isPlaying = ref(false)
const isLoading = ref(false)
const hasError = ref(false)
const errorMessage = ref('')
const currentTime = ref(0)
const duration = ref(0)
const volume = ref(80)
const isMuted = ref(false)
const hasEnded = ref(false) // 防止 ended 事件重复触发

// Initialize WaveSurfer
function initWaveSurfer() {
  if (!waveformRef.value) return
  
  // Destroy existing instance
  if (wavesurfer) {
    wavesurfer.destroy()
    wavesurfer = null
  }
  
  wavesurfer = WaveSurfer.create({
    container: waveformRef.value,
    waveColor: props.waveColor,
    progressColor: props.progressColor,
    height: props.mini ? 24 : props.height,
    barWidth: 3,
    barGap: 2,
    barRadius: 2,
    cursorWidth: 1,
    cursorColor: '#409eff',
    normalize: true,
    fillParent: true,
    backend: 'WebAudio',
    hideScrollbar: true
  })
  
  // Event listeners
  wavesurfer.on('ready', () => {
    isLoading.value = false
    duration.value = wavesurfer?.getDuration() || 0
    wavesurfer?.setVolume(volume.value / 100)
    
    if (props.autoplay) {
      wavesurfer?.play()
    }
  })
  
  wavesurfer.on('play', () => {
    isPlaying.value = true
    hasEnded.value = false // 重置结束标志
    emit('play')
  })
  
  wavesurfer.on('pause', () => {
    isPlaying.value = false
    emit('pause')
  })
  
  wavesurfer.on('finish', () => {
    if (!hasEnded.value) {
      hasEnded.value = true
      isPlaying.value = false
      currentTime.value = 0
      wavesurfer?.seekTo(0)
      emit('ended')
    }
  })
  
  wavesurfer.on('timeupdate', (time: number) => {
    currentTime.value = time
    emit('timeupdate', time)
    
    // 检查是否超过总时长，手动停止播放
    const totalDuration = wavesurfer?.getDuration() || 0
    if (totalDuration > 0 && time >= totalDuration - 0.1 && !hasEnded.value) {
      // 接近或超过结束时间，停止播放
      hasEnded.value = true
      wavesurfer?.pause()
      wavesurfer?.seekTo(0)
      currentTime.value = 0
      isPlaying.value = false
      emit('ended')
    }
  })
  
  wavesurfer.on('error', (err: Error) => {
    isLoading.value = false
    hasError.value = true
    errorMessage.value = '音频加载失败'
    emit('error', err)
  })
}

// Load audio source
function loadAudio(url: string) {
  if (!wavesurfer) {
    initWaveSurfer()
  }
  
  // Reset state
  isLoading.value = true
  hasError.value = false
  errorMessage.value = ''
  currentTime.value = 0
  duration.value = 0
  isPlaying.value = false
  hasEnded.value = false
  
  wavesurfer?.load(url)
}

// Watch for src changes
watch(() => props.src, async (newSrc) => {
  if (newSrc) {
    await nextTick()
    loadAudio(newSrc)
  } else {
    // Reset when no source
    if (wavesurfer) {
      wavesurfer.destroy()
      wavesurfer = null
    }
    isPlaying.value = false
    isLoading.value = false
    hasError.value = false
    currentTime.value = 0
    duration.value = 0
  }
}, { immediate: false })

// Methods
function togglePlay() {
  if (!wavesurfer || !props.src) return
  wavesurfer.playPause()
}

function toggleMute() {
  if (!wavesurfer) return
  isMuted.value = !isMuted.value
  wavesurfer.setMuted(isMuted.value)
}

function handleVolumeChange(value: number) {
  if (!wavesurfer) return
  wavesurfer.setVolume(value / 100)
  if (value === 0) {
    isMuted.value = true
  } else if (isMuted.value) {
    isMuted.value = false
    wavesurfer.setMuted(false)
  }
}

function formatTime(seconds: number): string {
  if (!seconds || isNaN(seconds)) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// Public methods
function play() {
  wavesurfer?.play()
}

function pause() {
  wavesurfer?.pause()
}

function stop() {
  wavesurfer?.stop()
  isPlaying.value = false
  currentTime.value = 0
}

// Lifecycle
onMounted(async () => {
  await nextTick()
  initWaveSurfer()
  if (props.src) {
    loadAudio(props.src)
  }
})

onUnmounted(() => {
  if (wavesurfer) {
    wavesurfer.destroy()
    wavesurfer = null
  }
})

// Expose methods
defineExpose({
  play,
  pause,
  stop,
  isPlaying
})
</script>

<style scoped>
.audio-player {
  position: relative;
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 12px 16px;
  min-height: 100px;
  width: 100%;
}

.audio-player.is-disabled {
  opacity: 0.6;
}

/* Mini Mode Styles */
.audio-player.is-mini {
  min-height: auto;
  padding: 6px 10px;
  background: transparent;
}

.mini-player {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mini-waveform {
  flex: 1;
  min-width: 60px;
}

.mini-time {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'Monaco', 'Menlo', monospace;
  min-width: 70px;
  white-space: nowrap;
}

.mini-loading,
.mini-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  color: var(--text-muted);
}

/* Normal Mode Styles */
.waveform-container {
  width: 100%;
  margin-bottom: 12px;
  border-radius: 4px;
  overflow: hidden;
}

.waveform-container :deep(wave) {
  overflow: hidden !important;
}

.player-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.play-btn {
  flex-shrink: 0;
}

.time-section {
  display: flex;
  align-items: center;
  gap: 4px;
}

.time-display {
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 36px;
  text-align: center;
  font-family: 'Monaco', 'Menlo', monospace;
}

.time-separator {
  color: var(--text-muted);
  font-size: 12px;
}

.volume-section {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.volume-slider {
  width: 80px;
}

.volume-slider :deep(.el-slider__runway) {
  height: 3px;
}

.volume-slider :deep(.el-slider__bar) {
  height: 3px;
}

.volume-slider :deep(.el-slider__button) {
  width: 10px;
  height: 10px;
}

.loading-overlay,
.error-overlay,
.no-source-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: var(--bg-secondary);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-muted);
}

.error-overlay {
  color: #f56c6c;
}

.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
