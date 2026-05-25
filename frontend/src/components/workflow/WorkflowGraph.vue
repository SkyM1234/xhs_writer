<template>
  <div class="workflow-graph-container" @click="handleContainerClick">
    <!-- 装饰性背景网格 -->
    <div class="canvas-grid"></div>
    <div class="canvas-glow"></div>

    <svg
      class="workflow-svg"
      :viewBox="`0 0 ${svgWidth} ${svgHeight}`"
      preserveAspectRatio="xMidYMid meet"
    >
      <defs>
        <!-- 箭头标记 -->
        <marker id="arrow-normal" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill="#64748b" />
        </marker>
        <marker id="arrow-active" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill="#a78bfa" />
        </marker>
        <marker id="arrow-back" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill="#fbbf24" />
        </marker>
        <marker id="arrow-cond" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill="#60a5fa" />
        </marker>

        <!-- 节点渐变：5 组职能色 (顶亮 → 底暗，带分组色调) -->
        <linearGradient id="grad-collect" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#1e3a52" />
          <stop offset="100%" stop-color="#172a3a" />
        </linearGradient>
        <linearGradient id="grad-plan" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#3a2a5c" />
          <stop offset="100%" stop-color="#251a3d" />
        </linearGradient>
        <linearGradient id="grad-create" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#5c2545" />
          <stop offset="100%" stop-color="#3d1830" />
        </linearGradient>
        <linearGradient id="grad-review" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#5c4419" />
          <stop offset="100%" stop-color="#3d2c10" />
        </linearGradient>
        <linearGradient id="grad-output" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#1d4d4a" />
          <stop offset="100%" stop-color="#13332f" />
        </linearGradient>

        <!-- 图标圆形底色滤镜：让 emoji 图标更突出 -->
        <filter id="icon-shadow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2" />
        </filter>
      </defs>

      <!-- 连线 -->
      <g class="edges-layer">
        <path
          v-for="edge in edges"
          :key="edge.id"
          :d="edge.path"
          :class="['edge', edge.type, { active: edge.active }]"
          :marker-end="getMarkerEnd(edge)"
        />
      </g>

      <!-- 节点 -->
      <g class="nodes-layer">
        <g
          v-for="node in layoutNodes"
          :key="node.id"
          :transform="`translate(${node.x}, ${node.y})`"
          class="node-group"
          :class="[`status-${node.status}`, `category-${getNodeCategory(node.id)}`]"
          @click.stop="handleNodeClick(node)"
        >
          <!-- 节点背景矩形（带分组渐变） -->
          <rect
            :x="-nodeWidth / 2"
            :y="-nodeHeight / 2"
            :width="nodeWidth"
            :height="nodeHeight"
            rx="14"
            class="node-bg"
            :fill="`url(#grad-${getNodeCategory(node.id)})`"
          />

          <!-- 顶部高光线（玻璃质感） -->
          <line
            :x1="-nodeWidth / 2 + 14"
            :x2="nodeWidth / 2 - 14"
            :y1="-nodeHeight / 2 + 1"
            :y2="-nodeHeight / 2 + 1"
            class="node-highlight"
          />

          <!-- 图标圆形底 -->
          <circle
            cx="0"
            cy="-12"
            r="16"
            class="icon-bg"
            :class="`icon-bg-${getNodeCategory(node.id)}`"
          />

          <!-- 节点图标 -->
          <text
            x="0"
            y="-12"
            text-anchor="middle"
            dominant-baseline="central"
            class="node-icon-text"
          >{{ getNodeIcon(node.id) }}</text>

          <!-- 节点名称 -->
          <text
            x="0"
            y="20"
            text-anchor="middle"
            dominant-baseline="middle"
            class="node-name-text"
          >{{ node.name }}</text>

          <!-- 状态指示点 -->
          <circle
            :cx="nodeWidth / 2 - 10"
            :cy="-nodeHeight / 2 + 10"
            r="4"
            :class="['status-dot', `dot-${node.status}`]"
          />
        </g>
      </g>
    </svg>

    <!-- 分组图例 + 状态图例 -->
    <div class="legend">
      <div class="legend-section">
        <span class="legend-title">阶段</span>
        <span class="legend-item"><i class="dot-cat cat-collect"></i>采集</span>
        <span class="legend-item"><i class="dot-cat cat-plan"></i>策划</span>
        <span class="legend-item"><i class="dot-cat cat-create"></i>创作</span>
        <span class="legend-item"><i class="dot-cat cat-review"></i>审核</span>
        <span class="legend-item"><i class="dot-cat cat-output"></i>输出</span>
      </div>
      <div class="legend-divider"></div>
      <div class="legend-section">
        <span class="legend-title">状态</span>
        <span class="legend-item"><i class="dot-st st-pending"></i>待执行</span>
        <span class="legend-item"><i class="dot-st st-running"></i>运行中</span>
        <span class="legend-item"><i class="dot-st st-completed"></i>已完成</span>
        <span class="legend-item"><i class="dot-st st-error"></i>错误</span>
      </div>
    </div>

    <!-- 节点详情 Modal -->
    <transition name="modal-fade">
      <div v-if="selectedNode" class="modal-overlay" @click="selectedNode = null">
        <div class="modal-box" @click.stop>
          <!-- Modal 头部 -->
          <div class="modal-header">
            <div class="flex items-center gap-3">
              <div class="text-3xl">{{ getNodeIcon(selectedNode.id) }}</div>
              <div>
                <h3 class="text-lg font-semibold text-text-primary">{{ selectedNode.name }}</h3>
                <p class="text-sm text-text-muted">{{ selectedNode.id }}</p>
              </div>
            </div>
            <button @click="selectedNode = null" class="close-btn">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Modal 内容 -->
          <div class="modal-content">
            <div class="detail-section">
              <div class="detail-label">描述</div>
              <div class="detail-value">{{ getNodeDescription(selectedNode.id) }}</div>
            </div>

            <div class="detail-section">
              <div class="detail-label">状态</div>
              <div class="detail-value">
                <span class="status-badge" :class="`badge-${selectedNode.status}`">
                  {{ getStatusText(selectedNode.status) }}
                </span>
              </div>
            </div>

            <div v-if="selectedNode.message" class="detail-section">
              <div class="detail-label">消息</div>
              <div class="detail-value text-sm">{{ selectedNode.message }}</div>
            </div>

            <div v-if="selectedNode.error" class="detail-section">
              <div class="detail-label">错误</div>
              <div class="detail-value">
                <div class="error-box">{{ selectedNode.error }}</div>
              </div>
            </div>

            <div v-if="selectedNode.startTime" class="detail-section">
              <div class="detail-label">执行时间</div>
              <div class="detail-value text-sm">
                <div v-if="selectedNode.endTime">
                  耗时: {{ formatDuration(selectedNode.endTime - selectedNode.startTime) }}
                </div>
                <div v-else>开始: {{ formatTime(selectedNode.startTime) }}</div>
              </div>
            </div>

            <div v-if="selectedNode.output" class="detail-section">
              <div class="detail-label">输出数据</div>
              <div class="detail-value">
                <pre class="data-box">{{ JSON.stringify(selectedNode.output, null, 2) }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { NodeStatus } from '@/types'

interface Props {
  nodes: Array<{
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
  }>
}

const props = defineProps<Props>()
const selectedNode = ref<any>(null)

// 节点图标映射
const nodeIcons: Record<string, string> = {
  trend_collector: '🔍',
  trend_analyzer: '📊',
  strategist: '🎯',
  title_lab: '✨',
  copywriter: '✍️',
  compliance_checker: '🛡️',
  chief_editor: '👔',
  human_review: '👤',
  visual_designer: '🎨',
  finalize: '🎉'
}

// 节点描述映射
const nodeDescriptions: Record<string, string> = {
  trend_collector: '实时抓取小红书热榜、竞品关键词数据',
  trend_analyzer: '分析热点数据，提取爆款特征和模板',
  strategist: '确定内容人设、切入角度、目标受众',
  title_lab: '同时生成3个不同风格的标题供选择',
  copywriter: '生成正文：三段式、Emoji、SEO标签',
  compliance_checker: '检测违禁词、广告法、平台规则',
  chief_editor: '综合评估内容质量，决定通过/打回',
  human_review: '人工确认内容是否符合要求',
  visual_designer: '生成配图提示词，然后生成图片',
  finalize: '输出完整的小红书内容'
}

// 节点尺寸（缩小以适应屏幕）
const nodeWidth = 100
const nodeHeight = 70

// 节点布局（中心点坐标）- 四行布局
const nodePositions: Record<string, { x: number; y: number }> = {
  // 第一行：热点采集 → 热点分析 → 选题策划 → 标题生成（4个节点）
  trend_collector: { x: 100, y: 60 },
  trend_analyzer: { x: 250, y: 60 },
  strategist: { x: 400, y: 60 },
  title_lab: { x: 550, y: 60 },

  // 第二行：文案创作（1个节点，居中）
  copywriter: { x: 325, y: 160 },

  // 第三行：合规检查 → 终审编辑 → 人工审核（3个节点）
  compliance_checker: { x: 175, y: 260 },
  chief_editor: { x: 325, y: 260 },
  human_review: { x: 475, y: 260 },

  // 第四行：视觉设计 → 最终输出（2个节点）
  visual_designer: { x: 250, y: 360 },
  finalize: { x: 400, y: 360 }
}

// SVG 画布尺寸（优化以适应屏幕）
const svgWidth = 650
const svgHeight = 420

// 计算带位置的节点列表
const layoutNodes = computed(() => {
  return props.nodes.map(node => ({
    ...node,
    x: nodePositions[node.id]?.x || 0,
    y: nodePositions[node.id]?.y || 0
  }))
})

// 边的类型
interface Edge {
  id: string
  from: string
  to: string
  type: 'normal' | 'back' | 'conditional'
  path: string
  active: boolean
}

// 计算连线
const edges = computed<Edge[]>(() => {
  const result: Edge[] = []

  // 第一行：热点采集 → 热点分析 → 选题策划 → 标题生成
  result.push(createEdge('trend_collector', 'trend_analyzer', 'normal'))
  result.push(createEdge('trend_analyzer', 'strategist', 'normal'))
  result.push(createEdge('strategist', 'title_lab', 'normal'))

  // 第一行到第二行：标题生成 → 文案创作
  result.push(createEdge('title_lab', 'copywriter', 'normal'))

  // 第二行到第三行：文案创作 → 合规检查
  result.push(createEdge('copywriter', 'compliance_checker', 'normal'))

  // 第三行：合规检查 → 终审编辑 → 人工审核
  result.push(createEdge('compliance_checker', 'chief_editor', 'normal'))
  result.push(createEdge('chief_editor', 'human_review', 'conditional'))  // 条件分支

  // 回退路径：合规检查不通过 → 文案创作
  result.push(createEdge('compliance_checker', 'copywriter', 'back'))

  // 回退路径：终审编辑不通过 → 文案创作
  result.push(createEdge('chief_editor', 'copywriter', 'back'))

  // 回退路径：人工审核不通过 → 文案创作
  result.push(createEdge('human_review', 'copywriter', 'back'))

  // 第三行到第四行：终审编辑 → 视觉设计
  result.push(createEdge('chief_editor', 'visual_designer', 'normal'))

  // 第三行到第四行：人工审核 → 视觉设计
  result.push(createEdge('human_review', 'visual_designer', 'normal'))

  // 第四行：视觉设计 → 最终输出
  result.push(createEdge('visual_designer', 'finalize', 'normal'))

  return result
})

// 创建边 - 路径从节点边缘出发，到目标节点边缘结束
function createEdge(from: string, to: string, type: 'normal' | 'back' | 'conditional'): Edge {
  const fromPos = nodePositions[from]
  const toPos = nodePositions[to]

  if (!fromPos || !toPos) {
    return { id: `${from}-${to}`, from, to, type, path: '', active: false }
  }

  const x1 = fromPos.x
  const y1 = fromPos.y
  const x2 = toPos.x
  const y2 = toPos.y

  let path = ''

  if (type === 'normal') {
    if (Math.abs(y2 - y1) < 10) {
      // 水平线：右边缘 → 左边缘
      path = `M ${x1 + nodeWidth / 2} ${y1} L ${x2 - nodeWidth / 2} ${y2}`
    } else {
      // 垂直/斜线：底部 → 顶部（贝塞尔曲线）
      const sx = x1, sy = y1 + nodeHeight / 2
      const ex = x2, ey = y2 - nodeHeight / 2
      const my = (sy + ey) / 2
      path = `M ${sx} ${sy} C ${sx} ${my}, ${ex} ${my}, ${ex} ${ey}`
    }
  } else if (type === 'back') {
    // 回退路径：根据起点位置使用不同的绕行策略
    // 为每条回退线设计独立的路径，避免穿过其他节点

    if (from === 'compliance_checker') {
      // 合规检查 → 文案创作：从顶部中点出发，向左绕行
      const sx = x1  // 起点中心
      const sy = y1 - nodeHeight / 2  // 起点顶部
      const ex = x2 - nodeWidth / 2  // 终点左边缘
      const ey = y2  // 终点中心（左边中点）

      // 向左绕行的贝塞尔曲线
      const controlX = x1 - 40
      const controlY = (sy + ey) / 2
      path = `M ${sx} ${sy} C ${controlX} ${sy}, ${controlX} ${ey}, ${ex} ${ey}`

    } else if (from === 'chief_editor') {
      // 终审编辑 → 文案创作：从顶部中点直接向上
      const sx = x1  // 起点中心
      const sy = y1 - nodeHeight / 2  // 起点顶部
      const ex = x2  // 终点中心
      const ey = y2 + nodeHeight / 2  // 终点底部

      // 直线向上
      path = `M ${sx} ${sy} L ${ex} ${ey}`

    } else if (from === 'human_review') {
      // 人工审核 → 文案创作：从顶部中点出发，向右绕行
      const sx = x1  // 起点中心
      const sy = y1 - nodeHeight / 2  // 起点顶部
      const ex = x2 + nodeWidth / 2  // 终点右边缘
      const ey = y2  // 终点中心（右边中点）

      // 向右绕行的贝塞尔曲线
      const controlX = x1 + 40
      const controlY = (sy + ey) / 2
      path = `M ${sx} ${sy} C ${controlX} ${sy}, ${controlX} ${ey}, ${ex} ${ey}`

    } else {
      // 默认回退路径
      const sx = x1, sy = y1 + nodeHeight / 2
      const ex = x2, ey = y2 + nodeHeight / 2
      const midX = (sx + ex) / 2
      const controlY = Math.max(sy, ey) + 50
      path = `M ${sx} ${sy} Q ${midX} ${controlY}, ${ex} ${ey}`
    }
  } else if (type === 'conditional') {
    // 条件分支：底部 → 顶部
    path = `M ${x1 + nodeWidth / 2} ${y1} L ${x2 - nodeWidth / 2} ${y2}`
  }

  const fromNode = props.nodes.find(n => n.id === from)
  const active = fromNode?.status === 'completed' || fromNode?.status === 'running'

  return { id: `${from}-${to}`, from, to, type, path, active }
}

function getNodeIcon(id: string): string { return nodeIcons[id] || '📦' }
function getNodeDescription(id: string): string { return nodeDescriptions[id] || '' }

// 节点职能分组：用于差异化配色
type NodeCategory = 'collect' | 'plan' | 'create' | 'review' | 'output'
const nodeCategories: Record<string, NodeCategory> = {
  trend_collector: 'collect',
  trend_analyzer: 'collect',
  strategist: 'plan',
  title_lab: 'plan',
  copywriter: 'create',
  compliance_checker: 'review',
  chief_editor: 'review',
  human_review: 'review',
  visual_designer: 'output',
  finalize: 'output',
}
function getNodeCategory(id: string): NodeCategory { return nodeCategories[id] || 'collect' }

function getStatusText(status: NodeStatus): string {
  const m: Record<NodeStatus, string> = { pending: '等待中', running: '运行中', completed: '已完成', error: '错误' }
  return m[status] || status
}

function getMarkerEnd(edge: Edge): string {
  if (edge.type === 'back') return 'url(#arrow-back)'
  if (edge.type === 'conditional') return 'url(#arrow-cond)'
  if (edge.active) return 'url(#arrow-active)'
  return 'url(#arrow-normal)'
}

function hasDetails(node: any): boolean {
  return !!(node.input || node.output || node.message || node.error)
}

function handleNodeClick(node: any): void {
  // 如果点击的是当前已选中的节点，则关闭侧边栏
  if (selectedNode.value?.id === node.id) {
    selectedNode.value = null
  } else {
    // 否则打开新节点的侧边栏
    selectedNode.value = node
  }
}

function handleContainerClick(): void {
  // 点击容器空白区域时关闭侧边栏
  selectedNode.value = null
}

function formatTime(ts: number): string { return new Date(ts).toLocaleTimeString('zh-CN') }

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
}
</script>

