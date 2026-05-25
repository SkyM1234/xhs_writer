<template>
  <Transition name="sidebar-left">
    <div
      v-if="isOpen"
      class="sidebar-panel sidebar-left"
    >
      <!-- 装饰背景 -->
      <div class="sidebar-grid"></div>
      <div class="sidebar-glow"></div>

      <!-- 头部 -->
      <div class="sidebar-header">
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <svg class="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          配置参数
        </h2>
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

      <!-- 表单内容 -->
      <div class="sidebar-content">
        <form @submit.prevent="$emit('submit')" class="space-y-5">
          <!-- 关键词 -->
          <div class="form-group">
            <label class="form-label">关键词 <span class="text-error">*</span></label>
            <input
              :value="keywordInput"
              @input="$emit('update:keywordInput', ($event.target as HTMLInputElement).value)"
              type="text"
              placeholder="输入关键词，回车添加"
              class="form-input"
              @keydown.enter.prevent="$emit('addKeyword')"
            />
            <div class="flex flex-wrap gap-2 mt-2">
              <span
                v-for="(keyword, index) in formData.keywords"
                :key="index"
                class="keyword-tag"
              >
                {{ keyword }}
                <button
                  type="button"
                  @click="$emit('removeKeyword', index)"
                  class="keyword-remove"
                >
                  ×
                </button>
              </span>
            </div>
          </div>

          <!-- 话题词 -->
          <div class="form-group">
            <label class="form-label">话题词</label>
            <input
              :value="topicWordInput"
              @input="$emit('update:topicWordInput', ($event.target as HTMLInputElement).value)"
              type="text"
              placeholder="输入话题词，回车添加（可选）"
              class="form-input"
              @keydown.enter.prevent="$emit('addTopicWord')"
            />
            <div class="flex flex-wrap gap-2 mt-2">
              <span
                v-for="(topicWord, index) in formData.topic_words"
                :key="index"
                class="keyword-tag"
              >
                {{ topicWord }}
                <button
                  type="button"
                  @click="$emit('removeTopicWord', index)"
                  class="keyword-remove"
                >
                  ×
                </button>
              </span>
            </div>
            <p class="text-xs text-text-muted mt-1">话题词用于筛选笔记，标题或正文需包含其中之一</p>
          </div>

          <!-- 账号人设 -->
          <div class="form-group">
            <label class="form-label">账号人设</label>
            <textarea
              :value="formData.account_persona"
              @input="$emit('update:accountPersona', ($event.target as HTMLTextAreaElement).value)"
              placeholder="描述账号定位和风格"
              class="form-input min-h-[80px] resize-none"
            ></textarea>
          </div>

          <!-- 采集参数 -->
          <div class="form-group">
            <label class="form-label">采集参数</label>
            <div class="grid grid-cols-2 gap-3 mb-3">
              <div>
                <label class="form-sublabel">目标数量</label>
                <input
                  :value="formData.target_count"
                  @input="$emit('update:targetCount', parseInt(($event.target as HTMLInputElement).value))"
                  type="number"
                  class="form-input-sm"
                  min="5"
                  max="50"
                />
              </div>
              <div>
                <label class="form-sublabel">天数</label>
                <input
                  :value="formData.days"
                  @input="$emit('update:days', parseInt(($event.target as HTMLInputElement).value))"
                  type="number"
                  class="form-input-sm"
                  min="1"
                  max="90"
                />
              </div>
            </div>

            <!-- 筛选条件 -->
            <div class="filter-section">
              <label class="form-sublabel text-text-muted mb-2">筛选条件（最小值）</label>
              <div class="grid grid-cols-3 gap-2">
                <div>
                  <label class="form-sublabel-xs">评论数</label>
                  <input
                    :value="formData.min_comments"
                    @input="$emit('update:minComments', parseInt(($event.target as HTMLInputElement).value))"
                    type="number"
                    class="form-input-xs"
                    min="0"
                    placeholder="0"
                  />
                </div>
                <div>
                  <label class="form-sublabel-xs">点赞数</label>
                  <input
                    :value="formData.min_likes"
                    @input="$emit('update:minLikes', parseInt(($event.target as HTMLInputElement).value))"
                    type="number"
                    class="form-input-xs"
                    min="0"
                    placeholder="0"
                  />
                </div>
                <div>
                  <label class="form-sublabel-xs">收藏数</label>
                  <input
                    :value="formData.min_favorites"
                    @input="$emit('update:minFavorites', parseInt(($event.target as HTMLInputElement).value))"
                    type="number"
                    class="form-input-xs"
                    min="0"
                    placeholder="0"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="flex gap-2 pt-2">
            <button
              type="submit"
              :disabled="isRunning || formData.keywords.length === 0"
              class="form-btn-primary flex-1"
            >
              {{ isRunning ? '执行中...' : '开始生成' }}
            </button>
            <button
              v-if="isRunning"
              type="button"
              @click="$emit('stop')"
              class="form-btn-danger"
            >
              停止
            </button>
          </div>
        </form>
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
interface FormData {
  keywords: string[]
  topic_words: string[]
  account_persona: string
  target_count: number
  days: number
  min_comments: number
  min_likes: number
  min_favorites: number
}

