<template>
  <div class="pending-page">
    <!-- 装饰背景 -->
    <div class="page-grid"></div>
    <div class="page-glow"></div>

    <div class="relative z-10 max-w-7xl mx-auto p-6">
      <!-- 页面标题 -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold mb-2 text-text-primary">待处理任务</h1>
        <p class="text-text-secondary">管理所有暂缓的标题选择和人工审核任务</p>
      </div>

      <!-- 筛选器 -->
      <div class="filter-bar mb-6">
        <div class="flex items-center gap-4 flex-wrap">
          <label class="text-sm font-medium text-text-secondary">任务类型</label>
          <div class="flex gap-2">
            <button
              @click="filterType = null"
              class="filter-chip"
              :class="{ active: filterType === null }"
            >
              全部 <span class="chip-count">{{ tasks.length }}</span>
            </button>
            <button
              @click="filterType = 'title_selection'"
              class="filter-chip chip-collect"
              :class="{ active: filterType === 'title_selection' }"
            >
              <i class="chip-dot"></i>标题选择 <span class="chip-count">{{ titleSelectionCount }}</span>
            </button>
            <button
              @click="filterType = 'human_review'"
              class="filter-chip chip-plan"
              :class="{ active: filterType === 'human_review' }"
            >
              <i class="chip-dot"></i>人工审核 <span class="chip-count">{{ humanReviewCount }}</span>
            </button>
          </div>
          <button
            @click="loadTasks"
            class="ml-auto refresh-btn flex items-center gap-2"
            :disabled="loading"
          >
            <svg class="w-4 h-4" :class="{ 'animate-spin': loading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            刷新
          </button>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="empty-card text-center py-16">
        <div class="inline-block w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4"></div>
        <p class="text-text-secondary">加载中...</p>
      </div>

      <!-- 空状态 -->
      <div v-else-if="filteredTasks.length === 0" class="empty-card text-center py-16">
        <div class="empty-icon-wrap">
          <svg class="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <p class="text-text-primary text-lg mb-1 font-medium">暂无待处理任务</p>
        <p class="text-text-muted text-sm">所有任务都已完成</p>
      </div>

      <!-- 任务列表 -->
      <div v-else class="space-y-4">
        <div
          v-for="task in filteredTasks"
          :key="task.task_id"
          class="task-card"
          :class="task.task_type === 'title_selection' ? 'cat-collect' : 'cat-plan'"
        >
          <!-- 左侧分组色条 -->
          <span class="task-bar"></span>
          <!-- 顶部高光线 -->
          <span class="task-highlight"></span>

          <div class="flex items-start gap-4 relative z-10">
            <!-- 任务类型图标 -->
            <div class="task-icon">
              <svg v-if="task.task_type === 'title_selection'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
              </svg>
              <svg v-else class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>

            <!-- 任务信息 -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-3 mb-2 flex-wrap">
                <h3 class="text-lg font-semibold text-text-primary">
                  {{ task.task_type === 'title_selection' ? '标题选择' : '人工审核' }}
                </h3>
                <span class="task-badge">
                  {{ task.status === 'waiting_title_selection' ? '等待选择标题' : '等待审核' }}
                </span>
              </div>

              <!-- 任务ID -->
              <div class="mb-3 text-xs text-text-muted font-mono">
                ID: {{ task.task_id.substring(0, 8) }}...
              </div>

              <!-- 关键词 -->
              <div class="flex flex-wrap gap-2 mb-3 items-center">
                <span class="text-xs text-text-secondary font-medium">关键词</span>
                <span
                  v-for="keyword in task.keywords"
                  :key="keyword"
                  class="kw-tag"
                >
                  {{ keyword }}
                </span>
              </div>

              <!-- 标题选择任务：显示标题候选 -->
              <div v-if="task.task_type === 'title_selection' && task.title_candidates && task.title_candidates.length > 0" class="mb-3">
                <div class="text-xs text-text-secondary font-medium mb-2">标题候选 ({{ task.title_candidates.length }}个)</div>
                <div class="space-y-1.5">
                  <div
                    v-for="(title, index) in task.title_candidates.slice(0, 3)"
                    :key="index"
                    class="title-row"
                  >
                    <span class="title-idx">{{ index + 1 }}</span>
                    <span class="text-sm text-text-primary">{{ title }}</span>
                  </div>
                  <div v-if="task.title_candidates.length > 3" class="text-xs text-text-muted italic pl-1">
                    还有 {{ task.title_candidates.length - 3 }} 个标题...
                  </div>
                </div>
              </div>

              <!-- 人工审核任务：评分 -->
              <div v-if="task.task_type === 'human_review' && task.editor_feedback && task.editor_feedback.score" class="mb-3">
                <div class="flex items-center gap-2">
                  <span class="text-xs text-text-secondary font-medium">编辑评分</span>
                  <span
                    class="score-badge"
                    :class="task.editor_feedback.score >= 90 ? 'score-high' : task.editor_feedback.score >= 80 ? 'score-mid' : 'score-low'"
                  >
                    {{ task.editor_feedback.score }} 分
                  </span>
                </div>
              </div>

              <!-- 时间信息 -->
              <div class="flex items-center gap-4 text-xs text-text-muted">
                <span>创建 · {{ formatTime(task.created_at) }}</span>
                <span>更新 · {{ formatTime(task.updated_at) }}</span>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="shrink-0 flex flex-col gap-2">
              <button
                @click="handleContinue(task)"
                class="action-btn action-primary flex items-center gap-2"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                继续处理
              </button>
              <button
                @click="handleDelete(task)"
                class="action-btn action-danger flex items-center gap-2"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                删除
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 标题选择对话框 -->
    <TitleSelectionDialog
      v-model="showTitleDialog"
      :titles="currentTitleCandidates"
      @confirm="handleTitleConfirm"
      @cancel="handleTitleCancel"
    />

    <!-- 人工审核对话框 -->
    <HumanReviewDialog
      v-model="showReviewDialog"
      :content="reviewContent"
      :editor-score="currentEditorScore"
      :editor-feedback="currentEditorFeedback"
      @confirm="handleReviewConfirm"
      @cancel="handleReviewCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listPendingTasks, deletePendingTask, restorePendingTask, continueGeneration, submitHumanReview } from '@/api/content'
