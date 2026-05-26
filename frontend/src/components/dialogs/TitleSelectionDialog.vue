<template>
  <Teleport to="body">
    <Transition name="dialog">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
        @click.self="handleClose"
      >
        <div class="card max-w-2xl w-full max-h-[80vh] overflow-y-auto scrollbar-thin">
          <!-- 标题 -->
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-2xl font-bold">选择标题</h2>
            <button
              @click="handleClose"
              class="text-text-muted hover:text-text-primary transition-colors"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <!-- 说明 -->
          <p class="text-text-secondary mb-6">
            标题实验室已生成 {{ titles.length }} 个不同风格的标题，请选择一个继续生成内容。
          </p>
          
          <!-- 标题列表 -->
          <div class="space-y-4">
            <div
              v-for="(title, index) in titles"
              :key="index"
              class="relative p-4 rounded-lg border-2 transition-all cursor-pointer"
              :class="selectedIndex === index 
                ? 'border-primary bg-primary/10' 
                : 'border-border-primary hover:border-primary/50 hover:bg-bg-tertiary'"
              @click="selectedIndex = index"
            >
              <!-- 选中标记 -->
              <div
                v-if="selectedIndex === index"
                class="absolute top-3 right-3 w-6 h-6 rounded-full bg-primary flex items-center justify-center"
              >
                <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              
              <!-- 标题编号 -->
              <div class="flex items-start gap-3">
                <div class="shrink-0 w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-semibold">
                  {{ index + 1 }}
                </div>
                
                <!-- 标题内容 -->
                <div class="flex-1 pt-1">
                  <p class="text-lg font-medium text-text-primary leading-relaxed">
                    {{ title }}
                  </p>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 操作按钮 -->
          <div class="flex gap-3 mt-6 pt-6 border-t border-border-primary">
            <button
              @click="handleClose"
              class="btn btn-secondary flex-1"
            >
              取消
            </button>
            <button
              @click="handleConfirm"
              :disabled="selectedIndex === null"
              class="btn btn-primary flex-1"
            >
              确认选择
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

interface Props {
  modelValue: boolean
  titles: string[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: [title: string, index: number]
  cancel: []
}>()

const selectedIndex = ref<number | null>(null)

// 监听对话框打开，重置选择
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    selectedIndex.value = null
  }
})

// 关闭对话框（发送暂缓请求）
function handleClose() {
  emit('cancel')
  emit('update:modelValue', false)
}

// 确认选择
function handleConfirm() {
  if (selectedIndex.value !== null) {
    emit('confirm', props.titles[selectedIndex.value], selectedIndex.value)
    emit('update:modelValue', false)
  }
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
