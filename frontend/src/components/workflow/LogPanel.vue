<template>
  <div class="log-panel card h-full flex flex-col">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold">执行日志</h3>
      <button 
        @click="clearLogs"
        class="text-xs text-text-muted hover:text-text-primary transition-colors"
      >
        清空
      </button>
    </div>
    
    <div 
      ref="logContainer"
      class="flex-1 overflow-y-auto scrollbar-thin space-y-2"
    >
      <div
        v-for="(log, index) in logs"
        :key="index"
        class="log-item text-xs p-2 rounded"
        :class="getLogClass(log.type)"
      >
        <div class="flex items-start gap-2">
          <span class="text-text-muted shrink-0">{{ formatTime(log.time) }}</span>
          <span class="flex-1">{{ log.content }}</span>
        </div>
      </div>
      
      <div v-if="logs.length === 0" class="text-center text-text-muted py-8">
        暂无日志
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

interface LogMessage {
  time: number
  type: string
  content: string
}

interface Props {
  logs: LogMessage[]
  autoScroll?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  autoScroll: true
})

const emit = defineEmits<{
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

// 清空日志
function clearLogs() {
  emit('clear')
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
      return 'bg-error/10 text-error border-l-2 border-error'
    case 'warning':
      return 'bg-warning/10 text-warning border-l-2 border-warning'
    case 'success':
      return 'bg-success/10 text-success border-l-2 border-success'
    case 'info':
      return 'bg-info/10 text-info border-l-2 border-info'
    case 'node_start':
      return 'bg-primary/10 text-primary border-l-2 border-primary'
    case 'node_complete':
      return 'bg-success/10 text-success border-l-2 border-success'
    case 'node_error':
      return 'bg-error/10 text-error border-l-2 border-error'
    default:
      return 'bg-bg-tertiary text-text-secondary'
  }
}
</script>

<style scoped>
.log-item {
  @apply transition-all duration-200;
}

.log-item:hover {
  @apply bg-opacity-20;
}
</style>
