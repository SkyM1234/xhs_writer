<template>
  <div class="min-h-screen p-6">
    <div class="max-w-7xl mx-auto">
      <!-- 页面标题和控制按钮 -->
      <div class="mb-8 flex items-center justify-between">
        <div>
          <h1 class="text-3xl font-bold mb-2">小红书内容生成工作流</h1>
          <p class="text-text-secondary">基于 LangGraph 的智能内容生成系统</p>
        </div>

        <!-- 侧边栏切换按钮 -->
        <div class="flex gap-3">
          <button
            @click="showConfigSidebar = true"
            class="workflow-btn workflow-btn-primary"
            :class="{ 'animate-pulse-subtle': !isRunning && workflowStore.formData.keywords.length === 0 }"
            title="打开配置参数"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span class="font-semibold">配置参数</span>
          </button>
          <button
            @click="showLogSidebar = true"
            class="workflow-btn workflow-btn-secondary"
            title="打开执行日志"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span class="font-semibold">执行日志</span>
            <span v-if="workflowStore.messages.length > 0" class="log-badge">
              {{ workflowStore.messages.length }}
            </span>
          </button>
        </div>
      </div>

      <!-- 进度条 -->
      <div v-if="workflowStore.taskStatus === 'running'" class="card mb-6">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm text-text-secondary">总体进度</span>
          <span class="text-sm font-medium text-primary">{{ workflowStore.overallProgress }}%</span>
        </div>
        <div class="h-2 bg-bg-tertiary rounded-full overflow-hidden">
          <div
            class="h-full bg-gradient-to-r from-primary to-primary-light transition-all duration-300"
            :style="{ width: `${workflowStore.overallProgress}%` }"
          ></div>
        </div>
        <div v-if="workflowStore.currentNode" class="mt-2 text-xs text-text-muted">
          当前节点: {{ workflowStore.currentNode.name }}
        </div>
      </div>

      <!-- 工作流可视化区（全宽） -->
      <div class="w-full">
        <WorkflowGraph :nodes="workflowStore.nodeList" />
      </div>
    </div>

    <!-- 配置参数侧边栏 -->
    <ConfigSidebar
      :is-open="showConfigSidebar"
      :form-data="workflowStore.formData"
      :keyword-input="keywordInput"
      :topic-word-input="topicWordInput"
      :is-running="isRunning"
      @close="showConfigSidebar = false"
      @submit="handleStart"
      @stop="handleStop"
      @add-keyword="addKeyword"
      @remove-keyword="removeKeyword"
      @add-topic-word="addTopicWord"
      @remove-topic-word="removeTopicWord"
      @update:keyword-input="keywordInput = $event"
      @update:topic-word-input="topicWordInput = $event"
      @update:account-persona="workflowStore.formData.account_persona = $event"
      @update:target-count="workflowStore.formData.target_count = $event"
      @update:days="workflowStore.formData.days = $event"
      @update:min-comments="workflowStore.formData.min_comments = $event"
      @update:min-likes="workflowStore.formData.min_likes = $event"
      @update:min-favorites="workflowStore.formData.min_favorites = $event"
    />

    <!-- 执行日志侧边栏 -->
    <LogSidebar
      :is-open="showLogSidebar"
      :logs="workflowStore.messages"
      @close="showLogSidebar = false"
      @clear="workflowStore.messages = []"
    />

    <!-- 标题选择对话框 -->
    <TitleSelectionDialog
      v-model="showTitleDialog"
      :titles="workflowStore.titleCandidates"
      @confirm="handleTitleConfirm"
      @cancel="handleTitleCancel"
    />

    <!-- 人工审核对话框 -->
    <HumanReviewDialog
      v-model="showReviewDialog"
      :content="reviewContent"
      :editor-score="workflowStore.editorFeedback?.score || 0"
      :editor-feedback="workflowStore.editorFeedback?.feedback"
      @confirm="handleReviewConfirm"
      @cancel="handleReviewCancel"
    />

    <!-- 结果展示对话框 -->
    <ResultDialog
      v-if="workflowStore.finalPost"
      v-model="showResultDialog"
      :result="workflowStore.finalPost"
      @export="handleExport"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useWorkflowStore } from '@/stores/workflow'
