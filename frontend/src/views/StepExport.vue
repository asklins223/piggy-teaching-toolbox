<template>
  <div class="step-export">
    <!-- Page Header -->
    <div class="page-header">
      <h2 class="page-title">
        <el-icon class="title-icon"><FolderOpened /></el-icon>
        预览与导出
      </h2>
      <p class="page-subtitle">检查所有素材，确认无误后导出完整素材包</p>
    </div>

    <div class="content-wrapper">
      <!-- Project Info -->
      <div class="card info-card">
        <div class="card-header">
          <div class="header-left">
            <div class="header-icon info-icon"><el-icon><Document /></el-icon></div>
            <h3>项目信息</h3>
          </div>
        </div>
        <div class="card-body">
          <div class="info-grid">
            <div class="info-item"><span class="label">主题</span><span class="value">{{ projectData?.goal?.topic || projectTopic || '-' }}</span></div>
            <div class="info-item"><span class="label">受众</span><span class="value">{{ projectData?.goal?.target_audience || projectAudience || '-' }}</span></div>
            <div class="info-item"><span class="label">分镜</span><el-tag type="primary" effect="light" size="small" round>{{ scenes.length }} 个</el-tag></div>
            <div class="info-item"><span class="label">状态</span><el-tag :type="getStatusTagType(projectStatus)" effect="light" size="small" round>{{ getStatusText(projectStatus) }}</el-tag></div>
          </div>
        </div>
      </div>

      <!-- Full Audio -->
      <div class="card audio-card">
        <div class="card-header">
          <div class="header-left">
            <div class="header-icon audio-icon"><el-icon><Headset /></el-icon></div>
            <h3>完整音频</h3>
          </div>
        </div>
        <div class="card-body">
          <div class="full-audio-grid">
            <div class="full-audio-item">
              <div class="audio-tag"><el-tag type="danger" effect="light" round>中文配音</el-tag></div>
              <div class="audio-box">
                <AudioPlayer v-if="fullAudioCnUrl" :src="fullAudioCnUrl" :height="48" />
                <div v-else class="no-audio"><el-icon><Mute /></el-icon><span>暂无音频</span></div>
              </div>
            </div>
            <div class="full-audio-item">
              <div class="audio-tag"><el-tag type="primary" effect="light" round>English Audio</el-tag></div>
              <div class="audio-box">
                <AudioPlayer v-if="fullAudioEnUrl" :src="fullAudioEnUrl" :height="48" />
                <div v-else class="no-audio"><el-icon><Mute /></el-icon><span>暂无音频</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Scenes Preview -->
      <div class="card scenes-card">
        <div class="card-header">
          <div class="header-left">
            <div class="header-icon scenes-icon"><el-icon><Film /></el-icon></div>
            <h3>分镜预览</h3>
          </div>
          <el-tag type="info" effect="light" round>共 {{ scenes.length }} 个分镜</el-tag>
        </div>
        <div class="card-body">
          <div class="scenes-list" v-if="scenes.length > 0">
            <div v-for="(scene, index) in scenes" :key="scene.scene_id" class="scene-item">
              <div class="scene-left">
                <div class="scene-num">{{ String(index + 1).padStart(2, '0') }}</div>
                <div class="scene-img">
                  <el-image v-if="scene.image_url" :src="scene.image_url" fit="cover" :preview-src-list="[scene.image_url]" preview-teleported>
                    <template #error><div class="img-err"><el-icon><Picture /></el-icon></div></template>
                  </el-image>
                  <div v-else class="img-empty"><el-icon><Picture /></el-icon></div>
                </div>
                <el-tag size="small" effect="plain" round>{{ scene.duration }}s</el-tag>
              </div>
              <div class="scene-right">
                <div class="narrations">
                  <div class="narration cn">
                    <span class="lang">中文</span>
                    <p>{{ scene.narration_cn || '暂无旁白' }}</p>
                  </div>
                  <div class="narration en">
                    <span class="lang">English</span>
                    <p>{{ scene.narration_en || 'No narration' }}</p>
                  </div>
                </div>
                <div class="audios">
                  <div class="audio-row">
                    <span class="audio-label cn">中文音频</span>
                    <div class="audio-player"><AudioPlayer :src="getSceneAudioUrl(scene.scene_id, 'cn')" :height="36" mini /></div>
                  </div>
                  <div class="audio-row">
                    <span class="audio-label en">英文音频</span>
                    <div class="audio-player"><AudioPlayer :src="getSceneAudioUrl(scene.scene_id, 'en')" :height="36" mini /></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无分镜数据" :image-size="80" />
        </div>
      </div>

      <!-- Export -->
      <div class="card export-card">
        <div class="card-header">
          <div class="header-left">
            <div class="header-icon export-icon" :class="getExportIconClass()"><el-icon><Download /></el-icon></div>
            <h3>导出素材包</h3>
          </div>
          <el-tag v-if="taskStatus" :type="getTaskStatusTagType(taskStatus)" effect="light" size="small" round>{{ getTaskStatusText(taskStatus) }}</el-tag>
        </div>
        <div class="card-body">
          <!-- Not Started -->
          <div v-if="!isExporting && !taskStatus && !hasExport" class="export-content">
            <div class="export-items">
              <div class="item"><el-icon><Picture /></el-icon><span>分镜图片</span></div>
              <div class="item"><el-icon><Headset /></el-icon><span>中英文音频</span></div>
              <div class="item"><el-icon><Document /></el-icon><span>SRT字幕</span></div>
              <div class="item"><el-icon><Files /></el-icon><span>提示词文件</span></div>
            </div>
            <el-button type="primary" size="large" @click="handleStartExport" :disabled="!canExport" class="export-btn">
              <el-icon><FolderOpened /></el-icon>开始导出
            </el-button>
          </div>
          <!-- Exporting -->
          <div v-else-if="isExporting || (taskStatus && taskStatus !== 'completed' && taskStatus !== 'failed')" class="export-content exporting">
            <div class="progress-ring">
              <svg viewBox="0 0 100 100"><circle class="bg" cx="50" cy="50" r="42"/><circle class="bar" cx="50" cy="50" r="42" :style="{strokeDashoffset: 264 - (progress/100)*264}"/></svg>
              <span class="num">{{ progress }}%</span>
            </div>
            <p>{{ progressMessage || '正在导出...' }}</p>
          </div>
          <!-- Completed -->
          <div v-else-if="taskStatus === 'completed' || hasExport" class="export-content done">
            <div class="done-icon"><el-icon><CircleCheck /></el-icon></div>
            <p>素材包已准备就绪</p>
            <div class="done-btns">
              <el-button type="primary" size="large" @click="handleDownload"><el-icon><Download /></el-icon>下载素材包</el-button>
              <el-button @click="handleReExport"><el-icon><RefreshRight /></el-icon>重新导出</el-button>
            </div>
          </div>
          <!-- Failed -->
          <div v-else-if="taskStatus === 'failed'" class="export-content failed">
            <div class="failed-icon"><el-icon><CircleClose /></el-icon></div>
            <p>{{ errorMessage || '导出失败' }}</p>
            <el-button type="primary" @click="handleRetry"><el-icon><RefreshRight /></el-icon>重试</el-button>
          </div>
        </div>
      </div>

      <!-- Nav -->
      <div class="nav-btns">
        <el-button @click="handlePrevStep" :disabled="isExporting" size="large"><el-icon><ArrowLeft /></el-icon>上一步</el-button>
        <el-button v-if="taskStatus === 'completed' || hasExport" type="success" size="large" @click="handleCreateNew"><el-icon><Plus /></el-icon>创建新项目</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { FolderOpened, Download, ArrowLeft, RefreshRight, Picture, Headset, Film, Document, Files, Mute, CircleCheck, CircleClose, Plus } from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'
