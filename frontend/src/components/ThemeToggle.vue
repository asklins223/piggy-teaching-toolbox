<template>
  <div class="theme-toggle-wrapper">
    <!-- 主题切换滑块 -->
    <div class="theme-toggle" @click="handleToggle">
      <div class="toggle-track" :class="{ 'is-dark': isDark, 'is-snowing': isSnowing }">
        <!-- 雪花粒子效果 -->
        <div class="snow-particles" v-if="isSnowing">
          <span class="snow-particle" v-for="i in 5" :key="i" :style="{ '--delay': `${i * 0.3}s`, '--x': `${15 + i * 15}%` }"></span>
        </div>
        
        <!-- 滑块 -->
        <div class="toggle-thumb">
          <div class="icon-wrapper">
            <svg v-if="!isDark" class="sun-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="5"/>
              <line x1="12" y1="1" x2="12" y2="3"/>
              <line x1="12" y1="21" x2="12" y2="23"/>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
              <line x1="1" y1="12" x2="3" y2="12"/>
              <line x1="21" y1="12" x2="23" y2="12"/>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
            </svg>
            <svg v-else class="moon-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          </div>
        </div>
        
        <!-- 星星装饰 -->
        <div class="stars">
          <span class="star" style="--delay: 0s; --x: 20%; --y: 30%;"></span>
          <span class="star" style="--delay: 0.1s; --x: 60%; --y: 20%;"></span>
          <span class="star" style="--delay: 0.2s; --x: 80%; --y: 50%;"></span>
        </div>
        
        <!-- 云朵装饰 -->
        <div class="clouds">
          <span class="cloud" style="--delay: 0s; --x: 60%;"></span>
          <span class="cloud" style="--delay: 0.15s; --x: 75%;"></span>
        </div>
        
        <!-- 雪花开关 - 融合在滑块右侧 -->
        <div class="snow-btn" :class="{ 'is-active': isSnowing }" @click.stop="handleSnowToggle">
          <span>❄</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()
const isDark = computed(() => themeStore.mode === 'dark')
const isSnowing = computed(() => themeStore.snowEnabled)

function handleToggle() {
  themeStore.toggleTheme()
}

function handleSnowToggle() {
  themeStore.toggleSnow()
}
</script>

<style scoped>
.theme-toggle-wrapper {
  display: flex;
  align-items: center;
}

.theme-toggle {
  cursor: pointer;
  user-select: none;
}

