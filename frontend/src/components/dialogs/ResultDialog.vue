<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
        @click.self="handleClose"
      >
        <div class="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
          <!-- 头部 -->
          <div class="flex items-center justify-between p-6 border-b border-gray-200">
            <h2 class="text-2xl font-bold text-gray-800">🎉 生成结果</h2>
            <div class="flex items-center gap-2">
              <button
                @click="handleExport"
                class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition flex items-center gap-2"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                导出
              </button>
              <button
                @click="handleClose"
                class="p-2 hover:bg-gray-100 rounded-lg transition"
              >
                <svg class="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          <!-- 内容区域 -->
          <div class="flex-1 overflow-y-auto p-6 space-y-6">
            <!-- 标题 -->
            <div>
              <div class="flex items-center justify-between mb-2">
                <label class="text-sm font-semibold text-gray-600">标题</label>
                <button
                  @click="copyToClipboard(result.title)"
                  class="text-xs text-purple-600 hover:text-purple-700 transition"
                >
                  复制
                </button>
              </div>
              <div class="p-4 rounded-lg bg-purple-50 border border-purple-200">
                <p class="text-lg font-semibold text-gray-800">{{ result.title }}</p>
              </div>
            </div>

            <!-- 正文 -->
            <div>
              <div class="flex items-center justify-between mb-2">
                <label class="text-sm font-semibold text-gray-600">正文内容</label>
                <button
                  @click="copyToClipboard(result.content)"
                  class="text-xs text-purple-600 hover:text-purple-700 transition"
                >
                  复制
                </button>
              </div>
              <div class="p-4 rounded-lg bg-gray-50 border border-gray-200">
                <p class="text-gray-800 whitespace-pre-wrap leading-relaxed">{{ result.content }}</p>
              </div>
            </div>

            <!-- 标签 -->
            <div v-if="result.tags && result.tags.length > 0">
              <div class="flex items-center justify-between mb-2">
                <label class="text-sm font-semibold text-gray-600">标签</label>
                <button
                  @click="copyToClipboard(result.tags.map(t => '#' + t).join(' '))"
                  class="text-xs text-purple-600 hover:text-purple-700 transition"
                >
                  复制
                </button>
              </div>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="tag in result.tags"
                  :key="tag"
                  class="px-3 py-1.5 rounded-full bg-blue-100 text-blue-700 text-sm font-medium"
                >
                  #{{ tag }}
                </span>
              </div>
            </div>

            <!-- 图片 -->
            <div v-if="result.images && result.images.length > 0">
              <label class="block text-sm font-semibold text-gray-600 mb-2">配图</label>
              <div class="grid grid-cols-3 gap-4">
                <div
                  v-for="(image, index) in result.images"
                  :key="index"
                  class="relative aspect-square rounded-lg overflow-hidden bg-gray-100 border border-gray-200 group cursor-pointer"
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
          </div>

          <!-- 底部操作 -->
          <div class="p-6 border-t border-gray-200 bg-gray-50">
            <button
              @click="copyFullContent"
              class="w-full px-6 py-3 bg-gray-800 text-white rounded-lg hover:bg-gray-900 transition flex items-center justify-center gap-2"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              复制完整内容
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 复制成功提示 -->
    <Transition name="toast">
      <div
        v-if="showToast"
        class="fixed bottom-8 left-1/2 -translate-x-1/2 px-6 py-3 rounded-lg bg-green-600 text-white shadow-xl z-[60]"
      >
        ✓ 复制成功
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  modelValue: boolean
  result: {
    title: string
    content: string
    tags: string[]
    images: string[]
  }
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  export: []
}>()

const showToast = ref(false)

// 关闭对话框
function handleClose() {
  emit('update:modelValue', false)
}

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
  window.open(url, '_blank')
}

// 图片加载失败
function handleImageError(event: Event) {
  const img = event.target as HTMLImageElement
  img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"%3E%3Crect fill="%23e5e7eb" width="200" height="200"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%239ca3af" font-size="14"%3E图片加载失败%3C/text%3E%3C/svg%3E'
}
</script>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 200ms ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .bg-white,
.modal-leave-active .bg-white {
  transition: transform 200ms ease;
}

.modal-enter-from .bg-white,
.modal-leave-to .bg-white {
  transform: scale(0.95);
}

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