import AudioPlayer from '@/components/AudioPlayer.vue'
import * as exportApi from '@/api/export'
import * as voicesApi from '@/api/voices'
import * as storyboardApi from '@/api/storyboard'
import * as projectsApi from '@/api/projects'
import * as tasksApi from '@/api/tasks'
import type { TaskStatus } from '@/api/tasks'
import type { Scene } from '@/api/storyboard'

const router = useRouter()
const projectStore = useProjectStore()

const scenes = ref<Scene[]>([])
const sceneAudios = ref<Map<string, { cn?: string; en?: string }>>(new Map())
const fullAudioCnUrl = ref<string | null>(null)
const fullAudioEnUrl = ref<string | null>(null)
const hasExport = ref(false)
const downloadUrl = ref<string | null>(null)
const projectTopic = ref('')
const projectAudience = ref('')
const isExporting = ref(false)
const taskId = ref('')
const taskStatus = ref<TaskStatus | ''>('')
const progress = ref(0)
const progressMessage = ref('')
const errorMessage = ref('')

const projectData = computed(() => projectStore.projectData)
const projectStatus = computed(() => projectStore.projectStatus)
const canExport = computed(() => projectStore.currentProjectId && !isExporting.value && scenes.value.length > 0)

onMounted(async () => { if (projectStore.currentProjectId) await loadProjectData() })
watch(() => projectStore.currentProjectId, async (id) => { if (id) await loadProjectData() })