import { wsService } from '@/api/websocket'
import { generateTitles, continueGeneration, submitHumanReview } from '@/api/content'
import WorkflowGraph from '@/components/workflow/WorkflowGraph.vue'
import ConfigSidebar from '@/components/workflow/ConfigSidebar.vue'
import LogSidebar from '@/components/workflow/LogSidebar.vue'
import TitleSelectionDialog from '@/components/dialogs/TitleSelectionDialog.vue'
import HumanReviewDialog from '@/components/dialogs/HumanReviewDialog.vue'
import ResultDialog from '@/components/dialogs/ResultDialog.vue'
import type { NodeProgressMessage } from '@/types'

const route = useRoute()
const workflowStore = useWorkflowStore()

// 侧边栏状态
const showConfigSidebar = ref(false)
const showLogSidebar = ref(false)

// 对话框状态
const showTitleDialog = ref(false)
const showReviewDialog = ref(false)
const showResultDialog = ref(false)

// 审核内容
const reviewContent = ref({
  title: '',
  body: '',
  tags: [] as string[]
})

// 表单状态
const keywordInput = ref('')
const topicWordInput = ref('')
const isRunning = computed(() => workflowStore.taskStatus === 'running')

/**
 * 添加关键词
 */
function addKeyword() {
  const keyword = keywordInput.value.trim()
  if (keyword && !workflowStore.formData.keywords.includes(keyword)) {
    workflowStore.formData.keywords.push(keyword)
    keywordInput.value = ''
  }
}

/**
 * 移除关键词
 */
function removeKeyword(index: number) {
  workflowStore.formData.keywords.splice(index, 1)
}

/**
 * 添加话题词
 */
function addTopicWord() {
  const topicWord = topicWordInput.value.trim()
  if (topicWord && !workflowStore.formData.topic_words.includes(topicWord)) {
    workflowStore.formData.topic_words.push(topicWord)
    topicWordInput.value = ''
  }
}

/**
 * 移除话题词
 */
function removeTopicWord(index: number) {
  workflowStore.formData.topic_words.splice(index, 1)
}

/**
 * 处理 WebSocket 进度消息
 */
function handleProgress(message: NodeProgressMessage) {
  console.log('[WorkflowView] 收到进度消息:', message)

  // 处理节点重置消息
  if (message.type === 'nodes_reset' && message.node_ids) {
    console.log('[WorkflowView] 重置节点:', message.node_ids)
    workflowStore.resetNodes(message.node_ids)
    workflowStore.addMessage('info', message.message || '工作流回退，重置后续节点')
    return
  }

  // 更新节点状态
  if (message.node_id) {
    workflowStore.updateNodeStatus(
      message.node_id,
      message.status || 'running',
      message.progress,
      message.message,
      message.output,
      message.error
    )
  }

  // 添加日志
  let logType = 'info'
  let logContent = message.message || ''

  switch (message.type) {
    case 'node_start':
      logType = 'node_start'
      logContent = `开始执行: ${message.node_name}`
      break
    case 'node_complete':
      logType = 'node_complete'
      logContent = `完成: ${message.node_name}`

      // 检查是否需要弹出对话框
      if (message.node_id === 'title_lab') {
        // 标题生成完成，检查输出中的标题数据（兼容 title_candidates 和 titles）
        const titles = message.output?.title_candidates || message.output?.titles
        if (titles && Array.isArray(titles) && titles.length > 0) {
          workflowStore.setTitleCandidates(titles)
          showTitleDialog.value = true
          workflowStore.addMessage('info', '请选择一个标题继续...')
        }
      } else if (message.node_id === 'chief_editor') {
        // 检查是否需要人工审核（兼容多种字段）
        const needReview = message.output?.need_human_review ||
                          message.output?.status === 'pending_human_review' ||
                          (message.output?.score >= 80 && message.output?.score < 90)

        if (needReview) {
          // 获取文案内容（从 copywriter 节点的输出中获取）
          const copywriterNode = workflowStore.nodes.get('copywriter')
          console.log('[DEBUG] copywriter 节点:', JSON.stringify(copywriterNode, null, 2))
          console.log('[DEBUG] copywriter 输出:', JSON.stringify(copywriterNode?.output, null, 2))

          const draftContent = copywriterNode?.output?.draft_content ||
                              copywriterNode?.output?.content ||
                              message.output?.content ||
                              message.output?.draft_content ||
                              ''

          // 需要人工审核
          reviewContent.value = {
            title: message.output.title || workflowStore.selectedTitle || '',
            body: draftContent,
            tags: message.output.tags || []
          }

          // 设置编辑反馈
          if (message.output.score !== undefined) {
            workflowStore.setEditorFeedback({
              score: message.output.score,
              feedback: message.output.feedback || message.output.editor_feedback || '需人工确认'
            })
          }

          showReviewDialog.value = true
          workflowStore.addMessage('info', '请进行人工审核...')
        }
      } else if (message.node_id === 'human_review') {
        // human_review 节点完成，检查是否需要打开审核对话框
        // 这种情况通常发生在从待处理任务恢复时
        if (message.output?.status === 'waiting_human_review') {
          console.log('[WorkflowView] human_review 节点返回等待状态，打开审核对话框')

          // 获取文案内容
          const copywriterNode = workflowStore.nodes.get('copywriter')
          const draftContent = copywriterNode?.output?.draft_content ||
                              copywriterNode?.output?.content ||
                              ''

          reviewContent.value = {
            title: workflowStore.selectedTitle || '',
            body: draftContent,
            tags: []
          }

          // 设置编辑反馈
          if (message.output.score !== undefined) {
            workflowStore.setEditorFeedback({
              score: message.output.score,
              feedback: message.output.feedback || '需人工确认'
            })
          }

          showReviewDialog.value = true
          workflowStore.addMessage('info', '请进行人工审核...')
        }
      } else if (message.node_id === 'finalize') {
        // 最终输出完成，显示结果
        if (message.output) {
          const finalPost = {
            title: message.output.title || '',
            content: message.output.content || '',
            tags: message.output.tags || [],
            images: message.output.images || message.output.local_images || []
          }

          workflowStore.setFinalPost(finalPost)
          showResultDialog.value = true
          workflowStore.addMessage('success', '🎉 内容生成完成！')

          if (message.output.saved_path) {
            workflowStore.addMessage('success', `📁 笔记已保存到: ${message.output.saved_path}`)
          }

          // 任务完成，更新状态
          workflowStore.setTaskStatus('completed')
        }
      }
      break
    case 'node_error':
      logType = 'node_error'
      logContent = `错误: ${message.node_name} - ${message.error}`
      break
    case 'node_progress':
      logType = 'info'
      logContent = `${message.node_name}: ${message.message}`
      break
    case 'message':
      logType = 'info'
      break
  }

  if (logContent) {
    workflowStore.addMessage(logType, logContent)
  }
}

