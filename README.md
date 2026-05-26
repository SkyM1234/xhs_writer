# Xiaohongshu-Flow (小红书爆款内容生成系统)

基于 LangGraph 多智能体协作的小红书内容自动化生产系统，从关键词输入到爆款图文输出的完整工作流。

## ✨ 项目简介

Xiaohongshu-Flow 是一个智能内容生成系统，通过多个 AI 智能体的协作，自动完成小红书内容的创作全流程：热点采集 → 数据分析 → 选题策划 → 标题生成 → 文案创作 → 合规检查 → 质量评审 → 图片生成。

### 核心特性

- 🔍 **真实数据采集**：集成小红书爬虫，抓取真实热门笔记数据
- 🤖 **多智能体协作**：10个专业智能体分工协作，模拟真实内容团队
- 🔄 **自动质量控制**：合规检查 + AI评分 + 人工审核的三重质量保障
- 💾 **断点恢复机制**：基于 LangGraph Checkpointer，支持流程中断后恢复
- 🎨 **AI 图片生成**：支持通义万相等图片生成服务
- 🔎 **RAG 风格检索**：使用向量数据库存储历史风格，保持账号人设一致性
- 👁️ **视觉内容分析**：使用 Qwen VL 模型自动将图片/视频转换为文字描述
- ⚡ **实时状态推送**：WebSocket 实时推送节点执行状态
- 📝 **任务管理**：支持待处理任务列表，可恢复中断的生成流程

## 🏗️ 技术架构

### 技术栈

**后端**
- FastAPI - 异步 Web 框架
- LangGraph - 多智能体工作流编排
- SQLAlchemy - ORM 框架
- MySQL - 爬虫数据存储
- Redis - 缓存层
- ChromaDB - 向量数据库（风格检索）
- WebSocket - 实时通信

**前端**
- Vue 3 + TypeScript
- Vite - 构建工具
- Tailwind CSS - UI 样式
- Pinia - 状态管理
- Axios - HTTP 客户端

**AI 服务**
- 支持 DeepSeek / Qwen / OpenAI
- 通义万相 - 图片生成

### LangGraph 工作流架构

系统包含 10 个智能体节点，分为 4 层：

#### 1️⃣ 数据采集层
- **trend_collector**（热点采集员）：爬取小红书热门笔记，支持关键词、话题、互动量筛选
- **trend_analyzer**（热点分析员）：分析爆款模板，提取话题切入点、情绪共鸣点、标签策略

#### 2️⃣ 内容生产层
- **strategist**（选题策划师）：确定内容角度、目标受众、情感基调
- **title_lab**（标题实验室）：生成 3 个候选标题，支持人工选择
- **copywriter**（爆款写手）：创作正文，三段式结构 + Emoji 优化
- **visual_designer**（视觉设计师）：生成配图提示词并调用图片生成服务

#### 3️⃣ 质量控制层
- **compliance_checker**（合规检查员）：检测敏感词、违禁内容
- **chief_editor**（终审编辑）：AI 质量评分（0-100分）
- **human_review**（人工审核）：人在回路（Human-in-the-loop）断点

#### 4️⃣ 输出层
- **finalize**（最终化）：整合所有内容，生成最终笔记

### 条件路由机制

```
copywriter → compliance_checker
                ├─ 通过 → chief_editor
                └─ 不通过 → copywriter（重写）

chief_editor
    ├─ 评分 ≥ 90 → visual_designer（直接生成图片）
    ├─ 80 ≤ 评分 < 90 → human_review（人工审核）
    └─ 评分 < 80 → copywriter（重写）

human_review
    ├─ 用户批准 → visual_designer
    └─ 用户拒绝 → copywriter（重写）
```

## 📁 项目结构

```
xhs_writer/
├── backend/
│   ├── app/
│   │   ├── agents/                  # LangGraph 核心
│   │   │   ├── graph.py              # 工作流定义
│   │   │   ├── nodes.py              # 智能体节点实现
│   │   │   ├── state.py              # 状态管理
│   │   │   ├── tools.py              # 工具函数
│   │   │   └── error_handling.py     # 错误处理
│   │   ├── api/v1/                   # API 路由
│   │   │   ├── content_generation.py # 内容生成接口
│   │   │   └── pending_tasks.py      # 任务管理接口
│   │   ├── core/                     # 核心配置
│   │   │   ├── config.py             # 配置管理
│   │   │   ├── llm.py                # LLM 客户端
│   │   │   ├── cache.py              # Redis 缓存
│   │   │   ├── logger.py             # 日志系统
│   │   │   └── websocket_manager.py  # WebSocket 管理
│   │   ├── database/                 # 数据库
│   │   │   ├── db.py                 # 数据库连接
│   │   │   ├── models.py             # 数据模型
│   │   │   └── session.py            # 会话管理
│   │   ├── services/                 # 业务服务
│   │   │   ├── xhs_crawler_service.py        # 小红书爬虫
│   │   │   ├── image_generation_service.py   # 图片生成
│   │   │   ├── style_retrieval_service.py    # 风格检索（RAG）
│   │   │   └── pending_task_service.py       # 任务管理
│   │   ├── utils/                    # 工具模块
│   │   │   ├── MediaCrawler_XHS/     # 小红书爬虫库
│   │   │   └── image_downloader.py   # 图片下载
│   │   └── models/
│   │       └── schemas.py            # Pydantic 模型
│   ├── main.py                       # 应用入口
│   ├── requirements.txt              # Python 依赖
│   ├── data/                         # 数据目录
│   ├── logs/                         # 日志目录
│   ├── checkpoints/                  # LangGraph 检查点
|   └── scripts/                      # 脚本目录
├── frontend/
│   ├── src/
│   │   ├── api/                      # API 封装
│   │   │   ├── http.ts              # HTTP 客户端
│   │   │   ├── content.ts           # 内容接口
│   │   │   └── websocket.ts         # WebSocket 客户端
│   │   ├── components/               # UI 组件
│   │   │   ├── workflow/            # 工作流组件
│   │   │   └── dialogs/             # 对话框组件
│   │   ├── views/                    # 页面视图
│   │   │   ├── WorkflowView.vue     # 工作流页面
│   │   │   ├── NotesView.vue        # 笔记列表
│   │   │   ├── NoteDetailView.vue   # 笔记详情
│   │   │   └── PendingTasksView.vue # 待处理任务
│   │   ├── stores/                   # 状态管理
│   │   │   └── workflow.ts          # 工作流状态
│   │   ├── types/                    # TypeScript 类型
│   │   ├── router/                   # 路由配置
│   │   └── main.ts                   # 应用入口
│   ├── package.json
│   └── vite.config.ts
└── docs/                             # 文档目录
```