async function loadProjectData() {
  if (!projectStore.currentProjectId) return
  try { await projectStore.refreshProject(); await loadScenes(); await loadSceneAudios(); await loadFullAudio(); await checkExportStatus() }
  catch (e) { console.error('Failed to load:', e) }
}
async function loadScenes() {
  if (!projectStore.currentProjectId) return
  try {
    const res = await storyboardApi.getScenes(projectStore.currentProjectId)
    scenes.value = res.scenes
    const info = await projectsApi.getProject(projectStore.currentProjectId)
    if (info) { projectTopic.value = info.goal?.topic || ''; projectAudience.value = info.goal?.target_audience || '' }
  } catch (e) { console.error(e) }
}
async function loadSceneAudios() {
  if (!projectStore.currentProjectId) return
  // 并发请求所有分镜的音频
  const promises = scenes.value.map(async (s) => {
    try {
      const r = await voicesApi.getSceneAudio(projectStore.currentProjectId!, s.scene_id)
      return { id: s.scene_id, cn: r.audio_cn_url || undefined, en: r.audio_en_url || undefined }
    } catch {
      return { id: s.scene_id, cn: undefined, en: undefined }
    }
  })
  const results = await Promise.all(promises)
  results.forEach(r => sceneAudios.value.set(r.id, { cn: r.cn, en: r.en }))
}
function getSceneAudioUrl(id: string, lang: 'cn'|'en'): string|null { const a = sceneAudios.value.get(id); return a ? (lang === 'cn' ? a.cn ?? null : a.en ?? null) : null }
async function loadFullAudio() { if (!projectStore.currentProjectId) return; try { const r = await voicesApi.getFullAudio(projectStore.currentProjectId); fullAudioCnUrl.value = r.full_cn_url || null; fullAudioEnUrl.value = r.full_en_url || null } catch {} }
async function checkExportStatus() {
  if (!projectStore.currentProjectId) return
  try {
    const r = await exportApi.getExportStatus(projectStore.currentProjectId)
    hasExport.value = r.has_export
    downloadUrl.value = r.download_url || null
    if (r.has_export) taskStatus.value = 'completed'
  } catch {}
}