import TitleSelectionDialog from '@/components/dialogs/TitleSelectionDialog.vue'
import HumanReviewDialog from '@/components/dialogs/HumanReviewDialog.vue'

const router = useRouter()

// 状态
const loading = ref(false)
const tasks = ref<any[]>([])
const filterType = ref<string | null>(null)

// 对话框状态
const showTitleDialog = ref(false)
const showReviewDialog = ref(false)
const currentTaskId = ref<string>('')
const currentTitleCandidates = ref<string[]>([])
const currentEditorScore = ref(0)
const currentEditorFeedback = ref('')
const reviewContent = ref({
  title: '',
  body: '',
  tags: [] as string[]
})

// 计算属性
const filteredTasks = computed(() => {
  if (!filterType.value) return tasks.value
  return tasks.value.filter(task => task.task_type === filterType.value)
})

const titleSelectionCount = computed(() => {
  return tasks.value.filter(task => task.task_type === 'title_selection').length
})

const humanReviewCount = computed(() => {
  return tasks.value.filter(task => task.task_type === 'human_review').length
})

// 加载任务列表
async function loadTasks() {
  loading.value = true
  try {
    tasks.value = await listPendingTasks()
  } catch (error: any) {
    console.error('加载待处理任务失败:', error)
    alert(`加载失败: ${error.message || error}`)
  } finally {
    loading.value = false
  }
}

// 格式化时间
function formatTime(timestamp: number): string {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  // 小于1分钟
  if (diff < 60000) {
    return '刚刚'
  }

  // 小于1小时
  if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}分钟前`
  }

  // 小于1天
  if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`
  }

  // 格式化为日期时间
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 继续处理任务
async function handleContinue(task: any) {
  currentTaskId.value = task.task_id

  try {
    // 从 checkpoint 恢复状态
    const restoredState = await restorePendingTask(task.task_id)

    if (task.task_type === 'title_selection') {
      // 标题选择任务
      currentTitleCandidates.value = restoredState.title_candidates || []
      showTitleDialog.value = true
    } else {
      // 人工审核任务
      reviewContent.value = {
        title: restoredState.selected_title || '',
        body: restoredState.draft_content || '',
        tags: []
      }
      currentEditorScore.value = restoredState.editor_feedback?.score || 0
      currentEditorFeedback.value = restoredState.editor_feedback?.feedback || ''
      showReviewDialog.value = true
    }
  } catch (error: any) {
    console.error('恢复任务状态失败:', error)
    alert(`恢复失败: ${error.message || error}`)
  }
}

// 删除任务
async function handleDelete(task: any) {
  if (!confirm(`确定要删除这个任务吗？\n任务ID: ${task.task_id}`)) {
    return
  }

  try {
    await deletePendingTask(task.task_id)
    // 重新加载列表
    await loadTasks()
  } catch (error: any) {
    console.error('删除任务失败:', error)
    alert(`删除失败: ${error.message || error}`)
  }
}

// 标题选择确认
async function handleTitleConfirm(title: string, index: number) {
  // 关闭对话框
  showTitleDialog.value = false

  // 跳转到工作流页面，并通过路由参数传递信息
  router.push({
    path: '/',
    query: {
      resume: 'true',
      task_id: currentTaskId.value,
      task_type: 'title_selection',
      selected_title: title
    }
  })
}

