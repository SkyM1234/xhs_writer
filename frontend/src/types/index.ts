// 节点状态类型
export type NodeStatus = 'pending' | 'running' | 'completed' | 'error'

// 节点信息
export interface NodeInfo {
  id: string
  name: string
  status: NodeStatus
  progress: number
  message?: string
  input?: any
  output?: any
  error?: string
  startTime?: number
  endTime?: number
}

// WebSocket 消息类型
export interface NodeProgressMessage {
  type: 'node_start' | 'node_progress' | 'node_complete' | 'node_error' | 'message' | 'nodes_reset'
  node_id?: string
  node_name?: string
  status?: NodeStatus
  progress?: number
  message?: string
  error?: string
  output?: any
  node_ids?: string[]  // 用于 nodes_reset 消息
}

// 内容生成请求
export interface ContentGenerationRequest {
  keywords: string[]
  topic_words?: string[]
  account_persona?: string
  target_count?: number
  min_comments?: number
  min_likes?: number
  min_favorites?: number
  days?: number
}

// 内容生成响应
export interface ContentGenerationResponse {
  task_id: string
  status: string
  title_candidates?: string[]
  draft_content?: string
  editor_feedback?: {
    score: number
    feedback: string
  }
  image_prompts?: string[]
  image_urls?: string[]
  image_local_paths?: string[]
  final_post?: {
    title: string
    content: string
    tags: string[]
    images: string[]
  }
  messages: string[]
  error?: string
}

// 标题选择请求
export interface TitleSelectionRequest {
  task_id: string
  selected_title?: string
  action?: 'select' | 'postpone'
}

// 人工审核请求
export interface HumanReviewRequest {
  task_id: string
  decision: 'approve' | 'reject' | 'postpone'
  feedback?: string
}