<style scoped>
/* ========== 画布容器：双层渐变 + 微弱网格 ========== */
.workflow-graph-container {
  @apply relative w-full rounded-2xl p-6 overflow-auto;
  /* 比 bg-secondary 略深，并加径向高光，避免与节点同色 */
  background:
    radial-gradient(ellipse 80% 60% at 50% 0%, rgba(99, 102, 241, 0.08), transparent 70%),
    linear-gradient(180deg, #131a2b 0%, #0d1322 100%);
  border: 1px solid rgba(99, 102, 241, 0.12);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.04),
    0 10px 40px rgba(0, 0, 0, 0.35);
}

/* 装饰网格：等距点阵，16px 间隔，极低对比度 */
.canvas-grid {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  background-size: 18px 18px;
  pointer-events: none;
  border-radius: inherit;
  mask-image: radial-gradient(ellipse 90% 90% at 50% 50%, #000 40%, transparent 100%);
}

/* 顶部柔光 */
.canvas-glow {
  position: absolute;
  top: -120px;
  left: 50%;
  transform: translateX(-50%);
  width: 60%;
  height: 220px;
  background: radial-gradient(ellipse at center, rgba(139, 92, 246, 0.15), transparent 70%);
  pointer-events: none;
  filter: blur(8px);
}

/* SVG 主画布 */
.workflow-svg {
  position: relative;
  z-index: 1;
  width: 100%;
  height: auto;
  min-height: 350px;
}

/* ========== 连线样式 ========== */
.edge {
  fill: none;
  stroke-width: 2;
  transition: all 0.3s ease;
}

.edge.normal {
  stroke: #64748b;
  opacity: 0.55;
}

.edge.back {
  stroke: #fbbf24;
  stroke-dasharray: 8, 4;
  opacity: 0.7;
}

.edge.conditional {
  stroke: #60a5fa;
  stroke-dasharray: 4, 4;
  opacity: 0.75;
}

.edge.active {
  stroke: #a78bfa;
  stroke-width: 2.5;
  opacity: 1;
  filter: drop-shadow(0 0 4px rgba(167, 139, 250, 0.5));
}

/* ========== 节点组 ========== */
.node-group {
  cursor: pointer;
}

/* hover 反馈通过 .node-bg 的描边/阴影实现，不在 <g> 上用 transform，
   因为 SVG <g> 的 attribute transform 会被 CSS transform 完全覆盖，导致抖动 */

/* ========== 节点背景：基础描边（按分组着色） ========== */
.node-bg {
  stroke-width: 1.5;
  transition: all 0.3s ease;
  filter: drop-shadow(0 4px 10px rgba(0, 0, 0, 0.45));
}

/* 顶部高光线（玻璃质感） */
.node-highlight {
  stroke: rgba(255, 255, 255, 0.08);
  stroke-width: 1;
  pointer-events: none;
}

/* 分组描边色：每个职能一种边框色 */
.category-collect .node-bg { stroke: rgba(56, 189, 248, 0.45); }
.category-plan    .node-bg { stroke: rgba(168, 85, 247, 0.45); }
.category-create  .node-bg { stroke: rgba(244, 114, 182, 0.50); }
.category-review  .node-bg { stroke: rgba(251, 191, 36, 0.45); }
.category-output  .node-bg { stroke: rgba(45, 212, 191, 0.50); }

/* hover 时分组描边加亮 + 阴影 */
.category-collect:hover .node-bg { stroke: #38bdf8; filter: drop-shadow(0 6px 16px rgba(56, 189, 248, 0.35)); }
.category-plan:hover    .node-bg { stroke: #a855f7; filter: drop-shadow(0 6px 16px rgba(168, 85, 247, 0.35)); }
.category-create:hover  .node-bg { stroke: #ec4899; filter: drop-shadow(0 6px 16px rgba(236, 72, 153, 0.40)); }
.category-review:hover  .node-bg { stroke: #f59e0b; filter: drop-shadow(0 6px 16px rgba(245, 158, 11, 0.35)); }
.category-output:hover  .node-bg { stroke: #2dd4bf; filter: drop-shadow(0 6px 16px rgba(45, 212, 191, 0.40)); }

/* ========== 状态描边：优先级高于分组 ========== */
.node-group.status-running .node-bg {
  stroke: #a78bfa !important;
  stroke-width: 2;
  filter: drop-shadow(0 0 12px rgba(167, 139, 250, 0.6));
  animation: pulse-running 2s ease-in-out infinite;
}

.node-group.status-completed .node-bg {
  stroke: #34d399 !important;
  stroke-width: 1.8;
  filter: drop-shadow(0 0 8px rgba(52, 211, 153, 0.35));
}

.node-group.status-error .node-bg {
  stroke: #f87171 !important;
  stroke-width: 2;
  filter: drop-shadow(0 0 12px rgba(248, 113, 113, 0.55));
  animation: pulse-error 1.2s ease-in-out infinite;
}

@keyframes pulse-running {
  0%, 100% { filter: drop-shadow(0 0 8px rgba(167, 139, 250, 0.45)); }
  50%      { filter: drop-shadow(0 0 16px rgba(167, 139, 250, 0.75)); }
}

@keyframes pulse-error {
  0%, 100% { filter: drop-shadow(0 0 8px rgba(248, 113, 113, 0.4)); }
  50%      { filter: drop-shadow(0 0 16px rgba(248, 113, 113, 0.7)); }
}

/* ========== 图标圆形底色（按分组） ========== */
.icon-bg {
  stroke: rgba(255, 255, 255, 0.06);
  stroke-width: 1;
  transition: all 0.3s ease;
}
.icon-bg-collect { fill: rgba(56, 189, 248, 0.18); }
.icon-bg-plan    { fill: rgba(168, 85, 247, 0.20); }
.icon-bg-create  { fill: rgba(236, 72, 153, 0.22); }
.icon-bg-review  { fill: rgba(245, 158, 11, 0.20); }
.icon-bg-output  { fill: rgba(45, 212, 191, 0.22); }

.node-group:hover .icon-bg {
  stroke: rgba(255, 255, 255, 0.18);
}

/* 节点图标文字 */
.node-icon-text {
  font-size: 18px;
  pointer-events: none;
}

/* 节点名称文字 */
.node-name-text {
  font-size: 11px;
  fill: #f1f5f9;
  font-weight: 600;
  letter-spacing: 0.3px;
  pointer-events: none;
}

/* ========== 状态指示点 ========== */
.status-dot {
  transition: all 0.3s ease;
  stroke: rgba(15, 23, 42, 0.6);
  stroke-width: 1.5;
}

.dot-pending   { fill: #94a3b8; }
.dot-running   { fill: #a78bfa; filter: drop-shadow(0 0 4px rgba(167, 139, 250, 0.8)); }
.dot-completed { fill: #34d399; filter: drop-shadow(0 0 3px rgba(52, 211, 153, 0.6)); }
.dot-error     { fill: #f87171; filter: drop-shadow(0 0 4px rgba(248, 113, 113, 0.7)); }

/* ========== 图例（右下角浮层） ========== */
.legend {
  position: absolute;
  right: 16px;
  bottom: 16px;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 14px;
  background: rgba(15, 23, 42, 0.7);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 999px;
  font-size: 11px;
  color: #cbd5e1;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  user-select: none;
  pointer-events: none;
}

.legend-section {
  display: flex;
  align-items: center;
  gap: 10px;
}

.legend-title {
  font-weight: 600;
  color: #94a3b8;
  font-size: 10px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.legend-divider {
  width: 1px;
  height: 14px;
  background: rgba(148, 163, 184, 0.2);
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
}

/* 分组色点（图例） */
.dot-cat {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 2px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}
.cat-collect { background: #38bdf8; }
.cat-plan    { background: #a855f7; }
.cat-create  { background: #ec4899; }
.cat-review  { background: #f59e0b; }
.cat-output  { background: #2dd4bf; }

/* 状态色点（图例） */
.dot-st {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
}
.st-pending   { background: #94a3b8; }
.st-running   { background: #a78bfa; box-shadow: 0 0 6px rgba(167, 139, 250, 0.8); }
.st-completed { background: #34d399; box-shadow: 0 0 5px rgba(52, 211, 153, 0.6); }
.st-error     { background: #f87171; box-shadow: 0 0 6px rgba(248, 113, 113, 0.7); }

/* 小屏幕隐藏图例 */
@media (max-width: 720px) {
  .legend { display: none; }
}

/* Modal 遮罩层 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

/* Modal 主体 */
.modal-box {
  background: var(--color-bg-primary, #1e293b);
  border: 1px solid var(--color-border-primary, #334155);
  border-radius: 16px;
  width: 480px;
  max-width: 90vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5);
}

/* Modal 头部 */
.modal-header {
  @apply flex items-center justify-between p-6 border-b border-border-primary;
}

.close-btn {
  @apply p-2 rounded-lg hover:bg-bg-secondary transition-colors text-text-secondary hover:text-text-primary;
}

/* Modal 内容 */
.modal-content {
  @apply flex-1 overflow-y-auto p-6 space-y-6;
}

.detail-section {
  @apply space-y-2;
}

.detail-label {
  @apply text-xs font-semibold text-text-muted uppercase tracking-wider;
}

.detail-value {
  @apply text-sm text-text-primary;
}

.status-badge {
  @apply inline-flex items-center px-3 py-1 rounded-full text-xs font-medium;
}

.badge-pending { background: rgba(156,163,175,0.2); color: #9ca3af; }
.badge-running { background: rgba(139,92,246,0.2); color: #8b5cf6; }
.badge-completed { background: rgba(34,197,94,0.2); color: #22c55e; }
.badge-error { background: rgba(239,68,68,0.2); color: #ef4444; }

.error-box {
  @apply bg-error/10 text-error rounded-lg p-3 text-xs;
}

.data-box {
  @apply bg-bg-tertiary rounded-lg p-3 text-xs overflow-x-auto;
  max-height: 200px;
}

/* Modal 动画 */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}

.modal-fade-enter-active .modal-box,
.modal-fade-leave-active .modal-box {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-from .modal-box,
.modal-fade-leave-to .modal-box {
  transform: scale(0.95);
  opacity: 0;
}
</style>