// 标题选择取消
function handleTitleCancel() {
  showTitleDialog.value = false
}

// 人工审核确认
async function handleReviewConfirm(decision: 'approve' | 'reject', feedback: string) {
  // 关闭对话框
  showReviewDialog.value = false

  // 跳转到工作流页面，并通过路由参数传递信息
  router.push({
    path: '/',
    query: {
      resume: 'true',
      task_id: currentTaskId.value,
      task_type: 'human_review',
      decision: decision,
      feedback: feedback
    }
  })
}

// 人工审核取消
function handleReviewCancel() {
  showReviewDialog.value = false
}

// 组件挂载时加载任务列表
onMounted(() => {
  loadTasks()
})
</script>

<style scoped>
/* ========== 页面容器：与工作流页同款星空渐变 ========== */
.pending-page {
  position: relative;
  min-height: 100vh;
  background:
    radial-gradient(ellipse 80% 60% at 50% 0%, rgba(99, 102, 241, 0.10), transparent 70%),
    linear-gradient(180deg, #131a2b 0%, #0d1322 100%);
  overflow: hidden;
}

.page-grid {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  background-size: 18px 18px;
  pointer-events: none;
  mask-image: radial-gradient(ellipse 90% 90% at 50% 30%, #000 40%, transparent 100%);
}

.page-glow {
  position: absolute;
  top: -120px;
  left: 50%;
  transform: translateX(-50%);
  width: 60%;
  height: 240px;
  background: radial-gradient(ellipse at center, rgba(139, 92, 246, 0.18), transparent 70%);
  pointer-events: none;
  filter: blur(8px);
}

/* ========== 筛选栏（玻璃质感） ========== */
.filter-bar {
  background: linear-gradient(180deg, rgba(30, 41, 59, 0.55), rgba(15, 23, 42, 0.55));
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 14px;
  padding: 14px 18px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04), 0 4px 16px rgba(0, 0, 0, 0.25);
}

.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 500;
  color: #cbd5e1;
  background: rgba(51, 65, 85, 0.4);
  border: 1px solid rgba(148, 163, 184, 0.15);
  transition: all 0.2s ease;
  cursor: pointer;
}
.filter-chip:hover { background: rgba(71, 85, 105, 0.55); border-color: rgba(148, 163, 184, 0.3); }

.chip-count {
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: #94a3b8;
  font-weight: 600;
}

.chip-dot {
  width: 7px; height: 7px; border-radius: 50%; display: inline-block;
}
.chip-collect .chip-dot { background: #38bdf8; box-shadow: 0 0 6px rgba(56, 189, 248, 0.6); }
.chip-plan    .chip-dot { background: #a855f7; box-shadow: 0 0 6px rgba(168, 85, 247, 0.6); }

/* 激活态：分组色高亮 */
.filter-chip.active {
  color: #fff;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.35), rgba(139, 92, 246, 0.35));
  border-color: rgba(167, 139, 250, 0.5);
  box-shadow: 0 4px 14px rgba(139, 92, 246, 0.25);
}
.filter-chip.active .chip-count { background: rgba(255, 255, 255, 0.18); color: #fff; }

.chip-collect.active {
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.4), rgba(56, 189, 248, 0.3));
  border-color: rgba(56, 189, 248, 0.55);
  box-shadow: 0 4px 14px rgba(56, 189, 248, 0.25);
}
.chip-plan.active {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.4), rgba(168, 85, 247, 0.3));
  border-color: rgba(168, 85, 247, 0.55);
  box-shadow: 0 4px 14px rgba(168, 85, 247, 0.25);
}

/* 刷新按钮 */
.refresh-btn {
  padding: 7px 14px;
  border-radius: 10px;
  font-size: 13px;
  color: #cbd5e1;
  background: rgba(51, 65, 85, 0.4);
  border: 1px solid rgba(148, 163, 184, 0.15);
  transition: all 0.2s ease;
  cursor: pointer;
}
.refresh-btn:hover:not(:disabled) {
  background: rgba(71, 85, 105, 0.6);
  color: #fff;
  border-color: rgba(148, 163, 184, 0.3);
}
.refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }


/* ========== 任务卡片：分组色 + 渐变 + 玻璃质感 ========== */
.task-card {
  position: relative;
  padding: 20px 22px 20px 28px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  overflow: hidden;
  transition: all 0.25s ease;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
}

