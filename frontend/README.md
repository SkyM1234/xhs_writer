# 小红书内容生成工作流 - 前端

基于 Vue3 + TypeScript + Vite + Tailwind CSS 构建的工作流可视化前端。

## 技术栈

- **框架**: Vue 3.4 + TypeScript
- **构建工具**: Vite 5
- **状态管理**: Pinia
- **路由**: Vue Router 4
- **样式**: Tailwind CSS 3.4
- **HTTP 客户端**: Axios
- **实时通信**: WebSocket (原生)

## 设计系统

查看 [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) 了解完整的设计规范。

### 核心特性
- 🎨 **Glassmorphism + Dark Mode** - 现代玻璃态深色主题
- 📊 **工作流可视化** - 10个节点实时状态展示
- 🔌 **WebSocket 实时通信** - 后端进度实时推送
- 🎯 **人工交互节点** - 标题选择、人工审核等中断点
- 📱 **响应式设计** - 适配桌面和平板设备

## 项目结构

```
frontend/
├── src/
│   ├── api/              # API 服务层
│   │   ├── http.ts       # Axios 实例配置
│   │   ├── content.ts    # 内容生成 API
│   │   └── websocket.ts  # WebSocket 服务
│   ├── components/       # 可复用组件
│   │   ├── workflow/     # 工作流相关组件
│   │   ├── common/       # 通用组件
│   │   └── dialogs/      # 对话框组件
│   ├── stores/           # Pinia 状态管理
│   │   └── workflow.ts   # 工作流状态
│   ├── types/            # TypeScript 类型定义
│   │   └── index.ts      # 通用类型
│   ├── views/            # 页面组件
│   │   └── WorkflowView.vue
│   ├── router/           # 路由配置
│   │   └── index.ts
│   ├── utils/            # 工具函数
│   ├── App.vue           # 根组件
│   ├── main.ts           # 入口文件
│   └── style.css         # 全局样式
├── public/               # 静态资源
├── index.html            # HTML 模板
├── vite.config.ts        # Vite 配置
├── tailwind.config.js    # Tailwind 配置
├── tsconfig.json         # TypeScript 配置
└── package.json          # 依赖配置
```

## 开发指南

### 安装依赖

```bash
cd frontend
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:5173

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 环境变量

在 `.env` 文件中配置：

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

## 工作流节点

1. **热点采集** (trend_collector) - 抓取小红书热榜数据
2. **热点分析** (trend_analyzer) - 分析热点特征
3. **选题策划** (strategist) - 确定内容策略
4. **标题生成** (title_lab) - 生成3个候选标题
5. **文案创作** (copywriter) - 生成完整文案
6. **合规检查** (compliance_checker) - 检测违禁词
7. **终审编辑** (chief_editor) - 质量评分
8. **人工审核** (human_review) - 人工确认
9. **视觉设计** (visual_designer) - 生成配图
10. **最终输出** (finalize) - 输出完整内容

## WebSocket 消息格式

```typescript
interface NodeProgressMessage {
  type: 'node_start' | 'node_progress' | 'node_complete' | 'node_error'
  node_id: string
  node_name: string
  status: 'running' | 'completed' | 'error'
  progress: number
  message?: string
  output?: any
}
```

## 开发规范

- 使用 TypeScript 严格模式
- 遵循 Vue 3 Composition API
- 使用 Tailwind CSS 工具类
- 组件命名采用 PascalCase
- 文件命名采用 kebab-case

## 浏览器支持

- Chrome >= 90
- Firefox >= 88
- Safari >= 14
- Edge >= 90

## License

MIT
