import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { NodeInfo, NodeStatus, ContentGenerationRequest } from '@/types'

/**
 * 工作流节点定义
 */
const WORKFLOW_NODES = [
  { id: 'trend_collector', name: '热点采集', description: '抓取小红书热榜数据' },
  { id: 'trend_analyzer', name: '热点分析', description: '分析热点特征和爆款模板' },
  { id: 'strategist', name: '选题策划', description: '确定内容策略和切入角度' },
  { id: 'title_lab', name: '标题生成', description: '生成3个候选标题' },
  { id: 'copywriter', name: '文案创作', description: '生成完整文案内容' },
  { id: 'compliance_checker', name: '合规检查', description: '检测违禁词和平台规则' },
  { id: 'chief_editor', name: '终审编辑', description: '质量评分和审核' },
  { id: 'human_review', name: '人工审核', description: '人工确认内容' },
  { id: 'visual_designer', name: '视觉设计', description: '生成配图' },
  { id: 'finalize', name: '最终输出', description: '输出完整内容' }
]

export const useWorkflowStore = defineStore('workflow', () => {
  // ========== 状态 ==========
  
  // 任务信息
  const taskId = ref<string | null>(null)
  const taskStatus = ref<string>('idle') // idle, running, completed, error
  
  // 节点状态
  const nodes = ref<Map<string, NodeInfo>>(new Map())
  
  // 消息日志
  const messages = ref<Array<{ time: number; type: string; content: string }>>([])
  
  // 表单数据
  const formData = ref<ContentGenerationRequest>({
    keywords: [],
    topic_words: [],
    account_persona: '专业分享者',
    target_count: 10,
    min_comments: 0,
    min_likes: 0,
    min_favorites: 0,
    days: 7
  })
  
  // 标题候选
  const titleCandidates = ref<string[]>([])
  const selectedTitle = ref<string | null>(null)
  
  // 编辑反馈
  const editorFeedback = ref<{ score: number; feedback: string } | null>(null)
  
  // 最终结果
  const finalPost = ref<{
    title: string
    content: string
    tags: string[]
    images: string[]
  } | null>(null)

  // ========== 计算属性 ==========
  
  // 节点列表（按顺序）
  const nodeList = computed(() => {
    return WORKFLOW_NODES.map(node => {
      const nodeInfo = nodes.value.get(node.id)
      return {
        ...node,
        status: nodeInfo?.status || 'pending',
        progress: nodeInfo?.progress || 0,
        message: nodeInfo?.message,
        input: nodeInfo?.input,
        output: nodeInfo?.output,
        error: nodeInfo?.error,
        startTime: nodeInfo?.startTime,
        endTime: nodeInfo?.endTime
      }
    })
  })
  
  // 当前运行的节点
  const currentNode = computed(() => {
    return nodeList.value.find(node => node.status === 'running')
  })
  
  // 已完成的节点数
  const completedCount = computed(() => {
    return nodeList.value.filter(node => node.status === 'completed').length
  })
  
  // 总进度百分比
  const overallProgress = computed(() => {
    return Math.round((completedCount.value / WORKFLOW_NODES.length) * 100)
  })

  // ========== 方法 ==========
  
  /**
   * 初始化节点状态
   */
  function initNodes() {
    nodes.value.clear()
    WORKFLOW_NODES.forEach(node => {
      nodes.value.set(node.id, {
        id: node.id,
        name: node.name,
        status: 'pending',
        progress: 0
      })
    })
  }
  
  /**
   * 更新节点状态
   */
  function updateNodeStatus(
    nodeId: string,
    status: NodeStatus,
    progress?: number,
    message?: string,
    output?: any,
    error?: string
  ) {
    const node = nodes.value.get(nodeId)
    if (node) {
      node.status = status
      if (progress !== undefined) node.progress = progress
      if (message) node.message = message
      if (output) node.output = output
      if (error) node.error = error

      if (status === 'running' && !node.startTime) {
        node.startTime = Date.now()
      }
      if ((status === 'completed' || status === 'error') && !node.endTime) {
        node.endTime = Date.now()
      }

      nodes.value.set(nodeId, { ...node })
    }
  }

  /**
   * 重置指定节点的状态（用于工作流回退）
   */
  function resetNodes(nodeIds: string[]) {
    nodeIds.forEach(nodeId => {
      const node = nodes.value.get(nodeId)
      if (node) {
        node.status = 'pending'
        node.progress = 0
        node.message = undefined
        node.output = undefined
        node.error = undefined
        node.startTime = undefined
        node.endTime = undefined
        nodes.value.set(nodeId, { ...node })
      }
    })
  }

  /**
   * 添加消息日志
   */
  function addMessage(type: string, content: string) {
    messages.value.push({
      time: Date.now(),
      type,
      content
    })
  }
  
  /**
   * 重置工作流
   */
  function resetWorkflow() {
    taskId.value = null
    taskStatus.value = 'idle'
    initNodes()
    messages.value = []
    titleCandidates.value = []
    selectedTitle.value = null
    editorFeedback.value = null
    finalPost.value = null
  }
  
  /**
   * 设置任务ID
   */
  function setTaskId(id: string) {
    taskId.value = id
  }
  
  /**
   * 设置任务状态
   */
  function setTaskStatus(status: string) {
    taskStatus.value = status
  }
  
  /**
   * 设置标题候选
   */
  function setTitleCandidates(titles: string[]) {
    titleCandidates.value = titles
  }
  
  /**
   * 选择标题
   */
  function selectTitle(title: string) {
    selectedTitle.value = title
  }
  
  /**
   * 设置编辑反馈
   */
  function setEditorFeedback(feedback: { score: number; feedback: string }) {
    editorFeedback.value = feedback
  }
  
  /**
   * 设置最终结果
   */
  function setFinalPost(post: { title: string; content: string; tags: string[]; images: string[] }) {
    finalPost.value = post
  }

  // 初始化节点
  initNodes()

  return {
    // 状态
    taskId,
    taskStatus,
    nodes,
    messages,
    formData,
    titleCandidates,
    selectedTitle,
    editorFeedback,
    finalPost,

    // 计算属性
    nodeList,
    currentNode,
    completedCount,
    overallProgress,

    // 方法
    initNodes,
    updateNodeStatus,
    resetNodes,
    addMessage,
    resetWorkflow,
    setTaskId,
    setTaskStatus,
    setTitleCandidates,
    selectTitle,
    setEditorFeedback,
    setFinalPost
  }
})
