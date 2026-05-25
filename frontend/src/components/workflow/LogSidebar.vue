<template>
  <Transition name="sidebar-right">
    <div
      v-if="isOpen"
      class="sidebar-panel sidebar-right"
    >
      <!-- 装饰背景 -->
      <div class="sidebar-grid"></div>
      <div class="sidebar-glow"></div>

      <!-- 头部 -->
      <div class="sidebar-header">
        <h3 class="text-lg font-semibold flex items-center gap-2">
          <svg class="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          执行日志
        </h3>
        <div class="flex items-center gap-2">
          <button
            @click="$emit('clear')"
            class="clear-btn"
          >
            清空
          </button>
          <button
            @click="$emit('close')"
            class="sidebar-close-btn"
            title="关闭"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <!-- 日志内容 -->
      <div
        ref="logContainer"
        class="sidebar-content log-content"
      >
        <div
          v-for="(log, index) in logs"
          :key="index"
          class="log-item"
          :class="getLogClass(log.type)"
        >
          <span class="log-time">{{ formatTime(log.time) }}</span>
          <span class="log-content-text">{{ log.content }}</span>
        </div>

        <div v-if="logs.length === 0" class="empty-log">
          <div class="empty-log-icon">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <p class="text-text-secondary text-sm">暂无日志</p>
        </div>
      </div>
    </div>
  </Transition>

  <!-- 遮罩层 -->
  <Transition name="fade">
    <div
      v-if="isOpen"
      class="sidebar-overlay"
      @click="$emit('close')"
    ></div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

interface LogMessage {
  time: number
  type: string
  content: string
}

interface Props {
  isOpen: boolean
  logs: LogMessage[]
  autoScroll?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  autoScroll: true
})

defineEmits<{
  close: []
  clear: []
}>()

const logContainer = ref<HTMLElement | null>(null)

// 监听日志变化，自动滚动到底部
watch(
  () => props.logs.length,
  async () => {
    if (props.autoScroll) {
      await nextTick()
      scrollToBottom()
    }
  }
)

// 滚动到底部
function scrollToBottom() {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}

// 格式化时间
function formatTime(timestamp: number): string {
  const date = new Date(timestamp)
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${hours}:${minutes}:${seconds}`
}

// 获取日志样式类
function getLogClass(type: string): string {
  switch (type) {
    case 'error':
    case 'node_error':
      return 'log-error'
    case 'warning':
      return 'log-warning'
    case 'success':
    case 'node_complete':
      return 'log-success'
    case 'info':
      return 'log-info'
    case 'node_start':
      return 'log-running'
    default:
      return 'log-default'
  }
}
</script>

<style scoped>
/* ========== 侧边栏容器 ========== */
.sidebar-panel {
  position: fixed;
  top: 6rem;
  height: calc(100vh - 10rem);
  width: 24rem;
  z-index: 40;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
  isolation: isolate;
  /* 深邃渐变背景 */
  background:
    radial-gradient(ellipse 80% 60% at 50% 0%, rgba(99, 102, 241, 0.12), transparent 70%),
    linear-gradient(180deg, #131a2b 0%, #0d1322 100%);
}

.sidebar-right {
  right: 0;
  border-radius: 16px 0 0 16px;
}

/* 装饰网格 */
.sidebar-grid {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  background-size: 18px 18px;
  pointer-events: none;
  mask-image: radial-gradient(ellipse 90% 90% at 50% 30%, #000 40%, transparent 100%);
  z-index: 0;
}

/* 顶部柔光 */
.sidebar-glow {
  position: absolute;
  top: -80px;
  left: 50%;
  transform: translateX(-50%);
  width: 70%;
  height: 180px;
  background: radial-gradient(ellipse at center, rgba(139, 92, 246, 0.2), transparent 70%);
  pointer-events: none;
  filter: blur(8px);
  z-index: 0;
}

/* ========== 头部 ========== */
.sidebar-header {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  background: linear-gradient(180deg, rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.6));
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.clear-btn {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  color: #94a3b8;
  background: rgba(51, 65, 85, 0.35);
  border: 1px solid rgba(148, 163, 184, 0.14);
  transition: all 0.2s ease;
}
.clear-btn:hover {
  color: #fff;
  background: rgba(71, 85, 105, 0.55);
  border-color: rgba(148, 163, 184, 0.3);
}

.sidebar-close-btn {
  padding: 6px;
  border-radius: 8px;
  color: #cbd5e1;
  transition: all 0.2s ease;
}
.sidebar-close-btn:hover {
  background: rgba(71, 85, 105, 0.5);
  color: #fff;
}

/* ========== 日志内容区 ========== */
.sidebar-content {
  position: relative;
  z-index: 1;
  flex: 1;
  overflow-y: auto;
  padding: 18px;
}

.log-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 自定义滚动条 */
.sidebar-content::-webkit-scrollbar { width: 6px; }
.sidebar-content::-webkit-scrollbar-track { background: rgba(15, 23, 42, 0.3); }
.sidebar-content::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.3);
  border-radius: 3px;
}
.sidebar-content::-webkit-scrollbar-thumb:hover { background: rgba(148, 163, 184, 0.5); }

/* ========== 日志项 ========== */
.log-item {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.45);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-left-width: 3px;
  transition: all 0.2s ease;
}

.log-item:hover {
  background: rgba(15, 23, 42, 0.7);
  border-color: rgba(148, 163, 184, 0.2);
}

.log-time {
  flex-shrink: 0;
  color: #64748b;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11px;
}

.log-content-text {
  flex: 1;
  font-size: 12px;
  line-height: 1.5;
  color: #cbd5e1;
}

/* 日志类型色 */
.log-error {
  border-left-color: #f87171;
  color: #fca5a5;
  background: rgba(248, 113, 113, 0.08);
}

.log-warning {
  border-left-color: #fbbf24;
  color: #fcd34d;
  background: rgba(251, 191, 36, 0.08);
}

.log-success {
  border-left-color: #34d399;
  color: #6ee7b7;
  background: rgba(52, 211, 153, 0.08);
}

.log-info {
  border-left-color: #38bdf8;
  color: #7dd3fc;
  background: rgba(56, 189, 248, 0.08);
}

.log-running {
  border-left-color: #a78bfa;
  color: #c4b5fd;
  background: rgba(167, 139, 250, 0.10);
}

.log-default {
  border-left-color: #64748b;
  color: #cbd5e1;
}

/* ========== 空状态 ========== */
.empty-log {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.empty-log-icon {
  width: 64px;
  height: 64px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.18), rgba(139, 92, 246, 0.04));
  color: #a78bfa;
  border: 1px solid rgba(167, 139, 250, 0.2);
}

/* ========== 遮罩层 ========== */
.sidebar-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
  z-index: 30;
}

/* ========== 动画 ========== */
.sidebar-right-enter-active,
.sidebar-right-leave-active {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-right-enter-from,
.sidebar-right-leave-to {
  transform: translateX(100%);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
