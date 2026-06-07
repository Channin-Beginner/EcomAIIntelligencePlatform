<script setup lang="ts">
import { computed, inject, nextTick, onMounted, onUnmounted, ref, watch, type Ref } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, FunnelChart, LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TitleComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import {
  fetchAssistantSuggestions,
  queryAssistant,
  type AssistantQueryResult,
  type ChartPayload,
} from '@/api/assistant'
import { useAssistantSessions } from '@/composables/useAssistantSessions'
import { useFloatingWindow } from '@/composables/useFloatingWindow'
import { todayYmd } from '@/utils/date'

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  PieChart,
  FunnelChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
])

const opsRefDate = inject<Ref<string>>('opsRefDate', ref(todayYmd()))

const open = ref(false)
const input = ref('')
const sending = ref(false)
const suggestions = ref<string[]>([])
const chatBodyRef = ref<HTMLElement | null>(null)
const openMenuId = ref<string | null>(null)

const {
  sessions,
  activeSessionId,
  messages,
  activeTitle,
  startNewChat,
  ensureSession,
  selectSession,
  togglePin,
  renameSession,
  deleteSession,
  touchActive,
} = useAssistantSessions()

const { windowStyle, startDrag, startResize, initLayout } = useFloatingWindow()

const showWelcome = computed(() => messages.value.length === 0 && !sending.value)

async function loadSuggestions() {
  try {
    suggestions.value = await fetchAssistantSuggestions()
  } catch {
    suggestions.value = [
      '今日 GMV 和订单数是多少？',
      '展示近 30 天 GMV 趋势',
      '转化漏斗各阶段人数',
      '当日 UV 和 PV 是多少？',
    ]
  }
}