## 🚀 快速开始

### 环境要求

- Python 3.9+
- Node.js 16+
- Redis 5.0+
- MySQL 5.7+

### 后端配置

1. 安装依赖
```bash
cd backend
pip install -r requirements.txt
playwright install chromium  # 安装浏览器驱动
```

2. 配置环境变量（backend\app\core\config.py）
```bash
# LLM 配置
LLM_PROVIDER=deepseek  # deepseek / qwen / openai
LLM_MODEL=deepseek-v4-flash
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.deepseek.com

# 数据库配置
DATABASE_URL=sqlite:///./xhs_writer.db
REDIS_URL=redis://localhost:6379/0

# MySQL 配置（爬虫数据）
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=xhs_crawler

# 图片生成配置
IMAGE_PROVIDER=qwen
IMAGE_API_KEY=your_qwen_api_key
```

3. 构建风格向量库
```bash
cd backend
python scripts/build_style_vectordb.py
```

4. 启动后端
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

后端将运行在 `http://localhost:8000`

### 前端配置

1. 安装依赖
```bash
cd frontend
npm install
```

2. 启动开发服务器
```bash
npm run dev
```

前端将运行在 `http://localhost:5173`

## 📖 使用指南

### 1. 创建内容生成任务

在前端界面输入：
- **关键词**：如 "职场穿搭"、"减肥食谱"
- **话题词**：如 "#OOTD"、"#健康生活"（可选）
- **账号人设**：如 "职场精英"、"健身博主"（可选）
- **爬虫配置**：目标笔记数、最小互动量、时间范围

### 2. 工作流执行

系统自动执行 10 个节点，实时显示：
- ✅ 已完成节点（绿色）
- ⏳ 执行中节点（蓝色动画）
- ⏸️ 等待中节点（灰色）
- ❌ 失败节点（红色）

### 3. 人工审核

当内容评分在 80-90 分时，系统会暂停并等待人工审核：
- 查看生成的标题和正文
- 选择"批准"继续生成图片
- 选择"拒绝"重新生成内容

### 4. 查看结果

生成完成后可以：
- 在笔记列表查看所有生成的内容
- 查看详细信息（标题、正文、图片、标签）
- 导出内容用于发布

### 5. 恢复暂缓的任务

如果流程暂缓（标题选择节点、人工审核节点），可以在"待处理任务"页面：
- 查看所有未完成的任务
- 点击"恢复"继续执行
- 点击"删除"清理任务

## 🔧 配置说明

### LLM 配置

支持多个 LLM 提供商，在 `backend/app/core/config.py` 中配置：

```python
LLM_PROVIDER = "deepseek"  # deepseek / qwen / openai
LLM_MODEL = "deepseek-chat"
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 2000
```

### 爬虫配置

小红书爬虫配置在 `backend/app/utils/MediaCrawler_XHS/config/` 中：
- 浏览器配置
- 登录凭证
- 代理设置

## 📊 API 文档

启动后端后访问：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 主要接口

**POST /api/v1/generate**
- 创建内容生成任务
- 返回 task_id

**GET /api/v1/stream/{task_id}**
- WebSocket 连接，实时推送节点状态

**POST /api/v1/resume/{task_id}**
- 恢复中断的任务

**POST /api/v1/human-review/{task_id}**
- 提交人工审核决策

## 🛠️ 开发指南

### 添加新的智能体节点

1. 在 `backend/app/agents/nodes.py` 中定义节点函数
2. 在 `backend/app/agents/graph.py` 中注册节点
3. 添加节点间的边或条件路由

### 扩展 LLM 支持

在 `backend/app/core/llm.py` 中添加新的 LLM 客户端实现。

### 自定义爬虫逻辑

修改 `backend/app/services/xhs_crawler_service.py` 中的爬取策略。

## ⚠️ 注意事项

1. **API Key 安全**：不要将 API Key 提交到代码仓库
2. **爬虫合规**：遵守小红书平台规则，合理控制爬取频率
3. **内容审核**：生成的内容仅供参考，发布前需人工审核
4. **资源消耗**：LLM 调用会产生费用，注意控制使用量

## 📄 License

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📮 联系方式

如有问题或建议，请提交 Issue。