.toggle-track {
  position: relative;
  width: 80px;
  height: 28px;
  border-radius: 14px;
  background: linear-gradient(135deg, #87CEEB 0%, #E0F4FF 100%);
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: visible;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
}

.toggle-track.is-dark {
  background: linear-gradient(135deg, #2d3a4f 0%, #1e293b 100%);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.1);
}

/* 下雪模式背景 */
.toggle-track.is-snowing {
  background: linear-gradient(135deg, #a8d4ff 0%, #d4e8ff 100%);
}

.toggle-track.is-snowing.is-dark {
  background: linear-gradient(135deg, #1a3a5c 0%, #0d2137 100%);
}

.toggle-thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
  box-shadow: 0 2px 8px rgba(255, 165, 0, 0.4);
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}

.is-dark .toggle-thumb {
  left: 30px;
  background: linear-gradient(135deg, #f5f5f5 0%, #e0e0e0 100%);
  box-shadow: 0 2px 8px rgba(255, 255, 255, 0.3);
}

.icon-wrapper {
  width: 14px;
  height: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sun-icon {
  width: 14px;
  height: 14px;
  color: #fff;
  animation: rotate-sun 10s linear infinite;
}

.moon-icon {
  width: 12px;
  height: 12px;
  color: #1a1a2e;
  animation: wobble 3s ease-in-out infinite;
}

@keyframes rotate-sun {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes wobble {
  0%, 100% { transform: rotate(-5deg); }
  50% { transform: rotate(5deg); }
}

/* 星星 */
.stars {
  position: absolute;
  top: 0;
  left: 0;
  width: 55px;
  height: 100%;
  opacity: 0;
  transition: opacity 0.5s ease;
  overflow: hidden;
}

.is-dark .stars {
  opacity: 1;
}

.star {
  position: absolute;
  width: 3px;
  height: 3px;
  background: #fff;
  border-radius: 50%;
  left: var(--x);
  top: var(--y);
  animation: twinkle 1.5s ease-in-out infinite;
  animation-delay: var(--delay);
}

@keyframes twinkle {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.2); }
}

/* 云朵 */
.clouds {
  position: absolute;
  top: 0;
  left: 0;
  width: 55px;
  height: 100%;
  opacity: 1;
  transition: opacity 0.5s ease;
  overflow: hidden;
}

.is-dark .clouds {
  opacity: 0;
}

.cloud {
  position: absolute;
  width: 10px;
  height: 5px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 5px;
  left: var(--x);
  top: 50%;
  transform: translateY(-50%);
  animation: float-cloud 3s ease-in-out infinite;
  animation-delay: var(--delay);
}

.cloud::before {
  content: '';
  position: absolute;
  width: 5px;
  height: 5px;
  background: inherit;
  border-radius: 50%;
  top: -2px;
  left: 2px;
}

@keyframes float-cloud {
  0%, 100% { transform: translateY(-50%) translateX(0); }
  50% { transform: translateY(-50%) translateX(-2px); }
}

/* 雪花按钮 - 融合在滑块内部右侧 */
.snow-btn {
  position: absolute;
  right: 3px;
  top: 3px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.85);
  border: 1.5px solid rgba(66, 165, 245, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  z-index: 3;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.snow-btn span {
  font-size: 11px;
  color: #1976d2;
  transition: all 0.3s ease;
}

.snow-btn:hover {
  background: rgba(255, 255, 255, 1);
  border-color: #42a5f5;
  transform: scale(1.1);
  box-shadow: 0 2px 6px rgba(66, 165, 245, 0.3);
}

.snow-btn:hover span {
  transform: rotate(15deg);
  color: #1565c0;
}

.snow-btn.is-active {
  background: linear-gradient(135deg, #64b5f6 0%, #42a5f5 100%);
  border-color: #2196f3;
  box-shadow: 0 0 10px rgba(66, 165, 245, 0.6), inset 0 0 4px rgba(255, 255, 255, 0.3);
}

.snow-btn.is-active span {
  color: #fff;
  animation: snowflake-spin 3s linear infinite;
  filter: drop-shadow(0 0 3px rgba(255, 255, 255, 0.9));
}

/* 暗黑模式下的雪花按钮 */
.is-dark .snow-btn {
  background: rgba(30, 40, 55, 0.9);
  border-color: rgba(100, 181, 246, 0.5);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.is-dark .snow-btn span {
  color: #64b5f6;
}

.is-dark .snow-btn:hover {
  background: rgba(40, 50, 65, 1);
  border-color: #64b5f6;
  box-shadow: 0 2px 6px rgba(66, 165, 245, 0.4);
}

.is-dark .snow-btn.is-active {
  background: linear-gradient(135deg, #42a5f5 0%, #1e88e5 100%);
  border-color: #1976d2;
  box-shadow: 0 0 12px rgba(66, 165, 245, 0.7), inset 0 0 4px rgba(255, 255, 255, 0.2);
}

@keyframes snowflake-spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 雪花粒子效果 */
.snow-particles {
  position: absolute;
  top: 0;
  left: 0;
  width: 55px;
  height: 100%;
  overflow: hidden;
  pointer-events: none;
}

.snow-particle {
  position: absolute;
  width: 2px;
  height: 2px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 50%;
  left: var(--x);
  animation: snow-fall 2s linear infinite;
  animation-delay: var(--delay);
}

@keyframes snow-fall {
  0% {
    top: -3px;
    opacity: 1;
  }
  100% {
    top: 100%;
    opacity: 0.3;
  }
}
</style>