async function handleStartExport() {
  if (!projectStore.currentProjectId) { ElMessage.warning('请先创建或加载项目'); return }
  isExporting.value = true; taskStatus.value = 'pending'; progress.value = 0; progressMessage.value = '正在启动...'; errorMessage.value = ''
  try { const r = await exportApi.exportProject(projectStore.currentProjectId); taskId.value = r.task_id; await pollTaskStatus() }
  catch (e: any) { isExporting.value = false; taskStatus.value = 'failed'; errorMessage.value = e.response?.data?.detail?.message || '启动失败'; ElMessage.error(errorMessage.value) }
}
async function pollTaskStatus() {
  try {
    const final = await tasksApi.pollTaskStatus(taskId.value, (t) => { taskStatus.value = t.status; progress.value = t.progress; progressMessage.value = t.message }, 1000)
    isExporting.value = false
    if (final.status === 'completed') {
      ElMessage.success('导出完成')
      hasExport.value = true
      await checkExportStatus()
      await projectStore.refreshProject()
    }
    else if (final.status === 'failed') { errorMessage.value = final.error || '导出失败'; ElMessage.error('导出失败') }
  } catch (e: any) { isExporting.value = false; taskStatus.value = 'failed'; errorMessage.value = e.response?.data?.detail?.message || '获取状态失败'; ElMessage.error(errorMessage.value) }
}
function handleDownload() {
  if (downloadUrl.value) {
    window.open(downloadUrl.value, '_blank')
    ElMessage.success('开始下载')
  } else {
    ElMessage.warning('下载链接不存在')
  }
}
function handleRetry() { taskStatus.value = ''; taskId.value = ''; progress.value = 0; progressMessage.value = ''; errorMessage.value = '' }
function handleReExport() { hasExport.value = false; downloadUrl.value = null; handleRetry() }
function handleCreateNew() { projectStore.reset(); router.push('/step/1'); ElMessage.success('已清除当前项目，可以创建新项目了') }
function handlePrevStep() { projectStore.setStep(5); router.push('/step/5') }
function getStatusTagType(s: string): 'success'|'warning'|'info'|'danger' { 
  return ({ 
    initialized:'info', 
    storyboard_ready:'warning', 
    images_generating:'warning',
    images_ready:'warning', 
    audio_generating:'primary',
    audio_ready:'success', 
    subtitles_ready:'success',
    completed:'success' 
  } as any)[s] || 'info' 
}
function getStatusText(s: string): string { 
  return ({ 
    initialized:'已初始化', 
    storyboard_ready:'分镜已生成', 
    images_generating:'图片生成中',
    images_ready:'图片已生成', 
    audio_generating:'音频生成中',
    audio_ready:'音频已生成', 
    subtitles_ready:'字幕已生成',
    completed:'已完成' 
  } as any)[s] || s 
}
function getTaskStatusTagType(s: TaskStatus|''): 'success'|'warning'|'info'|'danger' { return ({ pending:'info', running:'warning', completed:'success', failed:'danger' } as any)[s] || 'info' }
function getTaskStatusText(s: TaskStatus|''): string { return ({ pending:'等待中', running:'导出中', completed:'已完成', failed:'失败' } as any)[s] || s }
function getExportIconClass(): string { if (taskStatus.value === 'completed' || hasExport.value) return 'success'; if (taskStatus.value === 'failed') return 'error'; if (isExporting.value || taskStatus.value === 'running') return 'running'; return '' }
</script>

