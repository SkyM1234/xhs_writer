<template>
  <div class="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-blue-50 p-6">
    <div class="max-w-7xl mx-auto">
      <!-- 页面标题 -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-800 mb-2">📝 我的笔记</h1>
        <p class="text-gray-600">查看所有生成的小红书笔记</p>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="flex justify-center items-center py-20">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>

      <!-- 错误提示 -->
      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        {{ error }}
      </div>

      <!-- 空状态 -->
      <div v-else-if="notes.length === 0" class="text-center py-20">
        <div class="text-6xl mb-4">📭</div>
        <p class="text-gray-600 text-lg">还没有生成任何笔记</p>
        <router-link
          to="/"
          class="mt-4 inline-block px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
        >
          开始创作
        </router-link>
      </div>

      <!-- 笔记列表 -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="note in notes"
          :key="note.folder_name"
          class="bg-white rounded-xl shadow-md hover:shadow-xl transition-all overflow-hidden group relative"
        >
          <!-- 删除按钮 -->
          <button
            @click.stop="confirmDelete(note)"
            class="absolute top-3 right-3 z-10 w-8 h-8 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center hover:bg-red-600"
            title="删除笔记"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>

          <!-- 笔记卡片内容 -->
          <div @click="viewNote(note.folder_name)" class="cursor-pointer">
            <!-- 程序化封面：基于标题哈希生成独特配色和图案 -->
            <div
              class="cover"
              :style="getCoverStyle(note)"
            >
              <!-- 抽象几何装饰：3 个浮动圆 -->
              <span class="cover-shape shape-1"></span>
              <span class="cover-shape shape-2"></span>
              <span class="cover-shape shape-3"></span>

              <!-- 顶部品牌微标 -->
              <div class="cover-brand">
                <span class="cover-brand-dot"></span>
                <span>XHS NOTE</span>
              </div>

              <!-- 大号标题摘要 -->
              <div class="cover-headline">
                {{ getHeadline(note.title) }}
              </div>
            </div>

            <!-- 笔记信息 -->
            <div class="p-5">
              <h3 class="text-lg font-semibold text-gray-800 mb-2 line-clamp-2 group-hover:text-purple-600 transition">
                {{ note.title || '无标题' }}
              </h3>

              <!-- 关键词标签 -->
              <div class="flex flex-wrap gap-2 mb-3">
                <span
                  v-for="keyword in note.keywords.slice(0, 3)"
                  :key="keyword"
                  class="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-full"
                >
                  {{ keyword }}
                </span>
              </div>

              <!-- 底部信息 -->
              <div class="flex items-center justify-between text-sm text-gray-500">
                <div class="flex items-center gap-4">
                  <span>⭐ {{ note.quality_score }}</span>
                  <span v-if="note.has_images">🖼️ {{ note.image_count }}</span>
                </div>
              </div>
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
          确定要删除笔记 <span class="font-semibold text-gray-800">"{{ noteToDelete?.title }}"</span> 吗？此操作无法撤销。
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listNotes, deleteNote } from '@/api/content'

const router = useRouter()
const loading = ref(true)
const error = ref('')
const notes = ref<Array<{
  folder_name: string
  title: string
  keywords: string[]
  quality_score: number
  image_count: number
  has_images: boolean
}>>([])

// 删除相关状态
const showDeleteDialog = ref(false)
const deleting = ref(false)
const noteToDelete = ref<{
  folder_name: string
  title: string
} | null>(null)

// 加载笔记列表
const loadNotes = async () => {
  try {
    loading.value = true
    error.value = ''
    const response = await listNotes()
    notes.value = response.notes
  } catch (err: any) {
    error.value = err.message || '加载笔记列表失败'
  } finally {
    loading.value = false
  }
}

// 查看笔记详情
const viewNote = (folderName: string) => {
  router.push(`/notes/${folderName}`)
}

// ========== 程序化封面：基于标题哈希生成独特配色 ==========
// 12 套精心搭配的小红书风渐变色（柔和、年轻、不撞色）
const COVER_PALETTES: Array<[string, string, string]> = [
  ['#FF9A9E', '#FAD0C4', '#FFC1CC'], // 樱花粉
  ['#A18CD1', '#FBC2EB', '#E0C3FC'], // 紫梦境
  ['#FAD0C4', '#FFD1FF', '#FFE5EC'], // 蜜桃奶
  ['#FBC2EB', '#A6C1EE', '#C5D4F8'], // 蓝粉糖
  ['#FFECD2', '#FCB69F', '#FFD3A5'], // 焦糖橘
  ['#84FAB0', '#8FD3F4', '#A8E6CF'], // 薄荷青
  ['#FCCB90', '#D57EEB', '#F2A0E0'], // 葡萄紫
  ['#FF6E7F', '#BFE9FF', '#FFB6C1'], // 海岸珊瑚
  ['#43E97B', '#38F9D7', '#7AE7C7'], // 抹茶绿
  ['#FA709A', '#FEE140', '#FFB088'], // 落日金
  ['#5EE7DF', '#B490CA', '#A0D8F1'], // 极光紫
  ['#FFA8A8', '#FCFF00', '#FFE066'], // 柠檬粉
]