/**
 * 开始生成
 */
async function handleStart() {
  try {
    // 重置工作流
    workflowStore.resetWorkflow()
    workflowStore.setTaskStatus('running')

    // 生成任务ID
    const taskId = crypto.randomUUID()
    workflowStore.setTaskId(taskId)

    workflowStore.addMessage('info', `任务ID: ${taskId}`)
    workflowStore.addMessage('info', '正在连接 WebSocket...')

    // 先连接 WebSocket
    wsService.connect(taskId, handleProgress)

    // 等待连接建立（增加等待时间到 2 秒，并轮询检测）
    let connected = false
    for (let i = 0; i < 20; i++) {
      await new Promise(resolve => setTimeout(resolve, 100))
      if (wsService.isConnected()) {
        connected = true
        break
      }
    }

    if (!connected) {
      // 即使连接状态未确认，也继续执行（因为连接可能在后台建立）
      workflowStore.addMessage('warning', 'WebSocket 连接状态未确认，继续执行...')
    } else {
      workflowStore.addMessage('success', 'WebSocket 连接成功')
    }

    workflowStore.addMessage('info', '开始生成内容...')

    // 调用 API
    const response = await generateTitles(workflowStore.formData, taskId)

    console.log('[WorkflowView] API 响应:', response)

    // 处理响应
    if (response.title_candidates) {
      workflowStore.setTitleCandidates(response.title_candidates)
    }

    if (response.final_post) {
      const post = response.final_post
      workflowStore.setFinalPost({
        title: post.title || '',
        content: post.content || '',
        tags: post.tags || [],
        images: post.image_urls || []
      })
      showResultDialog.value = true
      workflowStore.addMessage('success', '内容生成完成！')
    }

    workflowStore.setTaskStatus('completed')

  } catch (error: any) {
    console.error('[WorkflowView] 生成失败:', error)
    workflowStore.setTaskStatus('error')
    workflowStore.addMessage('error', `生成失败: ${error.message || error}`)
  }
}

/**
 * 停止生成
 */
function handleStop() {
  wsService.disconnect()
  workflowStore.setTaskStatus('idle')
  workflowStore.addMessage('warning', '已停止生成')
}

/**
 * 标题选择确认
 */