<style scoped>
.step-export { padding: 32px; }
.page-header { margin-bottom: 28px; text-align: center; }
.page-title { display: inline-flex; align-items: center; gap: 12px; font-size: 26px; font-weight: 600; color: var(--text-primary); margin: 0 0 6px 0; }
.title-icon { color: #67c23a; font-size: 30px; }
.page-subtitle { color: var(--text-muted); font-size: 14px; margin: 0; }

.content-wrapper { max-width: 1000px; margin: 0 auto; }

/* Card */
.card { background: var(--bg-card); border-radius: 14px; box-shadow: var(--shadow-sm); margin-bottom: 20px; }
.card-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid var(--border-light); }
.header-left { display: flex; align-items: center; gap: 12px; }
.header-left h3 { margin: 0; font-size: 16px; font-weight: 600; color: var(--text-primary); }
.header-icon { width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; color: #fff; }
.info-icon { background: linear-gradient(135deg, #909399, #b1b3b8); }
.audio-icon { background: linear-gradient(135deg, #e6a23c, #f0b85a); }
.scenes-icon { background: linear-gradient(135deg, #409eff, #66b1ff); }
.export-icon { background: linear-gradient(135deg, #67c23a, #85ce61); }
.export-icon.running { background: linear-gradient(135deg, #e6a23c, #f0b85a); animation: pulse 2s infinite; }
.export-icon.success { background: linear-gradient(135deg, #67c23a, #85ce61); }
.export-icon.error { background: linear-gradient(135deg, #f56c6c, #f89898); }
@keyframes pulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.05)} }
.card-body { padding: 20px 24px; }

/* Info */
.info-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
.info-item { display: flex; flex-direction: column; gap: 6px; }
.info-item .label { font-size: 12px; color: var(--text-muted); }
.info-item .value { font-size: 14px; color: var(--text-primary); font-weight: 500; }

/* Full Audio */
.full-audio-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.full-audio-item { display: flex; flex-direction: column; gap: 12px; }
.audio-box { background: var(--bg-secondary); border-radius: 10px; padding: 16px; min-height: 80px; display: flex; align-items: center; }
.audio-box > * { flex: 1; min-width: 0; }
.no-audio { display: flex; align-items: center; justify-content: center; gap: 8px; color: var(--text-muted); font-size: 13px; width: 100%; }

/* Scenes */
.scenes-list { display: flex; flex-direction: column; gap: 16px; }
.scene-item { display: flex; gap: 24px; padding: 20px; background: var(--bg-secondary); border-radius: 12px; border: 1px solid var(--border-light); transition: all 0.2s; }
.scene-item:hover { border-color: #409eff; box-shadow: 0 4px 16px rgba(64,158,255,0.1); }
.scene-left { display: flex; flex-direction: column; align-items: center; gap: 10px; flex-shrink: 0; }
.scene-num { font-size: 24px; font-weight: 700; color: #409eff; font-family: 'Monaco', monospace; }
.scene-img { width: 280px; height: 180px; border-radius: 10px; overflow: hidden; background: var(--border-color); }
.scene-img .el-image { width: 100%; height: 100%; }
.img-err, .img-empty { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: var(--text-muted); font-size: 40px; }
.scene-right { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 16px; }
.narrations { display: flex; flex-direction: column; gap: 12px; }
.narration { display: flex; flex-direction: column; gap: 4px; }
.narration .lang { font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: 4px; width: fit-content; }
.narration.cn .lang { color: #f56c6c; background: rgba(245, 108, 108, 0.1); }
.narration.en .lang { color: #409eff; background: rgba(64, 158, 255, 0.1); }
.narration p { margin: 0; font-size: 14px; line-height: 1.6; color: var(--text-secondary); }
.narration.en p { color: var(--text-muted); font-style: italic; }
.audios { display: flex; flex-direction: column; gap: 10px; padding-top: 14px; border-top: 1px dashed var(--border-color); }
.audio-row { display: flex; align-items: center; gap: 12px; }
.audio-label { font-size: 12px; font-weight: 500; min-width: 64px; padding: 4px 10px; border-radius: 6px; text-align: center; }
.audio-label.cn { color: #f56c6c; background: rgba(245, 108, 108, 0.1); }
.audio-label.en { color: #409eff; background: rgba(64, 158, 255, 0.1); }
.audio-player { flex: 1; min-width: 0; }

/* Export */
.export-content { display: flex; flex-direction: column; align-items: center; gap: 20px; padding: 20px 0; }
.export-content p { margin: 0; font-size: 14px; color: var(--text-muted); }
.export-items { display: flex; gap: 16px; flex-wrap: wrap; justify-content: center; }
.export-items .item { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--text-secondary); background: var(--bg-secondary); padding: 10px 16px; border-radius: 8px; }
.export-items .item .el-icon { color: #67c23a; font-size: 18px; }
.export-btn { min-width: 200px; height: 48px; font-size: 15px; font-weight: 500; border-radius: 10px; background: linear-gradient(135deg, #67c23a, #85ce61); border: none; }
.export-btn:hover:not(:disabled) { background: linear-gradient(135deg, #529b2e, #67c23a); }
.progress-ring { position: relative; width: 100px; height: 100px; }
.progress-ring svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.progress-ring .bg { fill: none; stroke: var(--border-color); stroke-width: 8; }
.progress-ring .bar { fill: none; stroke: #67c23a; stroke-width: 8; stroke-linecap: round; stroke-dasharray: 264; transition: stroke-dashoffset 0.4s; }
.progress-ring .num { position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%); font-size: 20px; font-weight: 700; color: #67c23a; }
.done-icon { font-size: 56px; color: #67c23a; }
.failed-icon { font-size: 56px; color: #f56c6c; }
.done-btns { display: flex; gap: 12px; }

/* Nav */
.nav-btns { display: flex; justify-content: space-between; padding-top: 10px; }

/* Responsive */
@media (max-width: 768px) {
  .step-export { padding: 16px; }
  .page-title { font-size: 20px; }
  .info-grid { grid-template-columns: repeat(2, 1fr); }
  .full-audio-grid { grid-template-columns: 1fr; }
  .scene-item { flex-direction: column; }
  .scene-left { flex-direction: row; width: 100%; justify-content: space-between; align-items: center; }
  .scene-img { width: 160px; height: 100px; }
}
</style>
