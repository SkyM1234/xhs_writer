import { createRouter, createWebHistory } from 'vue-router'
import WorkflowView from '@/views/WorkflowView.vue'
import NotesView from '@/views/NotesView.vue'
import NoteDetailView from '@/views/NoteDetailView.vue'
import PendingTasksView from '@/views/PendingTasksView.vue'
import { useWorkflowStore } from '@/stores/workflow'

const router = createRouter({
  history: createWebHistory(import.meta.url),
  routes: [
    {
      path: '/',
      name: 'workflow',
      component: WorkflowView
    },
    {
      path: '/pending-tasks',
      name: 'pending-tasks',
      component: PendingTasksView
    },
    {
      path: '/notes',
      name: 'notes',
      component: NotesView
    },
    {
      path: '/notes/:folderName',
      name: 'note-detail',
      component: NoteDetailView
    }
  ]
})

// 导航守卫：检查是否有正在运行的任务
router.beforeEach((to, from, next) => {
  console.log('[Router] 导航守卫触发:', { from: from.path, to: to.path })

  // 只在从工作流页面离开时检查
  if (from.path === '/' && to.path !== '/') {
    const workflowStore = useWorkflowStore()

    console.log('[Router] 检查任务状态:', {
      taskStatus: workflowStore.taskStatus,
      taskId: workflowStore.taskId
    })

    // 如果有任务正在运行，提示用户
    if (workflowStore.taskStatus === 'running' && workflowStore.taskId) {
      console.log('[Router] 任务正在运行，弹出确认对话框')

      const confirmed = window.confirm(
        '⚠️ 任务正在运行中\n\n' +
        '离开页面会断开 WebSocket 连接，导致无法接收任务状态更新。\n\n' +
        '确定要离开吗？'
      )

      if (!confirmed) {
        console.log('[Router] 用户取消导航，停留在当前页面')
        // 用户取消，停留在当前页面
        next(false)
        return
      }

      console.log('[Router] 用户确认离开')
    }
  }

  // 继续导航
  next()
})

export default router