async function handleTitleConfirm(title: string, index: number) {
  try {
    workflowStore.selectTitle(title)
    workflowStore.addMessage('success', `已选择标题 ${index + 1}: ${title}`)
    workflowStore.addMessage('info', '继续生成内容...')

    // 恢复任务运行状态
    workflowStore.setTaskStatus('running')

    // 调用继续生成 API
    const response = await continueGeneration({
      task_id: workflowStore.taskId!,
      selected_title: title,
      action: 'select'
    })

    console.log('[WorkflowView] 继续生成响应:', response)

  } catch (error: any) {
    console.error('[WorkflowView] 继续生成失败:', error)
    workflowStore.addMessage('error', `继续生成失败: ${error.message || error}`)
    workflowStore.setTaskStatus('error')
  }
}

/**
 * 标题选择取消（暂缓）
 */
async function handleTitleCancel() {
  try {
    workflowStore.addMessage('info', '标题选择已暂缓')

    // 调用暂缓 API
    const response = await continueGeneration({
      task_id: workflowStore.taskId!,
      action: 'postpone'
    })

    console.log('[WorkflowView] 暂缓标题选择响应:', response)

    // 更新任务状态为暂缓
    workflowStore.setTaskStatus('idle')

  } catch (error: any) {
    console.error('[WorkflowView] 暂缓标题选择失败:', error)
    workflowStore.addMessage('error', `暂缓失败: ${error.message || error}`)
  }
}

/**
 * 人工审核确认
 */
async function handleReviewConfirm(decision: 'approve' | 'reject', feedback: string) {
  try {
    workflowStore.addMessage('info', `审核决定: ${decision === 'approve' ? '通过' : '拒绝'}`)
    if (feedback) {
      workflowStore.addMessage('info', `反馈意见: ${feedback}`)
    }

    // 恢复任务运行状态
    workflowStore.setTaskStatus('running')

    // 调用人工审核 API
    const response = await submitHumanReview({
      task_id: workflowStore.taskId!,
      decision,
      feedback
    })

    console.log('[WorkflowView] 人工审核响应:', response)

    // 如果通过，继续执行
    if (decision === 'approve') {
      workflowStore.addMessage('success', '审核通过，继续生成...')
    } else {
      workflowStore.addMessage('warning', '审核拒绝，重新生成...')
    }

    // 检查是否有最终结果
    if (response.final_post) {
      const post = response.final_post
      workflowStore.setFinalPost({
        title: post.title || '',
        content: post.content || '',
        tags: post.tags || [],
        images: post.image_urls || []
      })
      showResultDialog.value = true
      workflowStore.addMessage('success', '内容生成完成！')
      // 任务完成，更新状态
      workflowStore.setTaskStatus('completed')
    }

  } catch (error: any) {
    console.error('[WorkflowView] 人工审核失败:', error)
    workflowStore.addMessage('error', `人工审核失败: ${error.message || error}`)
    workflowStore.setTaskStatus('error')
  }
}

/**
 * 人工审核取消（暂缓）
 */
async function handleReviewCancel() {
  try {
    workflowStore.addMessage('info', '人工审核已暂缓')

    // 调用暂缓 API
    const response = await submitHumanReview({
      task_id: workflowStore.taskId!,
      decision: 'postpone',
      feedback: '用户暂缓审核'
    })

    console.log('[WorkflowView] 暂缓审核响应:', response)

    // 更新任务状态为暂缓
    workflowStore.setTaskStatus('idle')

  } catch (error: any) {
    console.error('[WorkflowView] 暂缓审核失败:', error)
    workflowStore.addMessage('error', `暂缓失败: ${error.message || error}`)
  }
}

/**
 * 导出内容
 */
function handleExport() {
  workflowStore.addMessage('success', '内容已导出')
}

/**
 * 从待处理任务恢复
 */
