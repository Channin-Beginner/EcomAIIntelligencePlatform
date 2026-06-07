import { computed, onMounted, onUnmounted, ref } from 'vue'

const LAYOUT_KEY = 'ecomai-assistant-layout'

interface WindowLayout {
  x: number
  y: number
  w: number
  h: number
}

const MIN_W = 420
const MIN_H = 480

function defaultLayout(): WindowLayout {
  const w = Math.min(920, window.innerWidth - 48)
  const h = Math.min(680, window.innerHeight - 48)
  return {
    x: Math.max(24, window.innerWidth - w - 24),
    y: Math.max(24, window.innerHeight - h - 24),
    w,
    h,
  }
}

function loadLayout(): WindowLayout {
  try {
    const raw = localStorage.getItem(LAYOUT_KEY)
    if (!raw) return defaultLayout()
    const parsed = JSON.parse(raw) as WindowLayout
    if (typeof parsed.x === 'number' && typeof parsed.w === 'number') {
      return {
        x: Math.max(0, parsed.x),
        y: Math.max(0, parsed.y),
        w: Math.max(MIN_W, Math.min(parsed.w, window.innerWidth - 16)),
        h: Math.max(MIN_H, Math.min(parsed.h, window.innerHeight - 16)),
      }
    }
  } catch {
    /* ignore */
  }
  return defaultLayout()
}

function saveLayout(layout: WindowLayout) {
  localStorage.setItem(LAYOUT_KEY, JSON.stringify(layout))
}

export function useFloatingWindow() {
  const layout = ref<WindowLayout>(defaultLayout())
  const dragging = ref(false)
  const resizing = ref(false)
  const dragStart = { x: 0, y: 0, winX: 0, winY: 0 }
  const resizeStart = { x: 0, y: 0, w: 0, h: 0 }

  const windowStyle = computed(() => ({
    left: `${layout.value.x}px`,
    top: `${layout.value.y}px`,
    width: `${layout.value.w}px`,
    height: `${layout.value.h}px`,
  }))

  function initLayout() {
    layout.value = loadLayout()
  }

  function onDragMove(e: MouseEvent) {
    if (dragging.value) {
      const dx = e.clientX - dragStart.x
      const dy = e.clientY - dragStart.y
      layout.value = {
        ...layout.value,
        x: Math.max(0, Math.min(dragStart.winX + dx, window.innerWidth - layout.value.w)),
        y: Math.max(0, Math.min(dragStart.winY + dy, window.innerHeight - layout.value.h)),
      }
    } else if (resizing.value) {
      const dw = e.clientX - resizeStart.x
      const dh = e.clientY - resizeStart.y
      layout.value = {
        ...layout.value,
        w: Math.max(MIN_W, Math.min(resizeStart.w + dw, window.innerWidth - layout.value.x)),
        h: Math.max(MIN_H, Math.min(resizeStart.h + dh, window.innerHeight - layout.value.y)),
      }
    }
  }

  function onDragEnd() {
    if (dragging.value || resizing.value) {
      dragging.value = false
      resizing.value = false
      saveLayout(layout.value)
    }
  }

  function startDrag(e: MouseEvent) {
    if (e.button !== 0) return
    dragging.value = true
    dragStart.x = e.clientX
    dragStart.y = e.clientY
    dragStart.winX = layout.value.x
    dragStart.winY = layout.value.y
    e.preventDefault()
  }

  function startResize(e: MouseEvent) {
    if (e.button !== 0) return
    resizing.value = true
    resizeStart.x = e.clientX
    resizeStart.y = e.clientY
    resizeStart.w = layout.value.w
    resizeStart.h = layout.value.h
    e.preventDefault()
    e.stopPropagation()
  }

  onMounted(() => {
    initLayout()
    window.addEventListener('mousemove', onDragMove)
    window.addEventListener('mouseup', onDragEnd)
  })

  onUnmounted(() => {
    window.removeEventListener('mousemove', onDragMove)
    window.removeEventListener('mouseup', onDragEnd)
  })

  return {
    layout,
    windowStyle,
    dragging,
    resizing,
    startDrag,
    startResize,
    initLayout,
  }
}