// 简易稳定哈希：把字符串映射到 0..N
function hashStr(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h) + s.charCodeAt(i)
    h |= 0
  }
  return Math.abs(h)
}

function getCoverStyle(note: { title: string; folder_name: string }): Record<string, string> {
  const seed = note.title || note.folder_name || 'note'
  const idx = hashStr(seed) % COVER_PALETTES.length
  const [c1, c2, c3] = COVER_PALETTES[idx]
  // 角度也跟着哈希变化，避免方向单一
  const angle = 100 + (hashStr(seed + 'angle') % 80) // 100~180deg
  return {
    background: `linear-gradient(${angle}deg, ${c1} 0%, ${c2} 50%, ${c3} 100%)`,
    '--cover-c1': c1,
    '--cover-c2': c2,
    '--cover-c3': c3,
  }
}

// 提取标题摘要（去掉 emoji，截断到合适长度）
function getHeadline(title: string): string {
  if (!title) return '无标题'
  // 去掉常见 emoji 和符号，保留中文/英文/数字
  const cleaned = title
    .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, '')
    .replace(/[|｜!！?？.。,，:：]/g, ' ')
    .trim()
  // 取前 14 个字
  return cleaned.length > 14 ? cleaned.slice(0, 14) + '…' : cleaned
}

// 确认删除
const confirmDelete = (note: any) => {
  noteToDelete.value = {
    folder_name: note.folder_name,
    title: note.title
  }
  showDeleteDialog.value = true
}

// 执行删除
const handleDelete = async () => {
  if (!noteToDelete.value) return

  try {
    deleting.value = true
    await deleteNote(noteToDelete.value.folder_name)

    // 从列表中移除已删除的笔记
    notes.value = notes.value.filter(
      note => note.folder_name !== noteToDelete.value?.folder_name
    )

    // 关闭对话框
    showDeleteDialog.value = false
    noteToDelete.value = null
  } catch (err: any) {
    alert(err.message || '删除笔记失败')
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadNotes()
})
</script>


<style scoped>
/* ========== 程序化封面 ========== */
.cover {
  position: relative;
  height: 200px;
  overflow: hidden;
  isolation: isolate;
  /* 渐变由内联 style 注入 */
}

/* 顶部柔光叠加：让渐变更有层次 */
.cover::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 60% 80% at 20% 0%, rgba(255, 255, 255, 0.45), transparent 60%),
    radial-gradient(ellipse 50% 60% at 100% 100%, rgba(0, 0, 0, 0.18), transparent 60%);
  pointer-events: none;
  z-index: 1;
}

/* 抽象几何装饰（半透明圆，blur 后形成色斑） */
.cover-shape {
  position: absolute;
  border-radius: 50%;
  filter: blur(28px);
  opacity: 0.55;
  pointer-events: none;
  z-index: 0;
}
.shape-1 {
  width: 140px; height: 140px;
  top: -40px; right: -30px;
  background: rgba(255, 255, 255, 0.7);
}
.shape-2 {
  width: 110px; height: 110px;
  bottom: -30px; left: -20px;
  background: rgba(255, 255, 255, 0.45);
}
.shape-3 {
  width: 80px; height: 80px;
  top: 50%; left: 60%;
  background: rgba(255, 255, 255, 0.35);
  transform: translateY(-50%);
}

/* 顶部品牌微标 */
.cover-brand {
  position: absolute;
  top: 14px;
  left: 16px;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.32);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: rgba(50, 30, 60, 0.85);
}
.cover-brand-dot {
  width: 5px; height: 5px;
  border-radius: 50%;
  background: #ff2442;
  box-shadow: 0 0 6px rgba(255, 36, 66, 0.8);
}

/* 大号标题摘要 */
.cover-headline {
  position: absolute;
  left: 18px;
  right: 18px;
  top: 55%;
  transform: translateY(-50%);
  z-index: 2;
  font-size: 22px;
  font-weight: 800;
  line-height: 1.3;
  color: rgba(45, 25, 60, 0.92);
  letter-spacing: 0.5px;
  text-shadow: 0 2px 8px rgba(255, 255, 255, 0.5);
  /* 限制 3 行 */
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* hover 微动效 */
.group:hover .cover-shape {
  transform: scale(1.15);
  transition: transform 0.6s ease;
}
.shape-3 { transition: transform 0.6s ease; }
.group:hover .shape-3 {
  transform: translateY(-50%) scale(1.2);
}
.cover-shape { transition: transform 0.6s ease; }
</style>
