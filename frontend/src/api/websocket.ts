import type { NodeProgressMessage } from '@/types'

type ProgressCallback = (message: NodeProgressMessage) => void

class WebSocketService {
  private ws: WebSocket | null = null
  private taskId: string | null = null
  private callback: ProgressCallback | null = null
  private heartbeatTimer: number | null = null
  private reconnectTimer: number | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 3000
  private isManualClose = false

  /**
   * 连接 WebSocket
   */
  connect(taskId: string, onProgress: ProgressCallback) {
    this.taskId = taskId
    this.callback = onProgress
    this.isManualClose = false
    this.reconnectAttempts = 0

    this.createConnection()
  }

  /**
   * 创建 WebSocket 连接
   */
  private createConnection() {
    if (!this.taskId) {
      console.error('[WebSocket] taskId 为空，无法连接')
      return
    }

    const wsUrl = `${import.meta.env.VITE_WS_BASE_URL}/api/v1/content/ws/${this.taskId}`
    console.log(`[WebSocket] 正在连接: ${wsUrl}`)

    try {
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log('[WebSocket] 连接成功')
        this.reconnectAttempts = 0
        this.startHeartbeat()
      }

      this.ws.onmessage = (event) => {
        try {
          const message: NodeProgressMessage = JSON.parse(event.data)
          console.log('[WebSocket] 收到消息:', message)

          if (this.callback) {
            this.callback(message)
          }
        } catch (error) {
          console.error('[WebSocket] 消息解析失败:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('[WebSocket] 连接错误:', error)
      }

      this.ws.onclose = (event) => {
        console.log('[WebSocket] 连接关闭:', event.code, event.reason)
        this.stopHeartbeat()

        // 如果不是手动关闭，尝试重连
        if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect()
        }
      }
    } catch (error) {
      console.error('[WebSocket] 创建连接失败:', error)
    }
  }

  /**
   * 启动心跳检测
   */
  private startHeartbeat() {
    this.stopHeartbeat()

    this.heartbeatTimer = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send('ping')
      }
    }, 30000) // 每30秒发送一次心跳
  }

  /**
   * 停止心跳检测
   */
  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * 安排重连
   */
  private scheduleReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * this.reconnectAttempts

    console.log(`[WebSocket] 将在 ${delay}ms 后尝试第 ${this.reconnectAttempts} 次重连`)

    this.reconnectTimer = window.setTimeout(() => {
      console.log(`[WebSocket] 开始第 ${this.reconnectAttempts} 次重连`)
      this.createConnection()
    }, delay)
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.isManualClose = true
    this.stopHeartbeat()

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.taskId = null
    this.callback = null
    this.reconnectAttempts = 0

    console.log('[WebSocket] 已断开连接')
  }

  /**
   * 获取连接状态
   */
  getReadyState(): number {
    return this.ws ? this.ws.readyState : WebSocket.CLOSED
  }

  /**
   * 是否已连接
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }
}

// 导出单例
export const wsService = new WebSocketService()