async function resumeFromPendingTask() {
  const resume = route.query.resume as string
  const taskId = route.query.task_id as string
  const taskType = route.query.task_type as string

  if (resume !== 'true' || !taskId || !taskType) {
    return
  }

  console.log('[WorkflowView] 从待处理任务恢复:', { taskId, taskType })

  try {
    // 设置任务状态
    workflowStore.setTaskId(taskId)
    workflowStore.setTaskStatus('running')
    workflowStore.addMessage('info', `恢复任务: ${taskId}`)

    // 连接 WebSocket
    workflowStore.addMessage('info', '正在连接 WebSocket...')
    wsService.connect(taskId, handleProgress)

    // 等待连接建立
    let connected = false
    for (let i = 0; i < 20; i++) {
      await new Promise(resolve => setTimeout(resolve, 100))
      if (wsService.isConnected()) {
        connected = true
        break
      }
    }

    if (connected) {
      workflowStore.addMessage('success', 'WebSocket 连接成功')
    } else {
      workflowStore.addMessage('warning', 'WebSocket 连接状态未确认，继续执行...')
    }

    workflowStore.addMessage('success', '任务已恢复，继续执行...')

    // 根据任务类型调用相应的 API
    let response
    if (taskType === 'title_selection') {
      const selectedTitle = route.query.selected_title as string
      workflowStore.addMessage('info', `继续生成，已选择标题: ${selectedTitle}`)

      response = await continueGeneration({
        task_id: taskId,
        selected_title: selectedTitle,
        action: 'select'
      })
    } else if (taskType === 'human_review') {
      const decision = route.query.decision as 'approve' | 'reject'
      const feedback = route.query.feedback as string || ''
      workflowStore.addMessage('info', `继续审核，决策: ${decision}`)

      response = await submitHumanReview({
        task_id: taskId,
        decision,
        feedback
      })
    }

    // 检查响应状态，如果需要人工介入则打开对应对话框
    if (response) {
      console.log('[WorkflowView] API 响应:', response)

      // 如果需要人工审核
      if (response.status === 'waiting_human_review') {
        workflowStore.addMessage('info', '需要人工审核...')

        // 设置审核内容
        reviewContent.value = {
          title: response.draft_content?.split('\n')[0] || '',
          body: response.draft_content || '',
          tags: []
        }

        // 设置编辑反馈
        if (response.editor_feedback) {
          workflowStore.setEditorFeedback({
            score: response.editor_feedback.score || 0,
            feedback: response.editor_feedback.feedback || ''
          })
        }

        // 打开审核对话框
        showReviewDialog.value = true
      }
      // 如果需要选择标题
      else if (response.status === 'waiting_title_selection') {
        workflowStore.addMessage('info', '需要选择标题...')

        if (response.title_candidates) {
          workflowStore.setTitleCandidates(response.title_candidates)
          showTitleDialog.value = true
        }
      }
      // 如果已完成
      else if (response.final_post) {
        const post = response.final_post
        workflowStore.setFinalPost({
          title: post.title || '',
          content: post.content || '',
          tags: post.tags || [],
          images: post.image_urls || []
        })
        showResultDialog.value = true
        workflowStore.addMessage('success', '🎉 内容生成完成！')
        // 任务完成，更新状态
        workflowStore.setTaskStatus('completed')
      }
    }

  } catch (error: any) {
    console.error('[WorkflowView] 恢复任务失败:', error)
    workflowStore.setTaskStatus('error')
    workflowStore.addMessage('error', `恢复任务失败: ${error.message || error}`)
  }
}

// 组件挂载时检查是否需要恢复任务
onMounted(() => {
  resumeFromPendingTask()
})

// 组件卸载时断开 WebSocket
onUnmounted(() => {
  wsService.disconnect()
})
</script>

<style scoped>
/* ========== 工作流按钮（玻璃质感） ========== */
.workflow-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: 12px;
  font-size: 14px;
  border: 1px solid;
  transition: all 0.25s ease;
  cursor: pointer;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
}

.workflow-btn-primary {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.85), rgba(139, 92, 246, 0.85));
  color: #fff;
  border-color: rgba(167, 139, 250, 0.5);
  box-shadow:
    0 4px 16px rgba(139, 92, 246, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
}

.workflow-btn-primary:hover {
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.95), rgba(124, 58, 237, 0.95));
  border-color: rgba(167, 139, 250, 0.7);
  box-shadow:
    0 6px 24px rgba(139, 92, 246, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  transform: translateY(-2px);
}

.workflow-btn-secondary {
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.7));
  color: #cbd5e1;
  border-color: rgba(148, 163, 184, 0.25);
  box-shadow:
    0 4px 16px rgba(0, 0, 0, 0.25),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.workflow-btn-secondary:hover {
  background: linear-gradient(135deg, rgba(51, 65, 85, 0.85), rgba(30, 41, 59, 0.85));
  color: #fff;
  border-color: rgba(148, 163, 184, 0.4);
  box-shadow:
    0 6px 24px rgba(0, 0, 0, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.12);
  transform: translateY(-2px);
}

/* 日志数量徽章 */
.log-badge {
  padding: 2px 8px;
  border-radius: 999px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.4);
}

/* 柔和的脉冲动画 - 用于提示用户配置参数 */
@keyframes pulse-subtle {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.9;
    transform: scale(1.02);
  }
}

.animate-pulse-subtle {
  animation: pulse-subtle 2s ease-in-out infinite;
}
</style>