function scrollToBottom() {
  nextTick(() => {
    const el = chatBodyRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function toggleOpen() {
  open.value = !open.value
  if (open.value) {
    initLayout()
    openMenuId.value = null
  } else {
    touchActive()
  }
}

function handleNewChat() {
  startNewChat()
  openMenuId.value = null
}

function toggleMenu(id: string, e: MouseEvent) {
  e.stopPropagation()
  openMenuId.value = openMenuId.value === id ? null : id
}

function closeMenu() {
  openMenuId.value = null
}

function onPin(id: string) {
  togglePin(id)
  closeMenu()
}

function onRename(id: string) {
  const s = sessions.value.find(x => x.id === id)
  const next = window.prompt('重命名对话', s?.title ?? '')
  if (next != null) renameSession(id, next)
  closeMenu()
}

function onDelete(id: string) {
  if (window.confirm('确定删除该对话？')) deleteSession(id)
  closeMenu()
}

async function sendQuestion(text: string) {
  const q = text.trim()
  if (!q || sending.value) return

  ensureSession(q)
  messages.value.push({ id: `u-${Date.now()}`, role: 'user', text: q })
  const loadingId = `a-${Date.now()}`
  messages.value.push({ id: loadingId, role: 'assistant', text: '', loading: true })
  input.value = ''
  sending.value = true
  scrollToBottom()

  try {
    const result = await queryAssistant(q, opsRefDate.value)
    const idx = messages.value.findIndex(m => m.id === loadingId)
    if (idx >= 0) {
      messages.value[idx] = {
        id: loadingId,
        role: 'assistant',
        text: result.answer,
        result,
      }
    }
    touchActive()
  } catch (e) {
    const idx = messages.value.findIndex(m => m.id === loadingId)
    const msg = e instanceof Error ? e.message : '请求失败'
    if (idx >= 0) {
      messages.value[idx] = {
        id: loadingId,
        role: 'assistant',
        text: `抱歉，分析失败：${msg}`,
      }
    }
    touchActive()
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

function onSubmit() {
  sendQuestion(input.value)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    onSubmit()
  }
}

function onGlobalKey(e: KeyboardEvent) {
  if (!open.value) return
  if (e.ctrlKey && (e.key === 'k' || e.key === 'K')) {
    e.preventDefault()
    handleNewChat()
  }
}

function hasChart(chart: ChartPayload) {
  return chart.type !== 'none' && chart.type !== 'table' && chart.option
}

onMounted(() => {
  loadSuggestions()
  window.addEventListener('keydown', onGlobalKey)
  document.addEventListener('click', closeMenu)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onGlobalKey)
  document.removeEventListener('click', closeMenu)
  touchActive()
})

watch(open, v => {
  if (v && suggestions.value.length === 0) loadSuggestions()
})
</script>

<template>
  <div class="bi-assistant-root">
    <button
      v-if="!open"
      type="button"
      class="bi-fab"
      aria-label="打开 EcomAI 助手"
      @click="toggleOpen"
    >
      <span class="bi-fab__icon">✦</span>
      <span class="bi-fab__label">EcomAI</span>
    </button>

    <div
      v-if="open"
      class="bi-window"
      role="dialog"
      aria-label="EcomAI 智能助手"
      :style="windowStyle"
      @click.stop
    >
      <aside class="bi-sidebar">
        <div class="bi-sidebar__brand">
          <span class="bi-sidebar__logo">豆</span>
          <span class="bi-sidebar__name">EcomAI</span>
        </div>
        <button type="button" class="bi-sidebar__new" @click="handleNewChat">
          <span>＋</span> 新对话
          <kbd>Ctrl K</kbd>
        </button>
        <div class="bi-sidebar__section">
          <div class="bi-sidebar__section-title">历史对话</div>
          <div v-if="sessions.length === 0" class="bi-sidebar__empty">暂无历史，发送消息后将自动保存</div>
          <div
            v-for="item in sessions"
            :key="item.id"
            class="bi-sidebar__history-item"
            :class="{ 'bi-sidebar__history-item--active': item.id === activeSessionId }"
            @click="selectSession(item.id)"
          >
            <span class="bi-sidebar__history-icon">{{ item.pinned ? '📌' : '💬' }}</span>
            <span class="bi-sidebar__history-title" :title="item.title">{{ item.title }}</span>
            <button
              type="button"
              class="bi-sidebar__history-more"
              aria-label="更多操作"
              @click="toggleMenu(item.id, $event)"
            >
              ···
            </button>
            <div
              v-if="openMenuId === item.id"
              class="bi-history-menu"
              @click.stop
            >
              <button type="button" @click="onPin(item.id)">
                <span>📌</span> {{ item.pinned ? '取消置顶' : '置顶' }}
              </button>
              <button type="button" @click="onRename(item.id)">
                <span>✎</span> 重命名
              </button>
              <button type="button" class="bi-history-menu__danger" @click="onDelete(item.id)">
                <span>🗑</span> 删除
              </button>
            </div>
          </div>
        </div>
        <div class="bi-sidebar__footer">
          <span class="bi-sidebar__avatar">运</span>
          <span>运营分析师</span>
        </div>
      </aside>

      <main class="bi-main">
        <header class="bi-header" @mousedown="startDrag">
          <h2 class="bi-header__title">{{ activeTitle }}</h2>
          <div class="bi-header__actions">
            <span class="bi-header__date">参考日 {{ opsRefDate }}</span>
            <button type="button" class="bi-header__close" aria-label="关闭" @mousedown.stop @click="toggleOpen">
              ×
            </button>
          </div>
        </header>

        <div ref="chatBodyRef" class="bi-body">
          <div v-if="showWelcome" class="bi-welcome">
            <h1 class="bi-welcome__title">有什么我能帮你的吗？</h1>
            <div class="bi-suggestions">
              <button
                v-for="(s, i) in suggestions"
                :key="i"
                type="button"
                class="bi-suggestion"
                @click="sendQuestion(s)"
              >
                {{ s }}
              </button>
            </div>
          </div>

          <div v-for="msg in messages" :key="msg.id" class="bi-msg" :class="`bi-msg--${msg.role}`">
            <div v-if="msg.role === 'assistant'" class="bi-msg__avatar">豆</div>
            <div class="bi-msg__bubble">
              <div v-if="msg.loading" class="bi-msg__loading">
                <span></span><span></span><span></span>
              </div>
              <template v-else>
                <p class="bi-msg__text">{{ msg.text }}</p>
                <div v-if="msg.result?.chart && hasChart(msg.result.chart)" class="bi-msg__chart">
                  <v-chart :option="msg.result.chart.option!" autoresize />
                </div>
                <table v-if="msg.result?.table?.rows?.length" class="bi-table">
                  <thead>
                    <tr>
                      <th v-for="col in msg.result.table.columns" :key="col">{{ col }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, ri) in msg.result.table.rows.slice(0, 8)" :key="ri">
                      <td v-for="(cell, ci) in row" :key="ci">{{ cell }}</td>
                    </tr>
                  </tbody>
                </table>
                <details v-if="msg.result?.sql" class="bi-sql">
                  <summary>查看 SQL</summary>
                  <pre>{{ msg.result.sql }}</pre>
                </details>
              </template>
            </div>
          </div>
        </div>

        <footer class="bi-input-wrap">
          <div class="bi-input-box">
            <textarea
              v-model="input"
              class="bi-input"
              rows="1"
              placeholder="发消息或输入想分析的数据问题…"
              :disabled="sending"
              @keydown="onKeydown"
            />
            <div class="bi-input-toolbar">
              <div class="bi-input-tags">
                <span class="bi-tag">深度思考</span>
                <span class="bi-tag bi-tag--active">EcomAI</span>
                <span class="bi-tag">数据解读</span>
              </div>
              <button
                type="button"
                class="bi-send"
                :disabled="sending || !input.trim()"
                aria-label="发送"
                @click="onSubmit"
              >
                ↑
              </button>
            </div>
          </div>
        </footer>
      </main>

      <div class="bi-resize-handle" title="拖动缩放" @mousedown="startResize" />
    </div>
  </div>
</template>

<style scoped>
.bi-assistant-root {
  position: fixed;
  inset: 0;
  z-index: 9999;
  pointer-events: none;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.bi-fab {
  position: fixed;
  right: 24px;
  bottom: 24px;
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px;
  border: none;
  border-radius: 999px;
  background: linear-gradient(135deg, #4f8cff, #6c5ce7);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 8px 28px rgba(79, 140, 255, 0.45);
  transition: transform 0.15s, box-shadow 0.15s;
}

.bi-fab:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(79, 140, 255, 0.55);
}

.bi-fab__icon {
  font-size: 16px;
}

.bi-window {
  position: fixed;
  pointer-events: auto;
  display: flex;
  border-radius: 16px;
  overflow: hidden;
  background: #f7f8fa;
  box-shadow: 0 24px 80px rgba(15, 23, 42, 0.28);
  border: 1px solid rgba(0, 0, 0, 0.06);
  min-width: 420px;
  min-height: 480px;
}

.bi-resize-handle {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 18px;
  height: 18px;
  cursor: se-resize;
  z-index: 10;
  background: linear-gradient(135deg, transparent 50%, rgba(0, 0, 0, 0.12) 50%);
  border-bottom-right-radius: 16px;
}

.bi-sidebar {
  width: 200px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-right: 1px solid #eceef2;
  padding: 16px 12px;
  min-height: 0;
}

.bi-sidebar__brand {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding: 0 4px;
}

.bi-sidebar__logo {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: linear-gradient(135deg, #4f8cff, #a78bfa);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
}

.bi-sidebar__name {
  font-weight: 600;
  font-size: 15px;
  color: #1a1a2e;
}

.bi-sidebar__new {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 10px 12px;
  margin-bottom: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fafbfc;
  color: #374151;
  font-size: 13px;
  cursor: pointer;
}

.bi-sidebar__new:hover {
  background: #f3f4f6;
}

.bi-sidebar__new kbd {
  margin-left: auto;
  font-size: 10px;
  color: #9ca3af;
  background: #f3f4f6;
  padding: 2px 5px;
  border-radius: 4px;
}

.bi-sidebar__section {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.bi-sidebar__section-title {
  font-size: 11px;
  color: #9ca3af;
  margin-bottom: 8px;
  padding: 0 4px;
}

.bi-sidebar__empty {
  font-size: 12px;
  color: #9ca3af;
  padding: 8px 10px;
  line-height: 1.5;
}

.bi-sidebar__history-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 8px;
  border-radius: 8px;
  font-size: 13px;
  color: #4b5563;
  cursor: pointer;
}

.bi-sidebar__history-item:hover {
  background: #f3f4f6;
}

.bi-sidebar__history-item--active {
  background: #eff6ff;
  color: #2563eb;
}

.bi-sidebar__history-icon {
  flex-shrink: 0;
  font-size: 12px;
}

.bi-sidebar__history-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bi-sidebar__history-more {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #9ca3af;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  opacity: 0;
}

.bi-sidebar__history-item:hover .bi-sidebar__history-more,
.bi-sidebar__history-item--active .bi-sidebar__history-more {
  opacity: 1;
}

.bi-sidebar__history-more:hover {
  background: rgba(0, 0, 0, 0.06);
  color: #374151;
}

.bi-history-menu {
  position: absolute;
  right: 4px;
  top: 100%;
  z-index: 20;
  min-width: 140px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  padding: 6px;
}

.bi-history-menu button {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  border: none;
  border-radius: 6px;
  background: transparent;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
  text-align: left;
}

.bi-history-menu button:hover {
  background: #f3f4f6;
}

.bi-history-menu__danger {
  color: #dc2626 !important;
}

.bi-sidebar__footer {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 4px;
  font-size: 12px;
  color: #6b7280;
}

.bi-sidebar__avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.bi-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  background: #fff;
}

.bi-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid #f0f1f3;
  cursor: move;
  user-select: none;
  flex-shrink: 0;
}

.bi-header__title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.bi-header__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.bi-header__date {
  font-size: 12px;
  color: #9ca3af;
  cursor: default;
}

.bi-header__close {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: transparent;
  font-size: 22px;
  line-height: 1;
  color: #6b7280;
  cursor: pointer;
}

.bi-header__close:hover {
  background: #f3f4f6;
}

.bi-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
  min-height: 0;
}

.bi-welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 240px;
  text-align: center;
}

.bi-welcome__title {
  font-size: 28px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 28px;
}

.bi-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  max-width: 560px;
}

