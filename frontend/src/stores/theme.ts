import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type ThemeMode = 'light' | 'dark'

export const useThemeStore = defineStore('theme', () => {
  // 从 localStorage 恢复，默认 light
  const mode = ref<ThemeMode>((localStorage.getItem('theme') as ThemeMode) || 'light')
  const snowEnabled = ref<boolean>(localStorage.getItem('snow') === 'true')

  // 监听变化并持久化
  watch(mode, (val) => {
    localStorage.setItem('theme', val)
    applyTheme(val)
  })

  watch(snowEnabled, (val) => {
    localStorage.setItem('snow', String(val))
    applySnow(val)
  })

  // 应用主题到 DOM
  function applyTheme(theme: ThemeMode) {
    document.documentElement.setAttribute('data-theme', theme)
    // 同时设置 Element Plus 的暗黑模式
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  // 应用下雪效果
  function applySnow(enabled: boolean) {
    if (enabled) {
      document.documentElement.classList.add('snow-mode')
      createSnowflakes()
      createSnowPiles()
      createFooterSnow()
      setupMutationObserver()
    } else {
      document.documentElement.classList.remove('snow-mode')
      removeSnowflakes()
      removeSnowPiles()
      removeFooterSnow()
    }
  }

  // 创建雪花
  function createSnowflakes() {
    // 移除已存在的雪花容器
    removeSnowflakes()

    const container = document.createElement('div')
    container.className = 'snowflakes-container'
    container.setAttribute('aria-hidden', 'true')

    // 创建多个雪花
    for (let i = 0; i < 50; i++) {
      const snowflake = document.createElement('div')
      snowflake.className = 'snowflake'
      snowflake.innerHTML = '❄'
      snowflake.style.left = `${Math.random() * 100}%`
      snowflake.style.animationDelay = `${Math.random() * 10}s`
      snowflake.style.animationDuration = `${8 + Math.random() * 12}s`
      snowflake.style.opacity = `${0.4 + Math.random() * 0.6}`
      snowflake.style.fontSize = `${8 + Math.random() * 16}px`
      container.appendChild(snowflake)
    }

    document.body.appendChild(container)
  }

  // 移除雪花
  function removeSnowflakes() {
    const existing = document.querySelector('.snowflakes-container')
    if (existing) {
      existing.remove()
    }
  }

  // 积雪目标选择器
  const snowSelectors = [
    '.step-bar',
    '.create-card',
    '.projects-card',
    '.login-card',
    '.result-card',
    '.el-card',
    '.card',
    '.summary-bar',
    '.scene-card',
    '.page-header',
    '.main-content'
  ]
  const snowSelectorString = snowSelectors.join(', ')

  // 创建积雪效果
  function createSnowPiles() {
    // removeSnowPiles() 

    snowSelectors.forEach(selector => {
      const elements = document.querySelectorAll(selector)
      elements.forEach((el) => {
        if (el.querySelector('.snow-pile-container')) return // 已有积雪

        // 检查元素是否有背景色（排除透明背景）
        const computed = window.getComputedStyle(el)
        const bgColor = computed.backgroundColor
        if (bgColor === 'transparent' || bgColor === 'rgba(0, 0, 0, 0)') {
          return // 跳过没有背景色的元素
        }

        // 确保父元素有相对定位和 overflow visible
        if (computed.position === 'static') {
          (el as HTMLElement).style.position = 'relative'
        }
        (el as HTMLElement).style.overflow = 'visible'

        // 修复因为 overflow: visible 导致的圆角失效问题
        // 尝试找到第一个子元素（通常是 header），赋予它与父元素相同的顶部圆角
        const firstChild = el.firstElementChild as HTMLElement
        if (firstChild) {
          const parentStyle = window.getComputedStyle(el)
          const radiusTopLeft = parentStyle.borderTopLeftRadius
          const radiusTopRight = parentStyle.borderTopRightRadius

          if (radiusTopLeft !== '0px') firstChild.style.borderTopLeftRadius = radiusTopLeft
          if (radiusTopRight !== '0px') firstChild.style.borderTopRightRadius = radiusTopRight
        }

        // 创建积雪容器
        const container = document.createElement('div')
        container.className = 'snow-pile-container'
        container.setAttribute('aria-hidden', 'true')

        const width = el.clientWidth

        // 1. 生成顶部积雪 (Snow Clumps) - Fluffy Version
        // 使用更密集的重叠圆来模拟松软的雪被
        // 大幅减少计算宽度，留出25px的安全余量，防止右侧溢出 (Optimized: closer to edge)
        const safeWidth = Math.max(0, width - 25)
        const clumpCount = Math.floor(safeWidth / 12)

        for (let i = 0; i < clumpCount; i++) {
          const clump = document.createElement('div')
          clump.className = 'snow-clump'

          // 随机大小，混合大块和小块
          const isLarge = Math.random() > 0.7
          const baseSize = isLarge ? 35 : 20
          const size = baseSize + Math.random() * 10

          // 位置更加随机和重叠
          const left = (i * 12) - 10 + (Math.random() * 10 - 5)

          // 绝对防溢出检查：如果雪球右边缘超过了容器宽度，直接跳过
          if (left + size > width) continue

          // 顶部位置浮动，制造起伏感
          const top = -12 + Math.random() * 8

          clump.style.width = `${size}px`
          clump.style.height = `${size * 0.7}px`
          clump.style.left = `${left}px`
          clump.style.top = `${top}px`

          // 更加圆润的形状
          const r1 = 50 + Math.random() * 20
          const r2 = 50 + Math.random() * 20
          clump.style.borderRadius = `${r1}% ${r2}% 40% 40%`

          container.appendChild(clump)
        }

        // 2. 生成冰挂/雪滴 (Soft Drips)
        // 减少冰挂数量，使其更厚实圆润
        const dripCount = Math.floor(width / 80)

        for (let i = 0; i < dripCount; i++) {
          const drip = document.createElement('div')
          drip.className = 'snow-icicle' // 复用类名，样式在CSS中调整

          const dWidth = 10 + Math.random() * 8 // 更宽
          const dHeight = 15 + Math.random() * 15 // 不要太长
          // 严格限制范围，防止溢出
          const dLeft = Math.random() * (width - 40) + 10

          drip.style.width = `${dWidth}px`
          drip.style.height = `${dHeight}px`
          drip.style.left = `${dLeft}px`
          drip.style.top = '5px' // 稍微下移，从雪堆里长出来

          container.appendChild(drip)
        }

        // 3. 填充层
        const snowCover = document.createElement('div')
        snowCover.className = 'snow-cover-layer'
        container.appendChild(snowCover)

        el.appendChild(container)
      })
    })
  }

  // 移除积雪
  function removeSnowPiles() {
    const piles = document.querySelectorAll('.snow-pile-container')
    piles.forEach(pile => pile.remove())

    // 兼容移除旧版
    const oldPiles = document.querySelectorAll('.snow-pile')
    oldPiles.forEach(pile => pile.remove())
  }

  // 刷新积雪（用于路由切换后）
  function refreshSnowPiles() {
    if (snowEnabled.value) {
      // 延迟执行，等待 DOM 渲染完成
      setTimeout(() => {
        createSnowPiles()
      }, 100)
    }
  }

  // 切换主题
  function toggleTheme() {
    mode.value = mode.value === 'light' ? 'dark' : 'light'
  }

  // 切换下雪
  function toggleSnow() {
    snowEnabled.value = !snowEnabled.value
  }

  // 初始化时应用主题和雪花
  function init() {
    applyTheme(mode.value)
    applySnow(snowEnabled.value)

    // 监听 DOM 变化，自动为新元素添加积雪
    if (snowEnabled.value) {
      setupMutationObserver()
    }
  }

  // 创建底部积雪 (Page Footer Snow)
  function createFooterSnow() {
    removeFooterSnow()

    // 优先获取挂载容器
    const app = document.getElementById('app')
    const container = app || document.body

    // 创建底部积雪层容器
    const layer = document.createElement('div')
    layer.className = 'snow-footer-layer'
    layer.setAttribute('aria-hidden', 'true')

    // 1. 添加平铺的基础雪层 (Base Ground)
    const base = document.createElement('div')
    base.className = 'snow-footer-base'
    layer.appendChild(base)

    // 使用容器实际宽度，确保覆盖全
    const width = container.scrollWidth || window.innerWidth

    // 2. 添加顶部的波浪雪堆 (Wavy Clumps)
    // 恢复较高密度以形成连续表面，但降低高度使其柔和 (Gentle continuous waves)
    const clumpCount = Math.ceil(width / 12)

    for (let i = 0; i < clumpCount; i++) {
      const clump = document.createElement('div')
      clump.className = 'snow-clump'

      // 变宽变扁：宽度 40-70px
      const w = 40 + Math.random() * 30
      // 高度较低：20-30px，形成平缓起伏
      const h = 20 + Math.random() * 10

      // 紧密重叠
      const left = (i * 12) - 20 + (Math.random() * 10 - 5)

      // 垂直位置：主要沉在下面，只露出一部分
      const bottom = -10 + Math.random() * 10

      clump.style.width = `${w}px`
      clump.style.height = `${h}px`
      clump.style.left = `${left}px`
      clump.style.bottom = `${bottom}px`
      clump.style.top = 'auto'

      // 形状
      clump.style.borderRadius = '50% 50% 20% 20%'
      clump.style.zIndex = '2' // 确保在 base 层之上

      layer.appendChild(clump)
    }

    // 挂载
    if (app) {
      const computed = window.getComputedStyle(app)
      if (computed.position === 'static') {
        app.style.position = 'relative'
      }
      app.appendChild(layer)
    } else {
      document.body.appendChild(layer)
    }
  }

  // 移除底部积雪
  function removeFooterSnow() {
    const existing = document.querySelector('.snow-footer-layer')
    if (existing) {
      existing.remove()
    }
  }

  // 监听窗口大小变化重新生成底部积雪
  let resizeTimeout: any = null
  window.addEventListener('resize', () => {
    if (snowEnabled.value) {
      if (resizeTimeout) clearTimeout(resizeTimeout)
      resizeTimeout = setTimeout(createFooterSnow, 200)
    }
  })

  // 设置 DOM 变化监听
  let observer: MutationObserver | null = null

  function setupMutationObserver() {
    if (observer) return

    observer = new MutationObserver((mutations) => {
      if (!snowEnabled.value) return

      let shouldRefresh = false
      mutations.forEach((mutation) => {
        if (mutation.addedNodes.length > 0) {
          mutation.addedNodes.forEach((node) => {
            if (node instanceof HTMLElement) {
              // 检查是否有需要添加积雪的元素
              if (node.matches?.(snowSelectorString) ||
                node.querySelector?.(snowSelectorString)) {
                shouldRefresh = true
              }
            }
          })
        }
      })

      if (shouldRefresh) {
        setTimeout(() => createSnowPiles(), 50)
      }
    })

    observer.observe(document.body, {
      childList: true,
      subtree: true
    })
  }

  return {
    mode,
    snowEnabled,
    toggleTheme,
    toggleSnow,
    init,
    refreshSnowPiles
  }
})