/* 分组渐变背景 */
.task-card.cat-collect {
  background: linear-gradient(135deg, #1e3a52 0%, #172a3a 60%, #131f2c 100%);
  border-color: rgba(56, 189, 248, 0.22);
}
.task-card.cat-plan {
  background: linear-gradient(135deg, #3a2a5c 0%, #251a3d 60%, #1d1430 100%);
  border-color: rgba(168, 85, 247, 0.22);
}

.task-card:hover {
  transform: translateY(-2px);
  border-color: rgba(255, 255, 255, 0.2);
}
.task-card.cat-collect:hover {
  border-color: rgba(56, 189, 248, 0.5);
  box-shadow: 0 8px 28px rgba(56, 189, 248, 0.18);
}
.task-card.cat-plan:hover {
  border-color: rgba(168, 85, 247, 0.5);
  box-shadow: 0 8px 28px rgba(168, 85, 247, 0.2);
}

/* 左侧色条 */
.task-bar {
  position: absolute;
  left: 0; top: 12px; bottom: 12px;
  width: 4px;
  border-radius: 0 4px 4px 0;
}
.cat-collect .task-bar { background: linear-gradient(180deg, #38bdf8, #0ea5e9); box-shadow: 0 0 8px rgba(56, 189, 248, 0.5); }
.cat-plan    .task-bar { background: linear-gradient(180deg, #a855f7, #7c3aed); box-shadow: 0 0 8px rgba(168, 85, 247, 0.5); }

/* 顶部高光线 */
.task-highlight {
  position: absolute;
  top: 0; left: 16px; right: 16px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.12), transparent);
}

/* 任务图标 */
.task-icon {
  flex-shrink: 0;
  width: 48px; height: 48px;
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.cat-collect .task-icon {
  background: rgba(56, 189, 248, 0.18);
  color: #7dd3fc;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}
.cat-plan .task-icon {
  background: rgba(168, 85, 247, 0.20);
  color: #c4b5fd;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

/* 状态徽章 */
.task-badge {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.cat-collect .task-badge {
  background: rgba(56, 189, 248, 0.15);
  color: #7dd3fc;
  border-color: rgba(56, 189, 248, 0.3);
}
.cat-plan .task-badge {
  background: rgba(168, 85, 247, 0.18);
  color: #c4b5fd;
  border-color: rgba(168, 85, 247, 0.3);
}

/* 关键词标签 */
.kw-tag {
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.18);
  color: #cbd5e1;
  font-size: 11px;
  transition: all 0.2s ease;
}
.kw-tag:hover {
  background: rgba(30, 41, 59, 0.7);
  border-color: rgba(148, 163, 184, 0.35);
}

/* 标题候选行 */
.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: rgba(15, 23, 42, 0.45);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 8px;
  transition: all 0.2s ease;
}
.title-row:hover { background: rgba(15, 23, 42, 0.7); border-color: rgba(148, 163, 184, 0.22); }

.title-idx {
  flex-shrink: 0;
  width: 20px; height: 20px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  background: rgba(56, 189, 248, 0.18);
  color: #7dd3fc;
}

/* 评分徽章 */
.score-badge {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid;
}
.score-high { background: rgba(45, 212, 191, 0.15); color: #5eead4; border-color: rgba(45, 212, 191, 0.4); }
.score-mid  { background: rgba(251, 191, 36, 0.15); color: #fcd34d; border-color: rgba(251, 191, 36, 0.4); }
.score-low  { background: rgba(248, 113, 113, 0.15); color: #fca5a5; border-color: rgba(248, 113, 113, 0.4); }


/* ========== 操作按钮 ========== */
.action-btn {
  padding: 8px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  border: 1px solid;
  transition: all 0.2s ease;
  cursor: pointer;
  white-space: nowrap;
}

.action-primary {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  border-color: rgba(167, 139, 250, 0.5);
  box-shadow: 0 4px 14px rgba(139, 92, 246, 0.3);
}
.action-primary:hover {
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  box-shadow: 0 6px 20px rgba(139, 92, 246, 0.45);
  transform: translateY(-1px);
}

.action-danger {
  background: rgba(248, 113, 113, 0.08);
  color: #fca5a5;
  border-color: rgba(248, 113, 113, 0.3);
}
.action-danger:hover {
  background: rgba(248, 113, 113, 0.18);
  color: #fee2e2;
  border-color: rgba(248, 113, 113, 0.5);
}

/* ========== 空状态 / 加载卡 ========== */
.empty-card {
  background: linear-gradient(180deg, rgba(30, 41, 59, 0.45), rgba(15, 23, 42, 0.45));
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 16px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.empty-icon-wrap {
  width: 72px; height: 72px;
  margin: 0 auto 16px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.18), rgba(139, 92, 246, 0.04));
  color: #a78bfa;
  border: 1px solid rgba(167, 139, 250, 0.2);
}

/* ========== 自旋动画 ========== */
.animate-spin { animation: spin 1s linear infinite; }
@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
</style>
