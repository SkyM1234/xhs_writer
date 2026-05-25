<template>
  <div class="result-panel card">
    <!-- 标题 -->
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-2xl font-bold">生成结果</h2>
      <button
        @click="handleExport"
        class="btn btn-primary"
      >
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        导出内容
      </button>
    </div>
    
    <!-- 内容区域 -->
    <div class="space-y-6">
      <!-- 标题 -->
      <div>
        <div class="flex items-center justify-between mb-2">
          <label class="text-sm font-medium text-text-secondary">标题</label>
          <button
            @click="copyToClipboard(result.title)"
            class="text-xs text-primary hover:text-primary-hover transition-colors"
          >
            复制
          </button>
        </div>
        <div class="p-4 rounded-lg bg-bg-tertiary border border-border-primary">
          <p class="text-lg font-semibold text-text-primary">{{ result.title }}</p>
        </div>
      </div>
      
      <!-- 正文 -->
      <div>
        <div class="flex items-center justify-between mb-2">
          <label class="text-sm font-medium text-text-secondary">正文内容</label>
          <button
            @click="copyToClipboard(result.content)"
            class="text-xs text-primary hover:text-primary-hover transition-colors"
          >
            复制
          </button>
        </div>
        <div class="p-4 rounded-lg bg-bg-tertiary border border-border-primary">
          <p class="text-text-primary whitespace-pre-wrap leading-relaxed">{{ result.content }}</p>
        </div>
      </div>
      
      <!-- 标签 -->
      <div v-if="result.tags && result.tags.length > 0">
        <div class="flex items-center justify-between mb-2">
          <label class="text-sm font-medium text-text-secondary">标签</label>
          <button
            @click="copyToClipboard(result.tags.map(t => '#' + t).join(' '))"
            class="text-xs text-primary hover:text-primary-hover transition-colors"
          >
            复制
          </button>
        </div>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="tag in result.tags"
            :key="tag"
            class="px-3 py-1.5 rounded-full bg-primary/20 text-primary text-sm font-medium"
          >
            #{{ tag }}
          </span>
        </div>
      </div>
      
      <!-- 图片 -->
      <div v-if="result.images && result.images.length > 0">
        <label class="block text-sm font-medium text-text-secondary mb-2">配图</label>
        <div class="grid grid-cols-3 gap-4">
          <div
            v-for="(image, index) in result.images"
            :key="index"
            class="relative aspect-square rounded-lg overflow-hidden bg-bg-tertiary border border-border-primary group cursor-pointer"
            @click="handleImageClick(image)"
          >
            <img
              :src="image"
              :alt="`配图 ${index + 1}`"
              class="w-full h-full object-cover"
              @error="handleImageError"
            />
            <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
              <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 完整内容复制 -->
      <div class="pt-4 border-t border-border-primary">
        <button
          @click="copyFullContent"
          class="btn btn-secondary w-full"
        >
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          复制完整内容
        </button>
      </div>
    </div>
    
    <!-- 复制成功提示 -->
    <Transition name="toast">
      <div
        v-if="showToast"
        class="fixed bottom-8 left-1/2 -translate-x-1/2 px-6 py-3 rounded-lg bg-success text-white shadow-xl"
      >
        ✓ 复制成功
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  result: {
    title: string
    content: string
    tags: string[]
    images: string[]
  }
}

const props = defineProps<Props>()

const emit = defineEmits<{
  export: []
  imageClick: [url: string]
}>()

const showToast = ref(false)

// 复制到剪贴板
async function copyToClipboard(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    showToast.value = true
    setTimeout(() => {
      showToast.value = false
    }, 2000)
  } catch (error) {
    console.error('复制失败:', error)
    alert('复制失败，请手动复制')
  }
}

// 复制完整内容
function copyFullContent() {
  const fullContent = `${props.result.title}\n\n${props.result.content}\n\n${props.result.tags.map(t => '#' + t).join(' ')}`
  copyToClipboard(fullContent)
}

// 导出内容
function handleExport() {
  emit('export')
  
  // 创建下载
  const content = `标题：\n${props.result.title}\n\n正文：\n${props.result.content}\n\n标签：\n${props.result.tags.map(t => '#' + t).join(' ')}`
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `小红书内容_${new Date().getTime()}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

// 图片点击
function handleImageClick(url: string) {
  emit('imageClick', url)
  // 在新窗口打开图片
  window.open(url, '_blank')
}

// 图片加载失败
function handleImageError(event: Event) {
  const img = event.target as HTMLImageElement
  img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"%3E%3Crect fill="%23334155" width="200" height="200"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%2364748B" font-size="14"%3E图片加载失败%3C/text%3E%3C/svg%3E'
}
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 200ms ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translate(-50%, 1rem);
}
</style>
