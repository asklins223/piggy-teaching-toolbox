<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="login-header">
          <h2>小猪教学工具箱</h2>
          <p class="login-subtitle">AI 驱动的教学视频素材自动生成工具</p>
        </div>
      </template>
      <el-form 
        ref="formRef"
        :model="form" 
        :rules="rules"
        @submit.prevent="handleLogin"
      >
        <div class="floating-input" :class="{ 'is-focus': usernameFocus || form.username }">
          <el-form-item prop="username">
            <input
              v-model="form.username"
              type="text"
              @focus="usernameFocus = true"
              @blur="usernameFocus = false"
              @keyup.enter="handleLogin"
            />
            <label>用户名</label>
          </el-form-item>
        </div>
        
        <div class="floating-input" :class="{ 'is-focus': passwordFocus || form.password }">
          <el-form-item prop="password">
            <input
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              @focus="passwordFocus = true"
              @blur="passwordFocus = false"
              @keyup.enter="handleLogin"
            />
            <label>密码</label>
            <span class="toggle-password" @click="showPassword = !showPassword">
              <el-icon><View v-if="!showPassword" /><Hide v-else /></el-icon>
            </span>
          </el-form-item>
        </div>

        <el-button 
          type="primary" 
          native-type="submit" 
          :loading="loading" 
          size="large"
          class="login-btn"
        >
          {{ loading ? '登录中...' : '登录' }}
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { View, Hide } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'

const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()

// 初始化主题
onMounted(() => {
  themeStore.init()
})

const formRef = ref<FormInstance>()
const usernameFocus = ref(false)
const passwordFocus = ref(false)
const showPassword = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = reactive<FormRules>({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
})

const loading = ref(false)

async function handleLogin() {
  if (!formRef.value) return
  
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  loading.value = true
  try {
    const success = await authStore.login(form.username, form.password)
    if (success) {
      ElMessage.success('登录成功')
      router.push('/step/1')
    } else {
      ElMessage.error(authStore.error || '登录失败，请检查用户名和密码')
    }
  } catch {
    ElMessage.error('登录失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: var(--bg-primary);
  transition: background-color 0.3s ease;
  position: relative;
}

.login-card {
  width: 420px;
  border-radius: 12px;
  box-shadow: var(--shadow-lg);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  transition: background-color 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
}

.login-header {
  text-align: center;
}

.login-header h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
  color: var(--text-primary);
  transition: color 0.3s ease;
}

.login-subtitle {
  margin: 0;
  font-size: 14px;
  color: var(--text-muted);
  transition: color 0.3s ease;
}

/* 浮动标签输入框 */
.floating-input {
  position: relative;
  margin-bottom: 24px;
}

.floating-input input {
  width: 100%;
  height: 50px;
  padding: 20px 12px 6px;
  font-size: 16px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  outline: none;
  background: var(--input-bg);
  color: var(--text-primary);
  transition: border-color 0.2s, background-color 0.3s ease, color 0.3s ease;
  box-sizing: border-box;
}

.floating-input input:focus {
  border-color: #409eff;
}

.floating-input label {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 16px;
  color: var(--text-muted);
  pointer-events: none;
  transition: all 0.2s ease;
  background: var(--input-bg);
  padding: 0 4px;
}

.floating-input.is-focus label {
  top: 0;
  font-size: 12px;
  color: #409eff;
}

.floating-input input:focus ~ label {
  color: #409eff;
}

.toggle-password {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  cursor: pointer;
  color: var(--text-muted);
  transition: color 0.3s ease;
}

.toggle-password:hover {
  color: #409eff;
}

.login-btn {
  width: 100%;
  height: 46px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  margin-top: 8px;
}

:deep(.el-card__header) {
  padding: 24px 20px 16px;
  border-bottom: 1px solid var(--border-light);
  transition: border-color 0.3s ease;
}

:deep(.el-card__body) {
  padding: 24px 20px;
}

:deep(.el-form-item) {
  margin-bottom: 0;
}

:deep(.el-form-item__error) {
  position: absolute;
  top: 100%;
  left: 0;
  padding-top: 2px;
}
</style>
