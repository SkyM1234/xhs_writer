<template>
  <div class="node-card" :class="statusClass">
    <!-- 状态指示器 -->
    <div class="absolute left-0 top-0 bottom-0 w-1 rounded-l-xl" :class="statusBarClass"></div>
    
    <div class="pl-3">
      <!-- 节点头部 -->
      <div class="flex items-center justify-between mb-2">
        <div class="flex items-center gap-2">
          <div class="w-2 h-2 rounded-full" :class="statusDotClass"></div>
          <h3 class="font-semibold text-text-primary">{{ node.name }}</h3>
        </div>
        <span class="text-xs text-text-muted">{{ node.id }}</span>
      </div>
      
      <!-- 节点描述 -->
      <p class="text-sm text-text-secondary mb-3">{{ description }}</p>
      
      <!-- 进度条 -->
      <div v-if="node.status === 'running'" class="mb-3">
        <div class="flex items-center justify-between mb-1">
          <span class="text-xs text-text-muted">执行中</span>
          <span class="text-xs text-text-primary font-medium">{{ node.progress }}%</span>
        </div>
        <div class="h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
          <div 
            class="h-full bg-primary transition-all duration-300"
            :style="{ width: `${node.progress}%` }"
          ></div>
        </div>
      </div>
      
      <!-- 消息 -->
      <div v-if="node.message" class="text-xs text-text-secondary mb-2">
        {{ node.message }}
      </div>
      
      <!-- 错误信息 -->
      <div v-if="node.error" class="text-xs text-error bg-error/10 rounded px-2 py-1 mb-2">
        {{ node.error }}
      </div>
      
      <!-- 执行时间 -->
      <div v-if="node.startTime" class="text-xs text-text-muted">
        <span v-if="node.endTime">
          耗时: {{ formatDuration(node.endTime - node.startTime) }}
        </span>
        <span v-else>
          开始时间: {{ formatTime(node.startTime) }}
        </span>
      </div>
      
      <!-- 展开/收起按钮 -->
      <button 
        v-if="hasDetails"
        @click="expanded = !expanded"
        class="mt-2 text-xs text-primary hover:text-primary-hover transition-colors"
      >
        {{ expanded ? '收起详情' : '查看详情' }}
      </button>
      
      <!-- 详情面板 -->
      <div v-if="expanded && hasDetails" class="mt-3 pt-3 border-t border-border-primary">
        <!-- 输入数据 -->
        <div v-if="node.input" class="mb-2">
          <div class="text-xs text-text-muted mb-1">输入:</div>
          <pre class="text-xs bg-bg-tertiary rounded p-2 overflow-x-auto scrollbar-thin">{{ JSON.stringify(node.input, null, 2) }}</pre>
        </div>
        
        <!-- 输出数据 -->
        <div v-if="node.output">
          <div class="text-xs text-text-muted mb-1">输出:</div>
          <pre class="text-xs bg-bg-tertiary rounded p-2 overflow-x-auto scrollbar-thin">{{ JSON.stringify(node.output, null, 2) }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { NodeStatus } from '@/types'

interface Props {
  node: {
    id: string
    name: string
    status: NodeStatus
    progress: number
    message?: string
    input?: any
    output?: any
    error?: string
    startTime?: number
    endTime?: number
  }
  description?: string
}

const props = defineProps<Props>()

const expanded = ref(false)

// 是否有详情数据
const hasDetails = computed(() => {
  return props.node.input || props.node.output
})

// 状态样式类
const statusClass = computed(() => {
  switch (props.node.status) {
    case 'running':
      return 'ring-2 ring-node-running/30'
    case 'completed':
      return 'ring-1 ring-node-completed/20'
    case 'error':
      return 'ring-2 ring-node-error/30'
    default:
      return ''
  }
})

// 状态条样式
const statusBarClass = computed(() => {
  switch (props.node.status) {
    case 'pending':
      return 'bg-node-pending'
    case 'running':
      return 'bg-node-running'
    case 'completed':
      return 'bg-node-completed'
    case 'error':
      return 'bg-node-error'
    default:
      return 'bg-node-pending'
  }
})

// 状态点样式
const statusDotClass = computed(() => {
  switch (props.node.status) {
    case 'pending':
      return 'bg-node-pending'
    case 'running':
      return 'bg-node-running animate-pulse'
    case 'completed':
      return 'bg-node-completed'
    case 'error':
      return 'bg-node-error animate-pulse'
    default:
      return 'bg-node-pending'
  }
})

// 格式化时间
function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString('zh-CN')
}

// 格式化时长
function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 600000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 600000)}m ${Math.floor((ms % 600000) / 1000)}s`
}
</script>
