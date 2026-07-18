<template>
  <div class="home-container">
    <el-container>
      <el-header class="header">
        <h1>小猪教学工具箱</h1>
        <div class="header-actions">
          <ThemeToggle />
          <el-button @click="$router.push('/tts-test')" text>
            <el-icon><Microphone /></el-icon>
            TTS 测试
          </el-button>
          <el-button @click="handleLogout" text>退出登录</el-button>
        </div>
      </el-header>
      <el-main>
        <StepBar />
        <div class="content">
          <router-view />
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useProjectStore } from '@/stores/project'
import { useThemeStore } from '@/stores/theme'
import StepBar from '@/components/StepBar.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import { Microphone } from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()
const projectStore = useProjectStore()
const themeStore = useThemeStore()

// 初始化主题
onMounted(() => {
  themeStore.init()
})

function handleLogout() {
  authStore.logout()
  projectStore.reset()
  router.push('/login')
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background: var(--bg-primary);
  transition: background-color 0.3s ease;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--header-bg);
  box-shadow: var(--shadow-sm);
  transition: background-color 0.3s ease, box-shadow 0.3s ease;
}

.header h1 {
  margin: 0;
  font-size: 20px;
  color: var(--text-primary);
  transition: color 0.3s ease;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-actions :deep(.el-button) {
  color: var(--text-secondary);
  transition: color 0.3s ease;
}

.header-actions :deep(.el-button:hover) {
  color: var(--text-primary);
}

.content {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}
</style>
