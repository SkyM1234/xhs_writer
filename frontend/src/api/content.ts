import http from './http'
import type {
  ContentGenerationRequest,
  ContentGenerationResponse,
  TitleSelectionRequest,
  HumanReviewRequest
} from '@/types'

/**
 * 生成标题候选
 * @param request 内容生成请求参数
 * @param taskId 任务ID（可选，前端生成）
 */
export const generateTitles = async (
  request: ContentGenerationRequest,
  taskId?: string
): Promise<ContentGenerationResponse> => {
  const params = taskId ? { task_id: taskId } : {}
  const response = await http.post<ContentGenerationResponse>(
    '/api/v1/content/generate/titles',
    request,
    { params }
  )
  return response.data
}

/**
 * 选择标题后继续生成完整内容
 * @param request 标题选择请求
 */
export const continueGeneration = async (
  request: TitleSelectionRequest
): Promise<ContentGenerationResponse> => {
  const response = await http.post<ContentGenerationResponse>(
    '/api/v1/content/generate/continue',
    request
  )
  return response.data
}

/**
 * 人工审核接口
 * @param request 人工审核请求
 */
export const submitHumanReview = async (
  request: HumanReviewRequest
): Promise<ContentGenerationResponse> => {
  const response = await http.post<ContentGenerationResponse>(
    '/api/v1/content/generate/human-review',
    request
  )
  return response.data
}

/**
 * 查询任务状态
 * @param taskId 任务ID
 */
export const getTaskStatus = async (
  taskId: string
): Promise<ContentGenerationResponse> => {
  const response = await http.get<ContentGenerationResponse>(
    `/api/v1/content/task/${taskId}`
  )
  return response.data
}

/**
 * 删除任务
 * @param taskId 任务ID
 */
export const deleteTask = async (taskId: string): Promise<void> => {
  await http.delete(`/api/v1/content/task/${taskId}`)
}

/**
 * 列出所有任务
 */
export const listTasks = async (): Promise<{ tasks: Array<{ task_id: string; status: string }> }> => {
  const response = await http.get('/api/v1/content/tasks')
  return response.data
}

/**
 * 健康检查
 */
export const healthCheck = async (): Promise<{ status: string; service: string }> => {
  const response = await http.get('/api/v1/content/health')
  return response.data
}

/**
 * 列出所有笔记
 */
export const listNotes = async (): Promise<{
  notes: Array<{
    folder_name: string
    title: string
    keywords: string[]
    quality_score: number
    image_count: number
    has_images: boolean
  }>
}> => {
  const response = await http.get('/api/v1/content/notes')
  return response.data
}

/**
 * 获取笔记详情
 * @param folderName 笔记文件夹名称
 */
export const getNoteDetail = async (folderName: string): Promise<{
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
}> => {
  const response = await http.get(`/api/v1/content/notes/${folderName}`)
  return response.data
}

/**
 * 删除笔记
 * @param folderName 笔记文件夹名称
 */
export const deleteNote = async (folderName: string): Promise<void> => {
  await http.delete(`/api/v1/content/notes/${folderName}`)
}

/**
 * 列出所有待处理任务
 * @param taskType 任务类型过滤（可选）
 */
export const listPendingTasks = async (taskType?: string): Promise<{
  id: number
  task_id: string
  task_type: string
  status: string
  keywords: string[]
  title_candidates?: string[]
  draft_content?: string
  editor_feedback?: any
  created_at: number
  updated_at: number
}[]> => {
  const params = taskType ? { task_type: taskType } : {}
  const response = await http.get('/api/v1/pending-tasks/', { params })
  return response.data
}

/**
 * 获取待处理任务详情
 * @param taskId 任务ID
 */
export const getPendingTask = async (taskId: string) => {
  const response = await http.get(`/api/v1/pending-tasks/${taskId}`)
  return response.data
}

/**
 * 删除待处理任务
 * @param taskId 任务ID
 */
export const deletePendingTask = async (taskId: string): Promise<void> => {
  await http.delete(`/api/v1/pending-tasks/${taskId}`)
}

/**
 * 从 checkpoint 恢复任务状态
 * @param taskId 任务ID
 */
export const restorePendingTask = async (taskId: string) => {
  const response = await http.get(`/api/v1/pending-tasks/${taskId}/restore`)
  return response.data
}
