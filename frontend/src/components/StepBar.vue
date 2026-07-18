<template>
  <div class="step-bar">
    <div class="step-container">
      <div 
        v-for="(step, index) in steps" 
        :key="step.id"
        class="step-item"
        :class="{
          'is-active': step.id === currentStep,
          'is-completed': step.id < currentStep,
          'is-clickable': step.id <= maxStep,
          'is-disabled': step.id > maxStep
        }"
        @click="handleClick(step.id)"
      >
        <div class="step-indicator">
          <div class="step-circle">
            <el-icon v-if="step.id < currentStep" class="check-icon"><Check /></el-icon>
            <span v-else>{{ step.id }}</span>
          </div>
          <div v-if="index < steps.length - 1" class="step-line" />
        </div>
        <div class="step-content">
          <span class="step-title">{{ step.name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/project'
import { Check } from '@element-plus/icons-vue'

const steps = [
  { id: 1, name: '创建项目' },
  { id: 2, name: '角色设定' },
  { id: 3, name: '生成分镜' },
  { id: 4, name: '编辑调整' },
  { id: 5, name: '生成音频' },
  { id: 6, name: '导出' },
]

const projectStore = useProjectStore()
const { currentStep, maxStep } = storeToRefs(projectStore)
const router = useRouter()

function handleClick(stepId: number) {
  if (stepId <= maxStep.value) {
    projectStore.setStep(stepId)
    router.push(`/step/${stepId}`)
  }
}
</script>

<style scoped>
.step-bar {
  background: var(--bg-card);
  padding: 24px 32px;
  border-radius: 16px;
  margin-bottom: 24px;
  box-shadow: var(--shadow-sm);
}

.step-container {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  position: relative;
  cursor: default;
}

.step-item.is-clickable {
  cursor: pointer;
}

.step-item.is-clickable:hover .step-circle {
  transform: scale(1.1);
}

.step-item.is-clickable:hover .step-title {
  color: #409eff;
}

.step-indicator {
  display: flex;
  align-items: center;
  width: 100%;
  position: relative;
}

.step-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  background: var(--bg-secondary);
  color: var(--text-muted);
  position: relative;
  z-index: 2;
  margin: 0 auto;
  transition: all 0.3s ease;
  border: 3px solid var(--bg-card);
  box-shadow: var(--shadow-sm);
}

.step-item.is-active .step-circle {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: #fff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
}

.step-item.is-completed .step-circle {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
  color: #fff;
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.3);
}

.step-item.is-disabled .step-circle {
  background: var(--bg-secondary);
  color: var(--text-muted);
}

.check-icon {
  font-size: 18px;
}

.step-line {
  position: absolute;
  top: 50%;
  left: calc(50% + 22px);
  right: calc(-50% + 22px);
  height: 3px;
  background: var(--border-color);
  transform: translateY(-50%);
  z-index: 1;
  border-radius: 2px;
}

.step-item.is-completed .step-line {
  background: linear-gradient(90deg, #67c23a 0%, #85ce61 100%);
}

.step-content {
  margin-top: 12px;
  text-align: center;
}

.step-title {
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
  transition: color 0.3s ease;
  white-space: nowrap;
}

.step-item.is-active .step-title {
  color: #409eff;
  font-weight: 600;
}

.step-item.is-completed .step-title {
  color: #67c23a;
}

.step-item.is-disabled .step-title {
  color: var(--text-muted);
}

/* Responsive */
@media (max-width: 768px) {
  .step-bar {
    padding: 16px;
    overflow-x: auto;
  }
  
  .step-container {
    min-width: 600px;
  }
  
  .step-circle {
    width: 32px;
    height: 32px;
    font-size: 12px;
  }
  
  .step-title {
    font-size: 12px;
  }
  
  .step-line {
    left: calc(50% + 18px);
    right: calc(-50% + 18px);
  }
}
</style>
