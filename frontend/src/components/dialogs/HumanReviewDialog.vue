<template>
  <Teleport to="body">
    <Transition name="dialog">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
        @click.self="handleClose"
      >
        <div class="card max-w-4xl w-full max-h-[85vh] overflow-y-auto scrollbar-thin">
          <!-- 标题 -->
          <div class="flex items-center justify-between mb-6">
            <div>
              <h2 class="text-2xl font-bold">人工审核</h2>
              <p class="text-sm text-text-secondary mt-1">
                编辑评分: <span :class="scoreClass">{{ editorScore }} 分</span>
              </p>
            </div>
            <button
              @click="handleClose"
              class="text-text-muted hover:text-text-primary transition-colors"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <!-- 编辑反馈 -->
          <div v-if="editorFeedback" class="mb-6 p-4 rounded-lg bg-warning/10 border border-warning/30">
            <div class="flex items-start gap-3">
              <svg class="w-5 h-5 text-warning shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div class="flex-1">
                <p class="font-medium text-warning mb-1">编辑建议</p>
                <p class="text-sm text-text-secondary">{{ editorFeedback }}</p>
              </div>
            </div>
          </div>
          
          <!-- 内容预览 -->
          <div class="space-y-6">
            <!-- 标题 -->
            <div>
              <label class="block text-sm font-medium mb-2 text-text-secondary">标题</label>
              <div class="p-4 rounded-lg bg-bg-tertiary">
                <p class="text-lg font-semibold text-text-primary">{{ content.title }}</p>
              </div>
            </div>
            
            <!-- 正文 -->
            <div>
              <label class="block text-sm font-medium mb-2 text-text-secondary">正文内容</label>
              <div class="p-4 rounded-lg bg-bg-tertiary">
                <p class="text-text-primary whitespace-pre-wrap leading-relaxed">{{ content.body }}</p>
              </div>
            </div>
            
            <!-- 标签 -->
            <div v-if="content.tags && content.tags.length > 0">
              <label class="block text-sm font-medium mb-2 text-text-secondary">标签</label>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="tag in content.tags"
                  :key="tag"
                  class="px-3 py-1 rounded-full bg-primary/20 text-primary text-sm"
                >
                  #{{ tag }}
                </span>
              </div>
            </div>
            
            <!-- 反馈输入 -->
            <div>
              <label class="block text-sm font-medium mb-2 text-text-secondary">
                审核意见（可选）
              </label>
              <textarea
                v-model="feedback"
                placeholder="如果拒绝，请说明原因或修改建议..."
                class="input min-h-[100px] resize-none"
              ></textarea>
            </div>
          </div>
          
          <!-- 操作按钮 -->
          <div class="flex gap-3 mt-6 pt-6 border-t border-border-primary">
            <button
              @click="handleReject"
              class="flex-1 px-6 py-3 rounded-lg font-medium transition-all duration-200 bg-error/20 hover:bg-error/30 text-error border border-error/30 flex items-center justify-center"
            >
              <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
              拒绝
            </button>
            <button
              @click="handleApprove"
              class="flex-1 px-6 py-3 rounded-lg font-medium transition-all duration-200 bg-primary hover:bg-primary-hover text-white flex items-center justify-center"
            >
              <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
              通过
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

interface Props {
  modelValue: boolean
  content: {
    title: string
    body: string
    tags?: string[]
  }
  editorScore: number
  editorFeedback?: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: [decision: 'approve' | 'reject', feedback: string]
  cancel: []
}>()

const feedback = ref('')

// 评分颜色
const scoreClass = computed(() => {
  if (props.editorScore >= 90) return 'text-success font-semibold'
  if (props.editorScore >= 80) return 'text-warning font-semibold'
  return 'text-error font-semibold'
})

// 监听对话框打开，重置反馈
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    feedback.value = ''
  }
})

// 关闭对话框（发送暂缓请求）
function handleClose() {
  emit('cancel')
  emit('update:modelValue', false)
}

// 通过
function handleApprove() {
  emit('confirm', 'approve', feedback.value)
  emit('update:modelValue', false)
}

// 拒绝
function handleReject() {
  emit('confirm', 'reject', feedback.value)
  emit('update:modelValue', false)
}
</script>

<style scoped>
.dialog-enter-active,
.dialog-leave-active {
  transition: opacity 200ms ease;
}

.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
}

.dialog-enter-active .card,
.dialog-leave-active .card {
  transition: transform 200ms ease, opacity 200ms ease;
}

.dialog-enter-from .card,
.dialog-leave-to .card {
  transform: scale(0.95);
  opacity: 0;
}
</style>
