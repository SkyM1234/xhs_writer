<template>
  <div class="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-blue-50 p-6">
    <div class="max-w-4xl mx-auto">
      <!-- 顶部操作栏 -->
      <div class="mb-6 flex items-center justify-between">
        <button
          @click="goBack"
          class="flex items-center gap-2 text-gray-600 hover:text-gray-800 transition"
        >
          <span>←</span>
          <span>返回列表</span>
        </button>

        <button
          @click="confirmDelete"
          class="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
          <span>删除笔记</span>
        </button>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="flex justify-center items-center py-20">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>

      <!-- 错误提示 -->
      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        {{ error }}
      </div>

      <!-- 笔记内容 -->
      <div v-else-if="note" class="bg-white rounded-xl shadow-lg overflow-hidden">
        <!-- 图片展示 -->
        <div v-if="note.image_urls.length > 0" class="relative">
          <img
            :src="currentImageUrl"
            :alt="note.title"
            class="w-full h-96 object-cover"
            @error="handleImageError"
          />
          
          <!-- 图片导航 -->
          <div v-if="note.image_urls.length > 1" class="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex gap-2">
            <button
              v-for="(_, index) in note.image_urls"
              :key="index"
              @click="currentImageIndex = index"
              :class="[
                'w-2 h-2 rounded-full transition',
                currentImageIndex === index ? 'bg-white' : 'bg-white/50'
              ]"
            ></button>
          </div>
        </div>

        <!-- 笔记信息 -->
        <div class="p-8">
          <!-- 标题 -->
          <h1 class="text-3xl font-bold text-gray-800 mb-4">{{ note.title }}</h1>

          <!-- 关键词和评分 -->
          <div class="flex items-center gap-4 mb-6">
            <div class="flex flex-wrap gap-2">
              <span
                v-for="keyword in note.keywords"
                :key="keyword"
                class="px-3 py-1 bg-purple-100 text-purple-700 text-sm rounded-full"
              >
                {{ keyword }}
              </span>
            </div>
            <div class="flex items-center gap-2 text-yellow-600">
              <span>⭐</span>
              <span class="font-semibold">{{ note.quality_score }}</span>
            </div>
          </div>

          <!-- 正文 -->
          <div class="prose prose-lg max-w-none mb-6">
            <div class="whitespace-pre-wrap text-gray-700 leading-relaxed">{{ note.content }}</div>
          </div>

          <!-- 标签 -->
          <div v-if="note.tags.length > 0" class="mb-6">
            <h3 class="text-sm font-semibold text-gray-600 mb-2">标签</h3>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="tag in note.tags"
                :key="tag"
                class="px-3 py-1 bg-blue-50 text-blue-700 text-sm rounded-lg"
              >
                #{{ tag }}
              </span>
            </div>
          </div>

          <!-- 图片提示词 -->
          <div v-if="note.image_prompts.length > 0" class="border-t pt-6">
            <h3 class="text-sm font-semibold text-gray-600 mb-2">图片提示词</h3>
            <p class="text-sm text-gray-600 italic">{{ note.image_prompts[0] }}</p>
          </div>

          <!-- 元信息 -->
          <div class="border-t pt-6 mt-6 text-sm text-gray-500">
            <div class="flex items-center gap-4">
              <span>迭代次数: {{ note.iteration_count }}</span>
              <span>文件夹: {{ note.folder_name }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 删除确认对话框 -->
    <div
      v-if="showDeleteDialog"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="showDeleteDialog = false"
    >
      <div class="bg-white rounded-xl shadow-2xl p-6 max-w-md w-full mx-4">
        <h3 class="text-xl font-bold text-gray-800 mb-4">确认删除</h3>
        <p class="text-gray-600 mb-6">
          确定要删除笔记 <span class="font-semibold text-gray-800">"{{ note?.title }}"</span> 吗？此操作无法撤销。
        </p>
        <div class="flex gap-3 justify-end">
          <button
            @click="showDeleteDialog = false"
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
          >
            取消
          </button>
          <button
            @click="handleDelete"
            :disabled="deleting"
            class="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ deleting ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getNoteDetail, deleteNote } from '@/api/content'

const router = useRouter()
const route = useRoute()
const loading = ref(true)
const error = ref('')
const currentImageIndex = ref(0)
const note = ref<{
  folder_name: string
  title: string
  content: string
  tags: string[]
  keywords: string[]
  quality_score: number
  iteration_count: number
  image_prompts: string[]
  image_urls: string[]
  online_image_urls: string[]
} | null>(null)

// 删除相关状态
const showDeleteDialog = ref(false)
const deleting = ref(false)

// 当前显示的图片 URL
const currentImageUrl = computed(() => {
  if (!note.value || note.value.image_urls.length === 0) return ''
  return `http://localhost:8000${note.value.image_urls[currentImageIndex.value]}`
})

// 加载笔记详情
const loadNote = async () => {
  try {
    loading.value = true
    error.value = ''
    const folderName = route.params.folderName as string
    note.value = await getNoteDetail(folderName)
  } catch (err: any) {
    error.value = err.message || '加载笔记详情失败'
  } finally {
    loading.value = false
  }
}

// 返回列表
const goBack = () => {
  router.push('/notes')
}

// 确认删除
const confirmDelete = () => {
  showDeleteDialog.value = true
}

// 执行删除
const handleDelete = async () => {
  if (!note.value) return

  try {
    deleting.value = true
    await deleteNote(note.value.folder_name)

    // 删除成功后返回列表
    router.push('/notes')
  } catch (err: any) {
    alert(err.message || '删除笔记失败')
    showDeleteDialog.value = false
  } finally {
    deleting.value = false
  }
}

// 图片加载失败处理
const handleImageError = (event: Event) => {
  console.error('图片加载失败:', currentImageUrl.value)
  // 可以设置一个默认图片
}

onMounted(() => {
  loadNote()
})
</script>