interface Props {
  isOpen: boolean
  formData: FormData
  keywordInput: string
  topicWordInput: string
  isRunning: boolean
}

defineProps<Props>()

defineEmits<{
  close: []
  submit: []
  stop: []
  addKeyword: []
  removeKeyword: [index: number]
  addTopicWord: []
  removeTopicWord: [index: number]
  'update:keywordInput': [value: string]
  'update:topicWordInput': [value: string]
  'update:accountPersona': [value: string]
  'update:targetCount': [value: number]
  'update:days': [value: number]
  'update:minComments': [value: number]
  'update:minLikes': [value: number]
  'update:minFavorites': [value: number]
}>()
</script>

<style scoped>
/* ========== 侧边栏容器 ========== */
.sidebar-panel {
  position: fixed;
  top: 6rem;
  height: calc(100vh - 10rem);
  width: 22rem;
  z-index: 40;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 0 16px 16px 0;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
  isolation: isolate;
  /* 深邃渐变背景 */
  background:
    radial-gradient(ellipse 80% 60% at 50% 0%, rgba(99, 102, 241, 0.12), transparent 70%),
    linear-gradient(180deg, #131a2b 0%, #0d1322 100%);
}

.sidebar-left { left: 0; }

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

/* ========== 内容区 ========== */
.sidebar-content {
  position: relative;
  z-index: 1;
  flex: 1;
  overflow-y: auto;
  padding: 18px;
}

/* 自定义滚动条 */
.sidebar-content::-webkit-scrollbar { width: 6px; }
.sidebar-content::-webkit-scrollbar-track { background: rgba(15, 23, 42, 0.3); }
.sidebar-content::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.3);
  border-radius: 3px;
}
.sidebar-content::-webkit-scrollbar-thumb:hover { background: rgba(148, 163, 184, 0.5); }

/* ========== 表单组件 ========== */
.form-group { margin-bottom: 20px; }

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #f1f5f9;
  margin-bottom: 8px;
  letter-spacing: 0.3px;
}

.form-sublabel {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: #cbd5e1;
  margin-bottom: 6px;
}

.form-sublabel-xs {
  display: block;
  font-size: 10px;
  font-weight: 500;
  color: #94a3b8;
  margin-bottom: 4px;
}

/* 输入框 */
.form-input,
.form-input-sm,
.form-input-xs {
  width: 100%;
  padding: 9px 12px;
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 8px;
  color: #f1f5f9;
  font-size: 13px;
  transition: all 0.2s ease;
}
.form-input-sm { padding: 7px 10px; font-size: 12px; }
.form-input-xs { padding: 5px 8px; font-size: 11px; }

.form-input:focus,
.form-input-sm:focus,
.form-input-xs:focus {
  outline: none;
  background: rgba(15, 23, 42, 0.7);
  border-color: rgba(139, 92, 246, 0.5);
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
}

.form-input::placeholder,
.form-input-sm::placeholder,
.form-input-xs::placeholder {
  color: #64748b;
}

/* 关键词标签 */
.keyword-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(139, 92, 246, 0.18);
  border: 1px solid rgba(139, 92, 246, 0.35);
  border-radius: 999px;
  color: #c4b5fd;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s ease;
}
.keyword-tag:hover {
  background: rgba(139, 92, 246, 0.25);
  border-color: rgba(139, 92, 246, 0.5);
}

.keyword-remove {
  font-size: 16px;
  line-height: 1;
  color: #a78bfa;
  transition: color 0.2s ease;
}
.keyword-remove:hover { color: #fff; }

/* 筛选条件分隔 */
.filter-section {
  padding-top: 12px;
  border-top: 1px solid rgba(148, 163, 184, 0.1);
}

/* 按钮 */
.form-btn-primary,
.form-btn-danger {
  padding: 9px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  border: 1px solid;
  transition: all 0.2s ease;
  cursor: pointer;
}

.form-btn-primary {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  border-color: rgba(167, 139, 250, 0.5);
  box-shadow: 0 4px 14px rgba(139, 92, 246, 0.3);
}
.form-btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  box-shadow: 0 6px 20px rgba(139, 92, 246, 0.45);
  transform: translateY(-1px);
}
.form-btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.form-btn-danger {
  background: rgba(248, 113, 113, 0.12);
  color: #fca5a5;
  border-color: rgba(248, 113, 113, 0.35);
}
.form-btn-danger:hover {
  background: rgba(248, 113, 113, 0.22);
  color: #fee2e2;
  border-color: rgba(248, 113, 113, 0.5);
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
.sidebar-left-enter-active,
.sidebar-left-leave-active {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-left-enter-from,
.sidebar-left-leave-to {
  transform: translateX(-100%);
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
