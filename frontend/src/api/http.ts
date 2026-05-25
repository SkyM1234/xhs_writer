import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios'

/**
 * 创建 Axios 实例
 */
const http: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 600000, // 600秒超时（工作流可能需要较长时间）
  headers: {
    'Content-Type': 'application/json'
  }
})

/**
 * 请求拦截器
 */
http.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 可以在这里添加 token 等认证信息
    // const token = localStorage.getItem('token')
    // if (token && config.headers) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }

    console.log(`[HTTP] ${config.method?.toUpperCase()} ${config.url}`, config.params || config.data)
    return config
  },
  (error: AxiosError) => {
    console.error('[HTTP] 请求错误:', error)
    return Promise.reject(error)
  }
)

/**
 * 响应拦截器
 */
http.interceptors.response.use(
  (response: AxiosResponse) => {
    console.log(`[HTTP] 响应成功:`, response.data)
    return response
  },
  (error: AxiosError) => {
    console.error('[HTTP] 响应错误:', error)

    // 统一错误处理
    if (error.response) {
      // 服务器返回错误状态码
      const { status, data } = error.response
      
      switch (status) {
        case 400:
          console.error('[HTTP] 请求参数错误:', data)
          break
        case 401:
          console.error('[HTTP] 未授权，请登录')
          // 可以跳转到登录页
          break
        case 403:
          console.error('[HTTP] 没有权限访问')
          break
        case 404:
          console.error('[HTTP] 请求的资源不存在')
          break
        case 500:
          console.error('[HTTP] 服务器内部错误')
          break
        default:
          console.error(`[HTTP] 请求失败: ${status}`)
      }
    } else if (error.request) {
      // 请求已发送但没有收到响应
      console.error('[HTTP] 网络错误，请检查网络连接')
    } else {
      // 请求配置出错
      console.error('[HTTP] 请求配置错误:', error.message)
    }

    return Promise.reject(error)
  }
)

export default http