.bi-suggestion {
  padding: 10px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fafbfc;
  color: #374151;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.bi-suggestion:hover {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1d4ed8;
}

.bi-msg {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.bi-msg--user {
  flex-direction: row-reverse;
}

.bi-msg__avatar {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  border-radius: 50%;
  background: linear-gradient(135deg, #4f8cff, #a78bfa);
  color: #fff;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}

.bi-msg__bubble {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.6;
}

.bi-msg--user .bi-msg__bubble {
  background: #4f8cff;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.bi-msg--assistant .bi-msg__bubble {
  background: #f3f4f6;
  color: #1f2937;
  border-bottom-left-radius: 4px;
}

.bi-msg__text {
  margin: 0;
  white-space: pre-wrap;
}

.bi-msg__chart {
  margin-top: 12px;
  height: 220px;
  background: #fff;
  border-radius: 10px;
  padding: 8px;
}

.bi-table {
  margin-top: 10px;
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}

.bi-table th,
.bi-table td {
  border: 1px solid #e5e7eb;
  padding: 6px 8px;
  text-align: left;
}

.bi-table th {
  background: #f9fafb;
  font-weight: 600;
}

.bi-sql {
  margin-top: 8px;
  font-size: 11px;
  color: #6b7280;
}

.bi-sql pre {
  margin-top: 6px;
  padding: 8px;
  background: #1e293b;
  color: #e2e8f0;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 11px;
}

.bi-msg__loading {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}

.bi-msg__loading span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #9ca3af;
  animation: bi-bounce 1.2s infinite ease-in-out;
}

.bi-msg__loading span:nth-child(2) {
  animation-delay: 0.15s;
}

.bi-msg__loading span:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes bi-bounce {
  0%,
  80%,
  100% {
    transform: scale(0.6);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.bi-input-wrap {
  padding: 12px 20px 20px;
  background: linear-gradient(to top, #fff 80%, transparent);
  flex-shrink: 0;
}

.bi-input-box {
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  background: #fafbfc;
  padding: 12px 14px 10px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.bi-input {
  width: 100%;
  border: none;
  background: transparent;
  resize: none;
  font-size: 14px;
  line-height: 1.5;
  color: #111827;
  outline: none;
  min-height: 24px;
  max-height: 120px;
}

.bi-input::placeholder {
  color: #9ca3af;
}

.bi-input-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
}

.bi-input-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.bi-tag {
  font-size: 11px;
  color: #6b7280;
  padding: 4px 8px;
  border-radius: 6px;
  background: #f3f4f6;
}

.bi-tag--active {
  background: #eff6ff;
  color: #2563eb;
}

.bi-send {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: #111827;
  color: #fff;
  font-size: 18px;
  cursor: pointer;
  flex-shrink: 0;
}

.bi-send:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .bi-sidebar {
    display: none;
  }
}
</style>
